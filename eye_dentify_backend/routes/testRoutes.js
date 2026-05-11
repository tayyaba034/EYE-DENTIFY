const express = require('express');
const router = express.Router();
const { authenticate, authorize } = require('../middleware/authMiddleware');
const { encrypt, decrypt } = require('../services/encryptionService');
const { apiRateLimiter } = require('../middleware/securityMiddleware');


router.get('/alerts/confidential',
    apiRateLimiter,
    authenticate,
    authorize(['security', 'admin']),
    async (req, res) => {
        // Sensitive data that should be encrypted in DB
        const sensitiveLocation = '33.6844° N, 73.0479° E (Private Residence)';
        const encryptedLocation = encrypt(sensitiveLocation);

        // Simulate reading from DB and decrypting for authorized user
        res.json({
            message: 'Secure Alert Details',
            payload: {
                id: 'AL-12345',
                type: 'Missing Person Match',
                encryptedDataPreview: encryptedLocation, // Show what it looks like in DB
                decryptedLocation: decrypt(encryptedLocation), // Real data for security personnel
                accessedBy: req.user.userId,
                role: req.user.role
            }
        });
    });

router.get('/cases/:caseId',
    authenticate,
    authorize(['guardian', 'admin']),
    (req, res) => {
        const { caseId } = req.params;

        // Server-side enforcement: Guardian must be the owner
        // This would typically involve a DB check: SELECT * FROM cases WHERE id = $1 AND user_id = $2
        const isOwner = true; // Logic: db.getCase(caseId).userId === req.user.userId

        if (!isOwner && req.user.role !== 'admin') {
            return res.status(403).json({ error: 'Access denied to this case' });
        }

        res.json({ message: `Details for case ${caseId}` });
    });

module.exports = router;
