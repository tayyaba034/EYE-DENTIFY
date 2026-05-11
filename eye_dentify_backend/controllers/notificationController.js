const admin = require('../services/firebaseAdmin');
const logger = require('../services/loggerService');
const tokenStore = require('../services/tokenStore');
const { supabaseAdmin } = require('../config/database');
const realtimeHub = require('../services/realtimeHub');

async function registerDeviceToken(req, res) {
    const { token } = req.body;
    const userId = req.user?.userId || null;
    if (!token) {
        return res.status(400).json({ error: 'token is required' });
    }

    tokenStore.add(token);
    await supabaseAdmin.from('device_tokens').upsert({
        user_id: userId,
        token,
        updated_at: new Date().toISOString(),
    });

    return res.status(200).json({ message: 'Token registered' });
}

async function sendNotification(req, res) {
    const { token, user_id, title, body, type, metadata } = req.body;
    const targetToken = token || tokenStore.getLatest();

    if (!targetToken) {
        return res.status(400).json({ error: 'token is required' });
    }

    const message = {
        notification: {
            title: title || 'Eye-Dentify Alert',
            body: body || 'Test notification working',
        },
        token: targetToken,
    };

    try {
        const response = await admin.messaging().send(message);
        logger.info('Notification sent', { response });

        if (user_id) {
            await supabaseAdmin.from('notifications').insert({
                user_id,
                title: message.notification.title,
                body: message.notification.body,
                type: type || 'system',
                metadata: metadata || {},
            });
            realtimeHub.broadcast({
                type: 'notification_created',
                payload: { user_id },
            });
        }
        return res.status(200).json({ message: 'Notification sent', response });
    } catch (error) {
        logger.error('FCM send failed', { error: error.message });
        return res.status(500).json({ error: 'Failed to send notification' });
    }
}

async function getNotifications(req, res) {
    const userId = req.user?.userId;
    if (!userId) return res.status(401).json({ error: 'Authentication required' });
    const { data, error } = await supabaseAdmin
        .from('notifications')
        .select('*')
        .eq('user_id', userId)
        .order('created_at', { ascending: false });
    if (error) return res.status(400).json({ error: error.message });
    return res.status(200).json(data || []);
}

async function markNotificationRead(req, res) {
    const userId = req.user?.userId;
    const id = req.params.id;
    if (!userId) return res.status(401).json({ error: 'Authentication required' });
    const { data, error } = await supabaseAdmin
        .from('notifications')
        .update({ read_at: new Date().toISOString() })
        .eq('id', id)
        .eq('user_id', userId)
        .select('*')
        .maybeSingle();
    if (error) return res.status(400).json({ error: error.message });
    if (!data) return res.status(404).json({ error: 'Notification not found' });
    realtimeHub.broadcast({
        type: 'notification_updated',
        payload: { user_id: userId },
    });
    return res.status(200).json(data);
}

module.exports = {
    registerDeviceToken,
    sendNotification,
    getNotifications,
    markNotificationRead,
};
