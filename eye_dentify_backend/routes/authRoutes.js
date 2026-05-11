const express = require('express');
const router = express.Router();
const authController = require('../controllers/authController');
const { validate, loginSchema, registerSchema } = require('../middleware/validationMiddleware');
const { authRateLimiter } = require('../middleware/securityMiddleware');
const { authenticate } = require('../middleware/authMiddleware');

router.post('/login', authRateLimiter, validate(loginSchema), authController.login);
router.post('/register', authRateLimiter, validate(registerSchema), authController.register);
router.post('/refresh', authController.refresh);
router.post('/logout', authenticate, authController.logout);
router.get('/me', authenticate, authController.me);
router.post('/forgot-password', authController.forgotPassword);

module.exports = router;
