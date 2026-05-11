const { supabaseAdmin } = require('../config/database');
const logger = require('../services/loggerService');

async function authenticate(req, res, next) {
    const authHeader = req.headers.authorization;
    if (!authHeader?.startsWith('Bearer ')) {
        return res.status(401).json({ error: 'Authentication required' });
    }

    const token = authHeader.slice('Bearer '.length);

    try {
        const { data, error } = await supabaseAdmin.auth.getUser(token);
        if (error || !data?.user) {
            return res.status(403).json({ error: 'Invalid token' });
        }

        const user = data.user;
        const role = user.user_metadata?.role || 'user';
        req.user = {
            userId: user.id,
            email: user.email,
            role,
            token,
        };
        return next();
    } catch (error) {
        logger.error('Supabase token verification failed', { error: error.message });
        return res.status(500).json({ error: 'Authentication failed' });
    }
}

function authorize(allowedRoles) {
    return (req, res, next) => {
        if (!req.user || !allowedRoles.includes(req.user.role)) {
            return res.status(403).json({ error: 'Insufficient permissions' });
        }
        return next();
    };
}

module.exports = { authenticate, authorize };
