const rateLimit = require('express-rate-limit');
const helmet = require('helmet');
const cors = require('cors');

// Security Headers
const securityHeaders = helmet();

// CORS Configuration
const corsConfig = cors({
    origin: process.env.ALLOWED_ORIGINS ? process.env.ALLOWED_ORIGINS.split(',') : '*',
    methods: ['GET', 'POST', 'PUT', 'DELETE'],
    allowedHeaders: ['Content-Type', 'Authorization', 'x-api-key'],
    credentials: true,
});

// Rate Limiting
const isDev = process.env.NODE_ENV !== 'production';

const authRateLimiter = rateLimit({
    windowMs: 15 * 60 * 1000, // 15 minutes
    max: isDev ? 1000 : 5, // Relax limits in development
    message: { error: 'Too many attempts, please try again later' },
    standardHeaders: true,
    legacyHeaders: false,
});

const apiRateLimiter = rateLimit({
    windowMs: 60 * 1000, // 1 minute
    max: 100, // Limit each IP to 100 requests per minute
    standardHeaders: true,
    legacyHeaders: false,
});

module.exports = {
    securityHeaders,
    corsConfig,
    authRateLimiter,
    apiRateLimiter,
};
