const express = require('express');
const router = express.Router();
const { authenticate } = require('../middleware/authMiddleware');
const {
    registerDeviceToken,
    sendNotification,
    getNotifications,
    markNotificationRead,
} = require('../controllers/notificationController');

router.post('/device-token', registerDeviceToken);
router.post('/', authenticate, sendNotification);
router.post('/send', authenticate, sendNotification);
router.get('/', authenticate, getNotifications);
router.patch('/:id/read', authenticate, markNotificationRead);

module.exports = router;
