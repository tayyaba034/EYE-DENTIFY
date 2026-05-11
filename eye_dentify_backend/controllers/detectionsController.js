const { supabaseAdmin, rawPg } = require('../config/database');
const logger = require('../services/loggerService');
const realtimeHub = require('../services/realtimeHub');
const {
    sendAlertPush,
    uploadSnapshotToSupabaseStorage,
} = require('../services/firebaseDelivery');
const { generateAlertSummaryGemini } = require('../services/aiService');

const COOLDOWN_MINUTES = Number(process.env.ALERT_COOLDOWN_MINUTES || 3);
const SIMILARITY_THRESHOLD = Number(process.env.ALERT_SIMILARITY_THRESHOLD || 0.8);
const FACE_THRESHOLD = Number(process.env.ALERT_FACE_THRESHOLD || 0.8);
const CLOTHING_THRESHOLD = Number(process.env.ALERT_CLOTHING_THRESHOLD || 0.7);

async function ingestDetection(req, res) {
    const apiKey = req.headers['x-api-key'];
    if (process.env.DETECTION_INGEST_KEY && apiKey !== process.env.DETECTION_INGEST_KEY) {
        return res.status(401).json({ error: 'Invalid ingest key' });
    }

    const {
        camera_id,
        track_id,
        embedding,
        face_score,
        clothing_score,
        bbox,
        snapshot_base64,
        detection_timestamp,
        missing_person_id,
        user_id,
        fcm_token,
        message,
    } = req.body || {};

    if (!camera_id || !track_id || face_score == null || detection_timestamp == null || !missing_person_id) {
        return res.status(400).json({ error: 'Missing required detection fields' });
    }

    try {
        const camera = await _getCamera(camera_id);
        const cameraReliability = Number(camera?.camera_reliability_score ?? 1.0);

        let snapshotUrl = null;
        if (snapshot_base64) {
            const buffer = Buffer.from(snapshot_base64, 'base64');
            snapshotUrl = await uploadSnapshotToSupabaseStorage({
                buffer,
                destinationPath: `snapshots/${camera_id}/${track_id}/${Date.now()}.jpg`,
                contentType: 'image/jpeg',
            });
        }

        const rawConfidence =
            (Number(face_score) * cameraReliability) +
            ((Number(clothing_score) || 0) * cameraReliability);
        const effectiveConfidence = Math.min(1, Math.max(0, rawConfidence));

        const detectionInsert = await supabaseAdmin
            .from('detections')
            .insert({
                camera_id: Number(camera_id),
                camera_id_text: String(camera_id),
                track_id: String(track_id),
                embedding: embedding || null,
                face_score: face_score,
                clothing_score: clothing_score ?? null,
                bbox: bbox || null,
                snapshot_url: snapshotUrl,
                detection_timestamp,
                confidence: effectiveConfidence,
                missing_person_id,
                source: 'camera',
            })
            .select('detection_id, detection_timestamp')
            .single();

        if (detectionInsert.error || !detectionInsert.data) {
            throw new Error(detectionInsert.error?.message || 'Failed to insert detection');
        }
        const detection = detectionInsert.data;

        const existingAlert = await _findDuplicateAlert({
            trackId: String(track_id),
            cameraId: String(camera_id),
            similarityScore: Number(face_score),
        });

        const ownerUserId = await _getMissingPersonOwner(missing_person_id);

        let alertRow;
        if (existingAlert) {
            alertRow = await _mergeAlert({
                alertId: existingAlert.alert_id,
                detectionId: detection.detection_id,
                cameraId: String(camera_id),
                trackId: String(track_id),
                confidence: effectiveConfidence,
            });
        } else {
            alertRow = await _createAlert({
                detectionId: detection.detection_id,
                userId: user_id || ownerUserId,
                message,
                cameraId: String(camera_id),
                trackId: String(track_id),
                confidence: effectiveConfidence,
                fcmToken: fcm_token || null,
            });
        }

        if (alertRow) {
            let aiSummary = alertRow.ai_summary || null;
            if (['strong_match', 'critical'].includes(alertRow.alert_level)) {
                aiSummary = await _generateAndStoreSummary(alertRow.alert_id);
            }
            const alertPayload = await _getAlertPayload(alertRow.alert_id);

            realtimeHub.broadcast({
                type: existingAlert ? 'alert_updated' : 'alert_created',
                payload: { alert: alertPayload },
            });

            if (_shouldPush(alertPayload.alert_level)) {
                const body = aiSummary || alertPayload.message;
                await sendAlertPush({
                    token: alertRow.fcm_token,
                    title: 'Eye-Dentify Alert',
                    body,
                    data: {
                        alertId: alertPayload.alert_id,
                        level: alertPayload.alert_level,
                    },
                });
                await _insertNotification({
                    user_id: alertPayload.user_id,
                    title: 'Eye-Dentify Alert',
                    body,
                    type: 'alert',
                    metadata: {
                        alert_id: alertPayload.alert_id,
                        level: alertPayload.alert_level,
                    },
                });
            }
        }

        return res.status(201).json({ success: true });
    } catch (error) {
        logger.error('Detection ingest failed', { error: error.message });
        return res.status(500).json({ error: 'Detection ingest failed' });
    }
}

async function getDetectionById(req, res) {
    try {
        const id = Number(req.params.id);
        if (!id) return res.status(400).json({ error: 'Invalid detection id' });
        const { data, error } = await supabaseAdmin
            .from('detections')
            .select('*')
            .eq('detection_id', id)
            .maybeSingle();
        if (error) return res.status(400).json({ error: error.message });
        if (!data) return res.status(404).json({ error: 'Detection not found' });
        return res.status(200).json(_mapDetection(data));
    } catch (error) {
        logger.error('Get detection failed', { error: error.message });
        return res.status(500).json({ error: 'Failed to fetch detection' });
    }
}

async function verifyDetection(req, res) {
    try {
        const id = Number(req.params.id);
        if (!id) return res.status(400).json({ error: 'Invalid detection id' });
        const verifier = req.user?.userId || null;
        const patch = {
            verified: req.body?.verified ?? true,
            verified_by: verifier,
            verified_at: new Date().toISOString(),
        };
        const { data, error } = await supabaseAdmin
            .from('detections')
            .update(patch)
            .eq('detection_id', id)
            .select('*')
            .maybeSingle();
        if (error) return res.status(400).json({ error: error.message });
        if (!data) return res.status(404).json({ error: 'Detection not found' });
        return res.status(200).json(_mapDetection(data));
    } catch (error) {
        logger.error('Verify detection failed', { error: error.message });
        return res.status(500).json({ error: 'Failed to verify detection' });
    }
}

async function getDetectionsByMissingPerson(req, res) {
    try {
        const missingPersonId = Number(req.params.id);
        if (!missingPersonId) {
            return res.status(400).json({ error: 'Invalid missing person id' });
        }
        const { data, error } = await supabaseAdmin
            .from('detections')
            .select('*')
            .eq('missing_person_id', missingPersonId)
            .order('detection_timestamp', { ascending: false });
        if (error) return res.status(400).json({ error: error.message });
        return res.status(200).json((data || []).map(_mapDetection));
    } catch (error) {
        logger.error('Get detections by case failed', { error: error.message });
        return res.status(500).json({ error: 'Failed to fetch detections' });
    }
}

function _mapDetection(row) {
    return {
        detection_id: row.detection_id,
        person_name: row.person_name || 'Unknown',
        camera_location: row.camera_location || 'Unknown',
        camera_id: row.camera_id_text || row.camera_id,
        track_id: row.track_id,
        latitude: row.latitude ? Number(row.latitude) : null,
        longitude: row.longitude ? Number(row.longitude) : null,
        face_match_score: Number(row.face_score ?? row.face_match_score ?? 0),
        color_match_score: row.clothing_score ?? row.color_match_score ?? null,
        height_match_score: row.height_match_score ?? null,
        combined_score: Number(row.confidence ?? row.combined_score ?? 0),
        snapshot_url: row.snapshot_url || row.image_snapshot_path || null,
        original_photo_url: row.original_photo_url || null,
        verified: row.verified ?? false,
        detection_timestamp: row.detection_timestamp,
    };
}

async function _getMissingPersonOwner(missingPersonId) {
    const { data } = await supabaseAdmin
        .from('missing_persons')
        .select('user_id')
        .eq('missing_person_id', missingPersonId)
        .maybeSingle();
    return data?.user_id || null;
}

async function _getCamera(cameraId) {
    const byId = await supabaseAdmin
        .from('cameras')
        .select('*')
        .eq('id', cameraId)
        .maybeSingle();
    if (!byId.error && byId.data) return byId.data;

    const byName = await supabaseAdmin
        .from('cameras')
        .select('*')
        .eq('name', String(cameraId))
        .maybeSingle();
    if (!byName.error && byName.data) return byName.data;

    return null;
}

async function _findDuplicateAlert({ trackId, cameraId, similarityScore }) {
    if (similarityScore < SIMILARITY_THRESHOLD) return null;
    const { data } = await supabaseAdmin
        .from('alerts')
        .select('alert_id,last_seen_time')
        .eq('track_id', trackId)
        .eq('camera_id_text', cameraId)
        .gte('last_seen_time', new Date(Date.now() - COOLDOWN_MINUTES * 60000).toISOString())
        .order('last_seen_time', { ascending: false })
        .limit(1);
    return data?.[0] || null;
}

async function _mergeAlert({ alertId, detectionId, cameraId, trackId, confidence }) {
    const current = await supabaseAdmin
        .from('alerts')
        .select('sightings_count,fcm_token')
        .eq('alert_id', alertId)
        .single();
    if (current.error || !current.data) throw new Error(current.error?.message || 'Alert not found');
    const sightings = Number(current.data.sightings_count || 1) + 1;
    const alertLevel = await _computeAlertLevel({ detectionId, sightings });
    const priority = _priorityForLevel(alertLevel);

    const updated = await supabaseAdmin
        .from('alerts')
        .update({
            sightings_count: sightings,
            last_seen_time: new Date().toISOString(),
            detection_id: detectionId,
            alert_level: alertLevel,
            priority,
            camera_id_text: cameraId,
            track_id: trackId,
            confidence,
        })
        .eq('alert_id', alertId)
        .select('*')
        .single();
    if (updated.error) throw new Error(updated.error.message);
    return updated.data;
}

async function _createAlert({ detectionId, userId, message, cameraId, trackId, confidence, fcmToken }) {
    const alertLevel = await _computeAlertLevel({ detectionId, sightings: 1 });
    const priority = _priorityForLevel(alertLevel);
    const created = await supabaseAdmin
        .from('alerts')
        .insert({
            detection_id: detectionId,
            user_id: userId,
            message: message || 'Potential match detected',
            status: 'sent',
            priority,
            alert_timestamp: new Date().toISOString(),
            sightings_count: 1,
            first_seen_time: new Date().toISOString(),
            last_seen_time: new Date().toISOString(),
            alert_level: alertLevel,
            camera_id_text: cameraId,
            track_id: trackId,
            confidence,
            fcm_token: fcmToken,
        })
        .select('*')
        .single();
    if (created.error) throw new Error(created.error.message);
    return created.data;
}

async function _computeAlertLevel({ detectionId, sightings }) {
    const detection = await supabaseAdmin
        .from('detections')
        .select('track_id,detection_timestamp,face_score,clothing_score')
        .eq('detection_id', detectionId)
        .single();
    if (detection.error || !detection.data) return 'preliminary';
    const row = detection.data;
    const trackId = row.track_id;
    const multiFrame = await _isMultiFrame(trackId);
    const multiCamera = await _isMultiCamera(trackId);
    const faceScore = Number(row.face_score || 0);
    const clothingScore = Number(row.clothing_score || 0);

    if (!multiFrame) return 'preliminary';
    if (multiCamera || sightings > 6) return 'critical';
    if (faceScore >= FACE_THRESHOLD && clothingScore >= CLOTHING_THRESHOLD) return 'strong_match';
    return 'tracking';
}

async function _isMultiFrame(trackId) {
    const { data } = await supabaseAdmin
        .from('detections')
        .select('detection_id,detection_timestamp')
        .eq('track_id', trackId)
        .gte('detection_timestamp', new Date(Date.now() - 5000).toISOString());
    return (data || []).length >= 3;
}

async function _isMultiCamera(trackId) {
    const { data } = await supabaseAdmin
        .from('detections')
        .select('camera_id_text,detection_timestamp')
        .eq('track_id', trackId)
        .gte('detection_timestamp', new Date(Date.now() - 5000).toISOString());
    const distinct = new Set((data || []).map((row) => row.camera_id_text).filter(Boolean));
    return distinct.size >= 2;
}

function _priorityForLevel(level) {
    switch (level) {
        case 'critical':
            return 'critical';
        case 'strong_match':
            return 'high';
        case 'tracking':
            return 'medium';
        default:
            return 'low';
    }
}

function _shouldPush(level) {
    return level === 'critical' || level === 'strong_match';
}

async function _generateAndStoreSummary(alertId) {
    try {
        const alert = await _getAlertPayload(alertId);
        if (!alert) return null;
        const summary = await generateAlertSummaryGemini({
            name: alert.detection?.person_name || 'Unknown',
            age: alert.detection?.age || 'Unknown',
            lastSeenLocation: alert.detection?.camera_location || 'Unknown',
            cameraName: alert.detection?.camera_location || 'Unknown',
            location: alert.detection?.camera_location || 'Unknown',
            detectedAt: alert.detection?.detection_timestamp,
            score: Math.round((alert.detection?.combined_score || 0) * 100),
            clothingScore: Math.round((alert.detection?.color_match_score || 0) * 100),
        });
        if (!summary) return null;
        await supabaseAdmin.from('alerts').update({ ai_summary: summary }).eq('alert_id', alertId);
        return summary;
    } catch (error) {
        logger.error('AI summary generation failed', { error: error.message });
        return null;
    }
}

async function _getAlertPayload(alertId) {
    const { data: row, error } = await supabaseAdmin
        .from('alerts')
        .select('*')
        .eq('alert_id', alertId)
        .maybeSingle();
    if (error || !row) return null;

    const detectionRes = await supabaseAdmin
        .from('detections')
        .select('*')
        .eq('detection_id', row.detection_id)
        .maybeSingle();
    const det = detectionRes.data || {};

    const mpRes = det.missing_person_id
        ? await supabaseAdmin
            .from('missing_persons')
            .select('full_name')
            .eq('missing_person_id', det.missing_person_id)
            .maybeSingle()
        : { data: null };
    const cam = await _getCamera(det.camera_id_text || det.camera_id);

    return {
        alert_id: row.alert_id,
        detection_id: row.detection_id,
        user_id: row.user_id,
        alert_timestamp: row.alert_timestamp,
        message: row.message,
        ai_summary: row.ai_summary,
        status: row.status,
        priority: row.priority,
        sightings_count: row.sightings_count,
        first_seen_time: row.first_seen_time,
        last_seen_time: row.last_seen_time,
        alert_level: row.alert_level,
        camera_id: row.camera_id_text,
        track_id: row.track_id,
        confidence: row.confidence,
        read_timestamp: row.read_timestamp || row.read_at || null,
        acknowledged_timestamp: row.acknowledged_timestamp || row.acknowledged_at || null,
        detection: {
            detection_id: row.detection_id,
            person_name: mpRes.data?.full_name || 'Unknown',
            camera_location: cam?.location || cam?.name || 'Unknown',
            camera_id: det.camera_id_text || det.camera_id || null,
            track_id: det.track_id || null,
            latitude: cam?.lat ? Number(cam.lat) : null,
            longitude: cam?.lng ? Number(cam.lng) : null,
            face_match_score: Number(det.face_score || 0),
            color_match_score: det.clothing_score != null ? Number(det.clothing_score) : null,
            combined_score: Number(det.confidence || det.face_score || 0),
            snapshot_url: det.snapshot_url || null,
            detection_timestamp: det.detection_timestamp || null,
        },
    };
}

async function _insertNotification(payload) {
    await supabaseAdmin.from('notifications').insert({
        user_id: payload.user_id,
        title: payload.title,
        body: payload.body,
        type: payload.type,
        metadata: payload.metadata || {},
    });
    realtimeHub.broadcast({
        type: 'notification_created',
        payload: { user_id: payload.user_id },
    });
}

module.exports = {
    ingestDetection,
    getDetectionById,
    verifyDetection,
    getDetectionsByMissingPerson,
};
