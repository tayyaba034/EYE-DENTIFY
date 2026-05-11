const { supabaseAdmin } = require('../config/database');
const logger = require('../services/loggerService');
const realtimeHub = require('../services/realtimeHub');
const { uploadPhotoFileToSupabase } = require('../services/firebaseDelivery');
const { generateCaseDescriptionGemini } = require('../services/aiService');
const { searchSocialMediaSightingsForCase } = require('../services/apifyScraper');

async function _getPhotos(missingPersonId) {
    const { data } = await supabaseAdmin
        .from('media')
        .select('file_path')
        .eq('missing_person_id', missingPersonId)
        .order('upload_timestamp', { ascending: false });
    return (data || []).map((row) => row.file_path);
}

async function _mapMissingPersonRow(row) {
    if (!row) return null;
    const photos = await _getPhotos(row.missing_person_id);
    return {
        missing_person_id: row.missing_person_id,
        user_id: row.user_id,
        full_name: row.full_name,
        age: row.age,
        gender: row.gender,
        height_cm: row.height_cm,
        height_range_min: row.height_range_min,
        height_range_max: row.height_range_max,
        last_seen_location: row.last_seen_location,
        last_seen_datetime: row.last_seen_datetime,
        clothing_description: row.clothing_description,
        additional_notes: row.additional_notes,
        status: row.status,
        created_at: row.created_at,
        updated_at: row.updated_at,
        photos,
    };
}

async function uploadPhoto(req, res) {
    try {
        if (!req.file) {
            return res.status(400).json({ error: 'photo file is required' });
        }
        const publicUrl = await uploadPhotoFileToSupabase({ file: req.file });
        if (!publicUrl) {
            return res.status(500).json({ error: 'Failed to upload photo' });
        }
        return res.status(200).json({ url: publicUrl });
    } catch (error) {
        logger.error('Upload photo failed', { error: error.message });
        return res.status(500).json({ error: 'Failed to upload photo' });
    }
}

async function createMissingPerson(req, res) {
    const userId = req.user?.userId;
    if (!userId) {
        return res.status(401).json({ error: 'Authentication required' });
    }

    const payload = req.body || {};
    const {
        full_name,
        age,
        gender,
        height_cm,
        height_range_min,
        height_range_max,
        last_seen_location,
        last_seen_datetime,
        clothing_description,
        additional_notes,
        status,
        photos,
    } = payload;

    if (!full_name) {
        return res.status(400).json({ error: 'full_name is required' });
    }

    try {
        const insert = await supabaseAdmin
            .from('missing_persons')
            .insert({
                user_id: userId,
                full_name,
                age: age ?? null,
                gender: gender ?? null,
                height_cm: height_cm ?? null,
                height_range_min: height_range_min ?? null,
                height_range_max: height_range_max ?? null,
                last_seen_location: last_seen_location ?? null,
                last_seen_datetime: last_seen_datetime ?? null,
                clothing_description: clothing_description ?? null,
                additional_notes: additional_notes ?? null,
                status: status ?? 'active',
            })
            .select('*')
            .single();

        if (insert.error || !insert.data) {
            return res.status(400).json({ error: insert.error?.message || 'Failed to create case' });
        }
        const created = insert.data;

        if (Array.isArray(photos) && photos.length) {
            for (const url of photos) {
                await supabaseAdmin.from('media').insert({
                    missing_person_id: created.missing_person_id,
                    file_path: url,
                    file_type: 'image',
                });
            }
        }

        const response = await _mapMissingPersonRow(created);
        realtimeHub.broadcast({
            type: 'case_created',
            payload: { case: response },
        });
        return res.status(201).json(response);
    } catch (error) {
        logger.error('Create missing person failed', { error: error.message });
        return res.status(500).json({ error: 'Failed to report missing person' });
    }
}

async function getMyCases(req, res) {
    const userId = req.user?.userId;
    if (!userId) {
        return res.status(401).json({ error: 'Authentication required' });
    }

    try {
        const result = await supabaseAdmin
            .from('missing_persons')
            .select('*')
            .eq('user_id', userId)
            .order('created_at', { ascending: false });
        if (result.error) return res.status(400).json({ error: result.error.message });
        const output = [];
        for (const row of result.data || []) {
            output.push(await _mapMissingPersonRow(row));
        }
        return res.status(200).json(output);
    } catch (error) {
        logger.error('Fetch my cases failed', { error: error.message });
        return res.status(500).json({ error: 'Failed to fetch your cases' });
    }
}

async function getAllCases(req, res) {
    const status = req.query.status;
    try {
        let query = supabaseAdmin.from('missing_persons').select('*').order('created_at', { ascending: false });
        if (status) query = query.eq('status', status);
        const result = await query;
        if (result.error) return res.status(400).json({ error: result.error.message });
        const output = [];
        for (const row of result.data || []) {
            output.push(await _mapMissingPersonRow(row));
        }
        return res.status(200).json(output);
    } catch (error) {
        logger.error('Fetch cases failed', { error: error.message });
        return res.status(500).json({ error: 'Failed to fetch cases' });
    }
}

async function getCaseById(req, res) {
    const id = Number(req.params.id);
    if (!id) {
        return res.status(400).json({ error: 'Invalid case id' });
    }
    try {
        const result = await supabaseAdmin
            .from('missing_persons')
            .select('*')
            .eq('missing_person_id', id)
            .maybeSingle();
        if (result.error) return res.status(400).json({ error: result.error.message });
        if (!result.data) return res.status(404).json({ error: 'Case not found' });
        const response = await _mapMissingPersonRow(result.data);
        return res.status(200).json(response);
    } catch (error) {
        logger.error('Fetch case failed', { error: error.message });
        return res.status(500).json({ error: 'Failed to fetch case' });
    }
}

async function updateCase(req, res) {
    const userId = req.user?.userId;
    const id = Number(req.params.id);
    if (!userId || !id) {
        return res.status(400).json({ error: 'Invalid request' });
    }

    const payload = req.body || {};
    try {
        const patch = {
            updated_at: new Date().toISOString(),
        };
        const fields = [
            'full_name', 'age', 'gender', 'height_cm', 'height_range_min', 'height_range_max',
            'last_seen_location', 'last_seen_datetime', 'clothing_description', 'additional_notes',
            'status',
        ];
        fields.forEach((field) => {
            if (payload[field] !== undefined) patch[field] = payload[field];
        });

        const result = await supabaseAdmin
            .from('missing_persons')
            .update(patch)
            .eq('missing_person_id', id)
            .eq('user_id', userId)
            .select('*')
            .maybeSingle();

        if (result.error) return res.status(400).json({ error: result.error.message });
        if (!result.data) return res.status(404).json({ error: 'Case not found' });

        const response = await _mapMissingPersonRow(result.data);
        realtimeHub.broadcast({
            type: 'case_updated',
            payload: { case: response },
        });
        return res.status(200).json(response);
    } catch (error) {
        logger.error('Update case failed', { error: error.message });
        return res.status(500).json({ error: 'Failed to update case' });
    }
}

async function deleteCase(req, res) {
    const userId = req.user?.userId;
    const id = Number(req.params.id);
    if (!userId || !id) {
        return res.status(400).json({ error: 'Invalid request' });
    }
    try {
        const result = await supabaseAdmin
            .from('missing_persons')
            .delete()
            .eq('missing_person_id', id)
            .eq('user_id', userId)
            .select('missing_person_id')
            .maybeSingle();
        if (result.error) return res.status(400).json({ error: result.error.message });
        if (!result.data) return res.status(404).json({ error: 'Case not found' });
        realtimeHub.broadcast({
            type: 'case_deleted',
            payload: { missing_person_id: result.data.missing_person_id },
        });
        return res.status(200).json({ success: true });
    } catch (error) {
        logger.error('Delete case failed', { error: error.message });
        return res.status(500).json({ error: 'Failed to delete case' });
    }
}

async function generateDescription(req, res) {
    try {
        const output = await generateCaseDescriptionGemini(req.body || {});
        return res.status(200).json({ description: output });
    } catch (error) {
        logger.error('Generate description failed', { error: error.message });
        return res.status(500).json({ error: 'Failed to generate description' });
    }
}

async function scanSocial(req, res) {
    try {
        const id = Number(req.params.id);
        if (!id) return res.status(400).json({ error: 'Invalid case id' });
        const created = await searchSocialMediaSightingsForCase(id);
        return res.status(200).json({ success: true, created });
    } catch (error) {
        logger.error('Social scan failed', { error: error.message });
        return res.status(500).json({ error: 'Failed to scan social media' });
    }
}

module.exports = {
    uploadPhoto,
    createMissingPerson,
    getMyCases,
    getAllCases,
    getCaseById,
    updateCase,
    deleteCase,
    generateDescription,
    scanSocial,
};
