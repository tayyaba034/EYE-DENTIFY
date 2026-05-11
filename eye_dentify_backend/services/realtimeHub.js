const { EventEmitter } = require('events');
const { WebSocketServer } = require('ws');
const logger = require('./loggerService');
const { supabaseAdmin } = require('../config/database');

class RealtimeHub extends EventEmitter {
    constructor() {
        super();
        this._wss = null;
        this._supabaseChannel = null;
    }

    attach(server) {
        if (this._wss) return;
        this._wss = new WebSocketServer({ server, path: '/ws' });

        this._wss.on('connection', (socket) => {
            logger.info('WebSocket client connected');
            socket.on('close', () => {
                logger.info('WebSocket client disconnected');
            });
        });

        this._subscribeAlertsRealtime();
    }

    _subscribeAlertsRealtime() {
        if (this._supabaseChannel) return;

        this._supabaseChannel = supabaseAdmin
            .channel('alerts-changes')
            .on(
                'postgres_changes',
                { event: '*', schema: 'public', table: 'alerts' },
                (payload) => {
                    const event = payload.eventType === 'INSERT'
                        ? 'alert_created'
                        : 'alert_updated';
                    this.broadcast({
                        type: event,
                        payload: {
                            source: 'supabase_realtime',
                            record: payload.new || payload.old,
                        },
                    });
                }
            )
            .subscribe((status) => {
                logger.info('Supabase alerts realtime status', { status });
            });
    }

    broadcast(payload) {
        if (!this._wss) return;
        const message = JSON.stringify(payload);
        this._wss.clients.forEach((client) => {
            if (client.readyState === 1) {
                client.send(message);
            }
        });
    }
}

module.exports = new RealtimeHub();
