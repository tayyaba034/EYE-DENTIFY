const logger = require('../services/loggerService');

/**
 * Global Error Handler
 */
const errorHandler = (err, req, res, next) => {
    const statusCode = err.status || 500;

    // Log error (safe logging - no sensitive data)
    logger.error('API Error', {
        message: err.message,
        stack: process.env.NODE_ENV === 'production' ? null : err.stack,
        path: req.path,
        method: req.method,
        userId: req.user?.userId
    });

    res.status(statusCode).json({
        error: process.env.NODE_ENV === 'production'
            ? 'An internal server error occurred'
            : err.message
    });
};

/**
 * Logging Middleware
 */
const requestLogger = (req, res, next) => {
    // Safe logging: Never log passwords, tokens, or full objects
    const { password, token, refreshToken, ...safeBody } = req.body || {};

    logger.info('Inbound Request', {
        method: req.method,
        path: req.path,
        body: Object.keys(safeBody).length > 0 ? safeBody : null,
        userId: req.user?.userId
    });
    next();
};

module.exports = { errorHandler, requestLogger };
