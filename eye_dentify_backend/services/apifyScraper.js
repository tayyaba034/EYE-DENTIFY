const { ApifyClient } = require('apify-client');
const cron = require('node-cron');
const { supabaseAdmin } = require('../config/database');
const logger = require('./loggerService');

async function searchSocialMediaSightings(personName, lastSeenLocation) {
    const token = process.env.APIFY_API_TOKEN;
    if (!token) return [];

    const client = new ApifyClient({ token });
    const hashtags = _hashtags(personName, lastSeenLocation);
    const runInput = {
        hashtags,
        resultsLimit: 20,
    };

    const run = await client.actor('apify/instagram-hashtag-scraper').call(runInput);
    const { items } = await client.dataset(run.defaultDatasetId).listItems({ limit: 20 });

    const now = Date.now();
    return (items || []).filter((item) => {
        const text = `${item.caption || ''} ${item.locationName || ''}`.toLowerCase();
        const hasName = personName && text.includes(personName.toLowerCase());
        const hasLocation = lastSeenLocation && text.includes(lastSeenLocation.toLowerCase());
        const ts = new Date(item.timestamp || item.createdAt || 0).getTime();
        const isRecent = ts > now - 24 * 60 * 60 * 1000;
        return hasName && hasLocation && isRecent;
    });
}

async function searchSocialMediaSightingsForCase(missingPersonId) {
    const mp = await supabaseAdmin
        .from('missing_persons')
        .select('missing_person_id,full_name,last_seen_location,user_id')
        .eq('missing_person_id', missingPersonId)
        .maybeSingle();
    if (mp.error || !mp.data) {
        throw new Error('Missing person not found');
    }
    return _scanAndInsertForCase(mp.data);
}

async function _scanAndInsertForCase(missingPersonRow) {
    const sightings = await searchSocialMediaSightings(
        missingPersonRow.full_name,
        missingPersonRow.last_seen_location
    );
    let created = 0;
    for (const sighting of sightings) {
        const detectedAt = sighting.timestamp || sighting.createdAt || new Date().toISOString();
        const insert = await supabaseAdmin.from('detections').insert({
            missing_person_id: missingPersonRow.missing_person_id,
            camera_id: null,
            camera_id_text: null,
            track_id: `social-${Date.now()}-${Math.round(Math.random() * 100000)}`,
            source: 'social_media',
            confidence: 0.6,
            face_score: 0.6,
            clothing_score: 0.6,
            snapshot_url: sighting.displayUrl || sighting.url || null,
            detection_timestamp: new Date(detectedAt).toISOString(),
            bbox: null,
        }).select('detection_id').single();
        if (!insert.error && insert.data) {
            created += 1;
        }
    }
    return created;
}

function startSocialScanCron() {
    cron.schedule('0 */6 * * *', async () => {
        try {
            const result = await supabaseAdmin
                .from('missing_persons')
                .select('missing_person_id,full_name,last_seen_location,user_id')
                .eq('status', 'active');
            if (result.error) {
                logger.error('Social scan fetch cases failed', { error: result.error.message });
                return;
            }
            for (const row of result.data || []) {
                try {
                    await _scanAndInsertForCase(row);
                } catch (inner) {
                    logger.error('Social scan case failed', {
                        caseId: row.missing_person_id,
                        error: inner.message,
                    });
                }
            }
        } catch (error) {
            logger.error('Social scan cron failed', { error: error.message });
        }
    });
}

function _hashtags(name, location) {
    const parts = [];
    if (name) {
        parts.push(name.replace(/\s+/g, '').toLowerCase());
    }
    if (location) {
        parts.push(location.replace(/\s+/g, '').toLowerCase());
    }
    if (!parts.length) return ['missingperson'];
    return parts.map((p) => (p.startsWith('#') ? p : `#${p}`));
}

module.exports = {
    searchSocialMediaSightings,
    searchSocialMediaSightingsForCase,
    startSocialScanCron,
};
