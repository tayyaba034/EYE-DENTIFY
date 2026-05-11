const express = require('express');
const router = express.Router();
const {
    ingestDetection,
    getDetectionById,
    verifyDetection,
} = require('../controllers/detectionsController');
const { authenticate } = require('../middleware/authMiddleware');

router.post('/ingest', ingestDetection);
router.get('/:id', authenticate, getDetectionById);
router.post('/:id/verify', authenticate, verifyDetection);

module.exports = router;
