const { supabaseAdmin } = require('../config/database');
const logger = require('./loggerService');
const realtimeHub = require('./realtimeHub');

const DEFAULT_INTERVAL_MS = 30000;

async function _expireLevel(level, minutes) {
    const cutoff = new Date(Date.now() - minutes * 60 * 1000).toISOString();
    const { data, error } = await supabaseAdmin
        .from('alerts')
        .update({ status: 'expired' })
        .eq('alert_level', level)
        .not('status', 'in', '(acknowledged,dismissed,expired)')
        .lt('last_seen_time', cutoff)
        .select('alert_id,status,alert_level,last_seen_time');
    if (error) throw error;
    return data || [];
}

async function runExpirySweep() {
    try {
        const expired = [];
        expired.push(...await _expireLevel('preliminary', 2));
        expired.push(...await _expireLevel('tracking', 5));
        expired.push(...await _expireLevel('strong_match', 10));
        expired.forEach((alert) => {
            realtimeHub.broadcast({
                type: 'alert_updated',
                payload: { alert },
            });
        });
    } catch (error) {
        logger.error('Alert expiry sweep failed', { error: error.message });
    }
}

function startAlertExpiryWorker({ intervalMs } = {}) {
    const every = intervalMs || DEFAULT_INTERVAL_MS;
    setInterval(runExpirySweep, every);
    logger.info(`Alert expiry worker started (${every}ms)`);
}

module.exports = {
    startAlertExpiryWorker,
};
