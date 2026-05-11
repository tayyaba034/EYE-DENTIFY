const { supabaseAdmin, rawPg } = require('../config/database');
const logger = require('../services/loggerService');
const realtimeHub = require('../services/realtimeHub');
const { sendAlertPush } = require('../services/firebaseDelivery');

const ALERT_SELECT_BASE = `
SELECT
    a.alert_id,
    a.detection_id,
    a.user_id,
    a.alert_timestamp,
    a.message,
    __AI_SUMMARY_SELECT__,
    a.status,
    a.priority,
    a.alert_level,
    a.sightings_count,
    a.first_seen_time,
    a.last_seen_time,
    a.camera_id_text,
    a.track_id,
    a.confidence,
    __CAMERA_RELIABILITY_SELECT__,
    __READ_TS_SELECT__,
    __ACK_TS_SELECT__,
    a.fcm_token,
    d.missing_person_id,
    d.camera_id,
    d.camera_id_text,
    d.track_id,
    d.detection_timestamp,
    __DETECTION_FACE_SELECT__,
    __DETECTION_CLOTHING_SELECT__,
    __DETECTION_HEIGHT_SELECT__,
    __DETECTION_COMBINED_SELECT__,
    __DETECTION_SNAPSHOT_SELECT__,
    d.verified,
    __CAMERA_NAME_SELECT__,
    __CAMERA_LOCATION_SELECT__,
    __CAMERA_LAT_SELECT__,
    __CAMERA_LNG_SELECT__,
    mp.full_name,
    media.file_path AS original_photo_url
FROM alerts a
JOIN detections d ON a.detection_id = d.detection_id
__CAMERA_JOIN__
LEFT JOIN missing_persons mp ON d.missing_person_id = mp.missing_person_id
LEFT JOIN LATERAL (
    SELECT file_path
    FROM media
    WHERE missing_person_id = mp.missing_person_id
    ORDER BY upload_timestamp DESC
    LIMIT 1
) media ON true
`;

let _hasAiSummaryColumn = null;
let _cameraSql = null;
let _alertTimestampSql = null;
let _alertUsesLegacyTimestamps = null;
let _detectionSql = null;

async function _resolveAiSummarySelect() {
    if (!rawPg) return 'NULL::text AS ai_summary';
    if (_hasAiSummaryColumn !== null) {
        return _hasAiSummaryColumn ? 'a.ai_summary' : 'NULL::text AS ai_summary';
    }
    try {
        const result = await rawPg.query(
            `SELECT 1
             FROM information_schema.columns
             WHERE table_schema = 'public'
               AND table_name = 'alerts'
               AND column_name = 'ai_summary'
             LIMIT 1`
        );
        _hasAiSummaryColumn = result.rowCount > 0;
    } catch (error) {
        _hasAiSummaryColumn = false;
    }
    return _hasAiSummaryColumn ? 'a.ai_summary' : 'NULL::text AS ai_summary';
}

async function _resolveCameraSql() {
    if (_cameraSql) return _cameraSql;
    const fallback = {
        join: 'LEFT JOIN cameras c ON d.camera_id_text::text = c.id::text',
        reliability: 'NULL::numeric AS camera_reliability_score',
        name: 'c.name AS camera_name',
        location: 'c.location AS location_name',
        lat: 'c.lat AS latitude',
        lng: 'c.lng AS longitude',
    };
    if (!rawPg) {
        _cameraSql = fallback;
        return _cameraSql;
    }
    try {
        const res = await rawPg.query(
            `SELECT column_name
             FROM information_schema.columns
             WHERE table_schema='public' AND table_name='cameras'`
        );
        const cols = new Set(res.rows.map((r) => r.column_name));
        const hasLegacy = cols.has('camera_id');
        if (hasLegacy) {
            _cameraSql = {
                join: 'LEFT JOIN cameras c ON d.camera_id = c.camera_id',
                reliability: cols.has('camera_reliability_score')
                    ? 'c.camera_reliability_score'
                    : 'NULL::numeric AS camera_reliability_score',
                name: cols.has('camera_name') ? 'c.camera_name' : 'NULL::text AS camera_name',
                location: cols.has('location_name') ? 'c.location_name' : 'NULL::text AS location_name',
                lat: cols.has('latitude') ? 'c.latitude' : 'NULL::numeric AS latitude',
                lng: cols.has('longitude') ? 'c.longitude' : 'NULL::numeric AS longitude',
            };
        } else {
            _cameraSql = fallback;
        }
    } catch {
        _cameraSql = fallback;
    }
    return _cameraSql;
}

async function _resolveAlertTimestampSql() {
    if (_alertTimestampSql) return _alertTimestampSql;
    const fallback = {
        read: 'a.read_at AS read_timestamp',
        ack: 'a.acknowledged_at AS acknowledged_timestamp',
    };
    if (!rawPg) {
        _alertTimestampSql = fallback;
        return _alertTimestampSql;
    }
    try {
        const res = await rawPg.query(
            `SELECT column_name
             FROM information_schema.columns
             WHERE table_schema='public' AND table_name='alerts'`
        );
        const cols = new Set(res.rows.map((r) => r.column_name));
        _alertTimestampSql = {
            read: cols.has('read_timestamp')
                ? 'a.read_timestamp'
                : 'a.read_at AS read_timestamp',
            ack: cols.has('acknowledged_timestamp')
                ? 'a.acknowledged_timestamp'
                : 'a.acknowledged_at AS acknowledged_timestamp',
        };
    } catch {
        _alertTimestampSql = fallback;
    }
    return _alertTimestampSql;
}

async function _resolveAlertPatchKeys() {
    if (_alertUsesLegacyTimestamps !== null) return _alertUsesLegacyTimestamps;
    if (!rawPg) {
        _alertUsesLegacyTimestamps = false;
        return _alertUsesLegacyTimestamps;
    }
    try {
        const res = await rawPg.query(
            `SELECT 1
             FROM information_schema.columns
             WHERE table_schema='public' AND table_name='alerts' AND column_name='read_timestamp'
             LIMIT 1`
        );
        _alertUsesLegacyTimestamps = res.rowCount > 0;
    } catch {
        _alertUsesLegacyTimestamps = false;
    }
    return _alertUsesLegacyTimestamps;
}

async function _resolveDetectionSql() {
    if (_detectionSql) return _detectionSql;
    const fallback = {
        face: 'd.face_score AS face_score',
        clothing: 'd.clothing_score AS clothing_score',
        height: 'NULL::numeric AS height_match_score',
        combined: 'COALESCE(d.confidence, d.face_score) AS combined_score',
        snapshot: 'd.snapshot_url AS snapshot_url',
    };
    if (!rawPg) {
        _detectionSql = fallback;
        return _detectionSql;
    }
    try {
        const res = await rawPg.query(
            `SELECT column_name
             FROM information_schema.columns
             WHERE table_schema='public' AND table_name='detections'`
        );
        const cols = new Set(res.rows.map((r) => r.column_name));
        _detectionSql = {
            face: cols.has('face_match_score')
                ? 'COALESCE(d.face_score, d.face_match_score) AS face_score'
                : 'd.face_score AS face_score',
            clothing: cols.has('color_match_score')
                ? 'COALESCE(d.clothing_score, d.color_match_score) AS clothing_score'
                : 'd.clothing_score AS clothing_score',
            height: cols.has('height_match_score')
                ? 'd.height_match_score'
                : 'NULL::numeric AS height_match_score',
            combined: cols.has('combined_score')
                ? 'COALESCE(d.confidence, d.combined_score, d.face_score) AS combined_score'
                : 'COALESCE(d.confidence, d.face_score) AS combined_score',
            snapshot: cols.has('image_snapshot_path')
                ? 'COALESCE(d.snapshot_url, d.image_snapshot_path) AS snapshot_url'
                : 'd.snapshot_url AS snapshot_url',
        };
    } catch {
        _detectionSql = fallback;
    }
    return _detectionSql;
}

function mapAlertRow(row) {
    return {
        alert_id: row.alert_id,
        detection_id: row.detection_id,
        user_id: row.user_id,
        alert_timestamp: row.alert_timestamp,
        message: row.message,
        ai_summary: row.ai_summary,
        status: row.status,
        priority: row.priority,
        alert_level: row.alert_level,
        sightings_count: row.sightings_count,
        first_seen_time: row.first_seen_time,
        last_seen_time: row.last_seen_time,
        camera_id: row.camera_id_text,
        track_id: row.track_id,
        confidence: row.confidence,
        camera_reliability_score: row.camera_reliability_score,
        read_timestamp: row.read_timestamp,
        acknowledged_timestamp: row.acknowledged_timestamp,
        detection: {
            detection_id: row.detection_id,
            person_name: row.full_name || 'Unknown',
            camera_location: row.location_name || row.camera_name || 'Unknown',
            camera_id: row.camera_id_text || row.camera_id,
            track_id: row.track_id,
            latitude: row.latitude ? Number(row.latitude) : null,
            longitude: row.longitude ? Number(row.longitude) : null,
            face_match_score: Number(row.face_score),
            color_match_score:
                row.clothing_score != null ? Number(row.clothing_score) : null,
            height_match_score:
                row.height_match_score != null ? Number(row.height_match_score) : null,
            combined_score: Number(row.combined_score),
            snapshot_url: row.snapshot_url,
            original_photo_url: row.original_photo_url,
            verified: row.verified,
            detection_timestamp: row.detection_timestamp,
        },
    };
}

async function _runAlertSelect(whereClause, params) {
    if (!rawPg) throw new Error('DATABASE_URL raw pg connection required for alert joins');
    const aiSummarySelect = await _resolveAiSummarySelect();
    const cam = await _resolveCameraSql();
    const ts = await _resolveAlertTimestampSql();
    const det = await _resolveDetectionSql();
    const queryText = ALERT_SELECT_BASE
        .replace('__AI_SUMMARY_SELECT__', aiSummarySelect)
        .replace('__CAMERA_JOIN__', cam.join)
        .replace('__CAMERA_RELIABILITY_SELECT__', cam.reliability)
        .replace('__CAMERA_NAME_SELECT__', cam.name)
        .replace('__CAMERA_LOCATION_SELECT__', cam.location)
        .replace('__CAMERA_LAT_SELECT__', cam.lat)
        .replace('__CAMERA_LNG_SELECT__', cam.lng)
        .replace('__READ_TS_SELECT__', ts.read)
        .replace('__ACK_TS_SELECT__', ts.ack)
        .replace('__DETECTION_FACE_SELECT__', det.face)
        .replace('__DETECTION_CLOTHING_SELECT__', det.clothing)
        .replace('__DETECTION_HEIGHT_SELECT__', det.height)
        .replace('__DETECTION_COMBINED_SELECT__', det.combined)
        .replace('__DETECTION_SNAPSHOT_SELECT__', det.snapshot);
    const result = await rawPg.query(`${queryText} ${whereClause}`, params);
    return result.rows;
}

async function getMyAlerts(req, res) {
    try {
        const userId = req.user?.userId;
        if (!userId) {
            return res.status(401).json({ error: 'Authentication required' });
        }
        const rows = await _runAlertSelect('WHERE a.user_id::text = $1 ORDER BY a.alert_timestamp DESC', [String(userId)]);
        return res.status(200).json(rows.map(mapAlertRow));
    } catch (error) {
        logger.error('Fetch alerts failed', { error: error.message });
        return res.status(500).json({ error: 'Failed to fetch alerts' });
    }
}

async function getAlertsSnapshot(req, res) {
    return getMyAlerts(req, res);
}

async function getAlertById(req, res) {
    try {
        const alertId = Number(req.params.id);
        if (!alertId) return res.status(400).json({ error: 'Invalid alert id' });
        const rows = await _runAlertSelect('WHERE a.alert_id = $1', [alertId]);
        if (!rows.length) return res.status(404).json({ error: 'Alert not found' });
        return res.status(200).json(mapAlertRow(rows[0]));
    } catch (error) {
        logger.error('Fetch alert failed', { error: error.message });
        return res.status(500).json({ error: 'Failed to fetch alert' });
    }
}

async function markAsRead(req, res) {
    const legacy = await _resolveAlertPatchKeys();
    return _simpleAlertUpdate(req, res, {
        [legacy ? 'read_timestamp' : 'read_at']: new Date().toISOString(),
    });
}

async function acknowledge(req, res) {
    const legacy = await _resolveAlertPatchKeys();
    return _simpleAlertUpdate(req, res, {
        [legacy ? 'acknowledged_timestamp' : 'acknowledged_at']: new Date().toISOString(),
    });
}

async function dismiss(req, res) {
    return _simpleAlertUpdate(req, res, {
        status: 'dismissed',
        dismissed_at: new Date().toISOString(),
    });
}

async function _simpleAlertUpdate(req, res, patch) {
    try {
        const alertId = Number(req.params.id);
        if (!alertId) return res.status(400).json({ error: 'Invalid alert id' });
        const { error } = await supabaseAdmin
            .from('alerts')
            .update(patch)
            .eq('alert_id', alertId);
        if (error) return res.status(400).json({ error: error.message });
        const rows = await _runAlertSelect('WHERE a.alert_id = $1', [alertId]);
        if (!rows.length) return res.status(404).json({ error: 'Alert not found' });
        const alert = mapAlertRow(rows[0]);
        realtimeHub.broadcast({ type: 'alert_updated', payload: { alert } });
        return res.status(200).json(alert);
    } catch (error) {
        logger.error('Alert patch failed', { error: error.message });
        return res.status(500).json({ error: 'Failed to update alert' });
    }
}

async function confirmMatch(req, res) {
    return _handleDecision(req, res, 'acknowledged', 'CONFIRM_MATCH');
}

async function rejectMatch(req, res) {
    return _handleDecision(req, res, 'dismissed', 'REJECT_FALSE_ALARM');
}

async function _handleDecision(req, res, status, actionType) {
    const alertId = Number(req.params.id);
    const decisionPayload = req.body || {};
    const operatorId = decisionPayload.operatorId || req.user?.userId || null;

    if (!alertId) {
        return res.status(400).json({ error: 'Invalid alert id' });
    }

    try {
        const legacy = await _resolveAlertPatchKeys();
        const { error: alertError } = await supabaseAdmin
            .from('alerts')
            .update({
                status,
                [legacy ? 'acknowledged_timestamp' : 'acknowledged_at']: new Date().toISOString(),
                [legacy ? 'read_timestamp' : 'read_at']: new Date().toISOString(),
            })
            .eq('alert_id', alertId);

        if (alertError) return res.status(400).json({ error: alertError.message });

        const { data: alertRow, error: alertFetchError } = await supabaseAdmin
            .from('alerts')
            .select('detection_id, fcm_token')
            .eq('alert_id', alertId)
            .maybeSingle();

        if (alertFetchError || !alertRow) {
            return res.status(404).json({ error: 'Alert not found' });
        }

        await supabaseAdmin
            .from('detections')
            .update({
                verified: status === 'acknowledged',
                verification_timestamp: new Date().toISOString(),
                verified_by: operatorId,
            })
            .eq('detection_id', alertRow.detection_id);

        await supabaseAdmin.from('system_logs').insert({
            user_id: operatorId,
            action_type: actionType,
            action_details: decisionPayload,
            ip_address: req.ip,
        });

        const rows = await _runAlertSelect('WHERE a.alert_id = $1', [alertId]);
        const alert = rows[0] ? mapAlertRow(rows[0]) : null;

        if (alert) {
            realtimeHub.broadcast({
                type: 'alert_updated',
                payload: { alert },
            });
            await sendAlertPush({
                token: alertRow.fcm_token,
                title: 'Eye-Dentify Alert',
                body: alert.ai_summary || `Alert ${alert.alert_id} ${status}`,
                data: { alertId, status },
            });
        }

        return res.status(200).json({ success: true, alert });
    } catch (error) {
        logger.error('Decision update failed', { error: error.message });
        return res.status(500).json({ error: 'Failed to update alert' });
    }
}

module.exports = {
    getMyAlerts,
    getAlertsSnapshot,
    getAlertById,
    markAsRead,
    acknowledge,
    dismiss,
    confirmMatch,
    rejectMatch,
};
