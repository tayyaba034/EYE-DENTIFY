require('dotenv').config();
const express = require('express');
const http = require('http');
const { securityHeaders, corsConfig, apiRateLimiter } = require('./middleware/securityMiddleware');
const { errorHandler, requestLogger } = require('./middleware/errorMiddleware');
const authRoutes = require('./routes/authRoutes');
const testRoutes = require('./routes/testRoutes');
const notificationRoutes = require('./routes/notificationRoutes');
const alertsRoutes = require('./routes/alertsRoutes');
const detectionsRoutes = require('./routes/detectionsRoutes');
const missingPersonsRoutes = require('./routes/missingPersonsRoutes');
const cameraRoutes = require('./routes/cameraRoutes');
const logger = require('./services/loggerService');
const realtimeHub = require('./services/realtimeHub');
const { startAlertExpiryWorker } = require('./services/alertExpiryWorker');
const { startSocialScanCron } = require('./services/apifyScraper');

const app = express();

app.use(securityHeaders);
app.use(corsConfig);
app.use(express.json({ limit: '10mb' }));
app.use(requestLogger);

app.use('/api', apiRateLimiter);

app.use('/api/auth', authRoutes);
app.use('/api/protected', testRoutes);
app.use('/api/notifications', notificationRoutes);
app.use('/api/notify', notificationRoutes);
app.use('/notifications', notificationRoutes);
app.use('/api/alerts', alertsRoutes);
app.use('/api/detections', detectionsRoutes);
app.use('/api/missing-persons', missingPersonsRoutes);
app.use('/api/cameras', cameraRoutes);

app.use((req, res, next) => {
    if (process.env.NODE_ENV === 'production' && !req.secure && req.get('x-forwarded-proto') !== 'https') {
        return res.redirect(`https://${req.get('host')}${req.url}`);
    }
    return next();
});

app.get('/health', (req, res) => {
    res.status(200).json({ status: 'UP', timestamp: new Date().toISOString() });
});

app.use(errorHandler);

const PORT = process.env.PORT || 5000;
const server = http.createServer(app);
realtimeHub.attach(server);

server.listen(PORT, () => {
    logger.info(`Server running in ${process.env.NODE_ENV} mode on port ${PORT}`);
    startAlertExpiryWorker({
        intervalMs: Number(process.env.ALERT_EXPIRY_INTERVAL_MS || 30000),
    });
    startSocialScanCron();
});

module.exports = app;
