const express = require('express');
const router = express.Router();
const {
    getMyAlerts,
    getAlertsSnapshot,
    getAlertById,
    markAsRead,
    acknowledge,
    dismiss,
    confirmMatch,
    rejectMatch,
} = require('../controllers/alertsController');
const { authenticate } = require('../middleware/authMiddleware');

router.get('/my', authenticate, getMyAlerts);
router.get('/snapshot', authenticate, getAlertsSnapshot);
router.get('/:id', authenticate, getAlertById);
router.patch('/:id/read', authenticate, markAsRead);
router.patch('/:id/acknowledge', authenticate, acknowledge);
router.patch('/:id/dismiss', authenticate, dismiss);
router.post('/:id/confirm-match', authenticate, confirmMatch);
router.post('/:id/reject-match', authenticate, rejectMatch);

module.exports = router;
