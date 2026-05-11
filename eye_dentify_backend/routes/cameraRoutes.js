const express = require('express');
const router = express.Router();
const { authenticate, authorize } = require('../middleware/authMiddleware');
const {
    getCameras,
    getCameraById,
    createCamera,
    updateCamera,
    deleteCamera,
} = require('../controllers/cameraController');

router.get('/', authenticate, getCameras);
router.get('/:id', authenticate, getCameraById);
router.post('/', authenticate, authorize(['admin']), createCamera);
router.put('/:id', authenticate, updateCamera);
router.delete('/:id', authenticate, deleteCamera);

module.exports = router;
