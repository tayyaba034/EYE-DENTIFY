const path = require('path');
const admin = require('./firebaseAdmin');
const logger = require('./loggerService');
const { supabaseAdmin } = require('../config/database');

async function sendAlertPush({ token, title, body, data }) {
    if (!token) return;
    try {
        await admin.messaging().send({
            notification: { title, body },
            data: _stringifyData(data || {}),
            token,
        });
    } catch (error) {
        logger.error('FCM push failed', { error: error.message });
    }
}

async function uploadSnapshotToSupabaseStorage({ buffer, destinationPath, contentType }) {
    try {
        const { error } = await supabaseAdmin.storage
            .from('missing-persons-media')
            .upload(destinationPath, buffer, {
                contentType: contentType || 'image/jpeg',
                upsert: true,
            });

        if (error) {
            logger.error('Supabase storage upload failed', { error: error.message });
            return null;
        }

        const { data } = supabaseAdmin.storage
            .from('missing-persons-media')
            .getPublicUrl(destinationPath);
        return data?.publicUrl || null;
    } catch (error) {
        logger.error('Supabase storage upload failed', { error: error.message });
        return null;
    }
}

async function uploadPhotoFileToSupabase({ file }) {
    const extension = path.extname(file.originalname || '').toLowerCase() || '.jpg';
    const filePath = `reports/${Date.now()}-${Math.round(Math.random() * 1e9)}${extension}`;
    return uploadSnapshotToSupabaseStorage({
        buffer: file.buffer,
        destinationPath: filePath,
        contentType: file.mimetype || 'image/jpeg',
    });
}

function _stringifyData(data) {
    const output = {};
    Object.entries(data).forEach(([key, value]) => {
        output[key] = value == null ? '' : String(value);
    });
    return output;
}

module.exports = {
    sendAlertPush,
    uploadSnapshotToSupabaseStorage,
    uploadPhotoFileToSupabase,
};
