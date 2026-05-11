const { supabaseAdmin, rawPg } = require('../config/database');
const logger = require('../services/loggerService');

function _isAdmin(req) {
    return req.user?.role === 'admin';
}

let _orgSupportCache = null;

async function _getOrgSupport() {
    if (_orgSupportCache) return _orgSupportCache;
    const fallback = { cameraOrg: false, profileOrg: false, usersOrg: false };
    if (!rawPg) {
        _orgSupportCache = fallback;
        return _orgSupportCache;
    }
    try {
        const result = await rawPg.query(`
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name IN ('cameras', 'profiles', 'users')
              AND column_name = 'organization_id'
        `);
        const set = new Set(result.rows.map((r) => `${r.table_name}.${r.column_name}`));
        _orgSupportCache = {
            cameraOrg: set.has('cameras.organization_id'),
            profileOrg: set.has('profiles.organization_id'),
            usersOrg: set.has('users.organization_id'),
        };
    } catch {
        _orgSupportCache = fallback;
    }
    return _orgSupportCache;
}

async function _getUserOrganizationId(userId) {
    const support = await _getOrgSupport();
    if (support.profileOrg) {
        const profile = await supabaseAdmin
            .from('profiles')
            .select('organization_id')
            .eq('id', userId)
            .maybeSingle();
        if (!profile.error && profile.data?.organization_id) {
            return profile.data.organization_id;
        }
    }
    if (support.usersOrg) {
        const user = await supabaseAdmin
            .from('users')
            .select('organization_id')
            .eq('id', userId)
            .maybeSingle();
        if (!user.error && user.data?.organization_id) {
            return user.data.organization_id;
        }
    }
    return null;
}

async function getCameras(req, res) {
    try {
        let query = supabaseAdmin.from('cameras').select('*').order('created_at', { ascending: false });
        if (!_isAdmin(req)) {
            const support = await _getOrgSupport();
            if (support.cameraOrg) {
                const orgId = await _getUserOrganizationId(req.user?.userId);
                if (!orgId) {
                    return res.status(403).json({ error: 'Organization not assigned to user' });
                }
                query = query.eq('organization_id', orgId);
            } else {
                query = query.eq('status', 'active');
            }
        }
        const { data, error } = await query;
        if (error) return res.status(400).json({ error: error.message });
        return res.status(200).json((data || []).map(_mapCamera));
    } catch (error) {
        logger.error('Fetch cameras failed', { error: error.message });
        return res.status(500).json({ error: 'Failed to fetch cameras' });
    }
}

async function getCameraById(req, res) {
    try {
        const id = req.params.id;
        let query = supabaseAdmin
            .from('cameras')
            .select('*')
            .eq('id', id);

        if (!_isAdmin(req)) {
            const support = await _getOrgSupport();
            if (support.cameraOrg) {
                const orgId = await _getUserOrganizationId(req.user?.userId);
                if (!orgId) return res.status(403).json({ error: 'Organization not assigned to user' });
                query = query.eq('organization_id', orgId);
            } else {
                query = query.eq('status', 'active');
            }
        }

        const { data, error } = await query.maybeSingle();
        if (error) return res.status(400).json({ error: error.message });
        if (!data) return res.status(404).json({ error: 'Camera not found' });
        return res.status(200).json(_mapCamera(data));
    } catch (error) {
        logger.error('Fetch camera failed', { error: error.message });
        return res.status(500).json({ error: 'Failed to fetch camera' });
    }
}

async function createCamera(req, res) {
    if (!_isAdmin(req)) return res.status(403).json({ error: 'Insufficient role' });
    try {
        const payload = req.body || {};
        const support = await _getOrgSupport();
        const { data, error } = await supabaseAdmin
            .from('cameras')
            .insert({
                name: payload.name,
                location: payload.location,
                lat: payload.lat,
                lng: payload.lng,
                status: payload.status || 'active',
                api_key: payload.api_key || null,
                ...(support.cameraOrg ? { organization_id: payload.organization_id || null } : {}),
            })
            .select('*')
            .single();
        if (error) return res.status(400).json({ error: error.message });
        return res.status(201).json(_mapCamera(data));
    } catch (error) {
        logger.error('Create camera failed', { error: error.message });
        return res.status(500).json({ error: 'Failed to create camera' });
    }
}

async function updateCamera(req, res) {
    try {
        const id = req.params.id;
        const payload = req.body || {};
        let query = supabaseAdmin
            .from('cameras')
            .update({
                name: payload.name,
                location: payload.location,
                lat: payload.lat,
                lng: payload.lng,
                status: payload.status,
                api_key: payload.api_key,
            })
            .eq('id', id);

        if (!_isAdmin(req)) {
            const support = await _getOrgSupport();
            if (support.cameraOrg) {
                const orgId = await _getUserOrganizationId(req.user?.userId);
                if (!orgId) return res.status(403).json({ error: 'Organization not assigned to user' });
                query = query.eq('organization_id', orgId);
            }
        }

        const { data, error } = await query.select('*').maybeSingle();
        if (error) return res.status(400).json({ error: error.message });
        if (!data) return res.status(404).json({ error: 'Camera not found' });
        return res.status(200).json(_mapCamera(data));
    } catch (error) {
        logger.error('Update camera failed', { error: error.message });
        return res.status(500).json({ error: 'Failed to update camera' });
    }
}

async function deleteCamera(req, res) {
    try {
        const id = req.params.id;
        let query = supabaseAdmin
            .from('cameras')
            .update({ status: 'inactive' })
            .eq('id', id);

        if (!_isAdmin(req)) {
            const support = await _getOrgSupport();
            if (support.cameraOrg) {
                const orgId = await _getUserOrganizationId(req.user?.userId);
                if (!orgId) return res.status(403).json({ error: 'Organization not assigned to user' });
                query = query.eq('organization_id', orgId);
            }
        }

        const { data, error } = await query.select('*').maybeSingle();
        if (error) return res.status(400).json({ error: error.message });
        if (!data) return res.status(404).json({ error: 'Camera not found' });
        return res.status(200).json({ success: true });
    } catch (error) {
        logger.error('Delete camera failed', { error: error.message });
        return res.status(500).json({ error: 'Failed to delete camera' });
    }
}

function _mapCamera(row) {
    return {
        id: row.id,
        location: row.location,
        status: row.status,
        latitude: Number(row.lat || 0),
        longitude: Number(row.lng || 0),
        type: row.name || 'Camera',
        name: row.name,
        api_key: row.api_key,
        created_at: row.created_at,
    };
}

module.exports = {
    getCameras,
    getCameraById,
    createCamera,
    updateCamera,
    deleteCamera,
};
