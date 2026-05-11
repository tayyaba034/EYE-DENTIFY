const { supabaseAdmin, supabaseAnon } = require('../config/database');
const logger = require('../services/loggerService');

function _normalizeRole(role) {
    if (!role) return 'user';
    const normalized = String(role).toLowerCase();
    if (['admin', 'security', 'guardian', 'user'].includes(normalized)) {
        return normalized;
    }
    return 'user';
}

async function _fetchProfile(userId) {
    const { data, error } = await supabaseAdmin
        .from('profiles')
        .select('*')
        .eq('id', userId)
        .maybeSingle();
    if (error) throw error;
    return data;
}

const authController = {
    async register(req, res) {
        try {
            const { email, password, role } = req.body;
            const fullName = req.body.full_name || req.body.fullName;
            const normalizedRole = _normalizeRole(role);

            const { data: created, error: createError } = await supabaseAdmin.auth.admin.createUser({
                email,
                password,
                email_confirm: true,
                user_metadata: {
                    full_name: fullName,
                    role: normalizedRole,
                },
            });

            if (createError || !created?.user) {
                return res.status(400).json({ error: createError?.message || 'Registration failed' });
            }

            const userId = created.user.id;
            const { error: profileError } = await supabaseAdmin
                .from('profiles')
                .upsert({
                    id: userId,
                    email,
                    full_name: fullName,
                    role: normalizedRole,
                });

            if (profileError) {
                return res.status(500).json({ error: profileError.message });
            }

            const authClient = supabaseAnon || supabaseAdmin;
            const { data: sessionData, error: signInError } = await authClient.auth.signInWithPassword({
                email,
                password,
            });

            if (signInError || !sessionData?.session) {
                return res.status(201).json({
                    message: 'User created, but login session was not created automatically.',
                    user: {
                        id: userId,
                        email,
                        full_name: fullName,
                        role: normalizedRole,
                    },
                });
            }

            const profile = await _fetchProfile(userId);
            return res.status(201).json({
                access_token: sessionData.session.access_token,
                refresh_token: sessionData.session.refresh_token,
                user: profile,
            });
        } catch (error) {
            logger.error('Register failed', { error: error.message });
            return res.status(500).json({ error: 'Registration failed' });
        }
    },

    async login(req, res) {
        try {
            const { email, password } = req.body;
            const authClient = supabaseAnon || supabaseAdmin;
            const { data, error } = await authClient.auth.signInWithPassword({
                email,
                password,
            });

            if (error || !data?.session || !data?.user) {
                return res.status(401).json({ error: error?.message || 'Invalid credentials' });
            }

            const profile = await _fetchProfile(data.user.id);
            return res.status(200).json({
                access_token: data.session.access_token,
                refresh_token: data.session.refresh_token,
                user: profile,
            });
        } catch (error) {
            logger.error('Login failed', { error: error.message });
            return res.status(500).json({ error: 'Login failed' });
        }
    },

    async refresh(req, res) {
        try {
            const refreshToken = req.body.refresh_token || req.body.refreshToken;
            if (!refreshToken) {
                return res.status(400).json({ error: 'refresh_token is required' });
            }

            const authClient = supabaseAnon || supabaseAdmin;
            const { data, error } = await authClient.auth.refreshSession({
                refresh_token: refreshToken,
            });

            if (error || !data?.session) {
                return res.status(401).json({ error: error?.message || 'Invalid refresh token' });
            }

            return res.status(200).json({
                access_token: data.session.access_token,
                refresh_token: data.session.refresh_token,
            });
        } catch (error) {
            logger.error('Refresh failed', { error: error.message });
            return res.status(500).json({ error: 'Refresh failed' });
        }
    },

    async logout(req, res) {
        try {
            const token = req.user?.token || (req.headers.authorization || '').replace('Bearer ', '');
            if (token) {
                const { error } = await supabaseAdmin.auth.admin.signOut(token);
                if (error) {
                    logger.warn('Supabase signOut warning', { error: error.message });
                }
            }
            return res.status(200).json({ message: 'Logged out successfully' });
        } catch (error) {
            logger.error('Logout failed', { error: error.message });
            return res.status(500).json({ error: 'Logout failed' });
        }
    },

    async me(req, res) {
        try {
            const token = (req.headers.authorization || '').replace('Bearer ', '');
            if (!token) {
                return res.status(401).json({ error: 'Authentication required' });
            }
            const { data, error } = await supabaseAdmin.auth.getUser(token);
            if (error || !data?.user) {
                return res.status(403).json({ error: 'Invalid token' });
            }
            const profile = await _fetchProfile(data.user.id);
            return res.status(200).json(profile);
        } catch (error) {
            logger.error('Get me failed', { error: error.message });
            return res.status(500).json({ error: 'Failed to load profile' });
        }
    },

    async forgotPassword(req, res) {
        try {
            const { email } = req.body;
            if (!email) {
                return res.status(400).json({ error: 'email is required' });
            }
            const authClient = supabaseAnon || supabaseAdmin;
            const { error } = await authClient.auth.resetPasswordForEmail(email);
            if (error) {
                return res.status(400).json({ error: error.message });
            }
            return res.status(200).json({ message: 'Password reset email sent' });
        } catch (error) {
            logger.error('Forgot password failed', { error: error.message });
            return res.status(500).json({ error: 'Failed to send password reset email' });
        }
    },
};

module.exports = authController;
