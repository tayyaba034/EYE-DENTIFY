const express = require('express');
const multer = require('multer');
const router = express.Router();
const { authenticate } = require('../middleware/authMiddleware');
const {
    uploadPhoto,
    createMissingPerson,
    getMyCases,
    getAllCases,
    getCaseById,
    updateCase,
    deleteCase,
    generateDescription,
    scanSocial,
} = require('../controllers/missingPersonsController');
const { getDetectionsByMissingPerson } = require('../controllers/detectionsController');

const upload = multer({ storage: multer.memoryStorage() });

router.post('/upload-photo', authenticate, upload.single('photo'), uploadPhoto);
router.post('/generate-description', authenticate, generateDescription);
router.post('/', authenticate, createMissingPerson);
router.get('/my', authenticate, getMyCases);
router.get('/', getAllCases);
router.get('/:id', getCaseById);
router.put('/:id', authenticate, updateCase);
router.delete('/:id', authenticate, deleteCase);
router.get('/:id/detections', authenticate, getDetectionsByMissingPerson);
router.post('/:id/scan-social', authenticate, scanSocial);

module.exports = router;
