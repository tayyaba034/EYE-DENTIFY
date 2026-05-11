const { z } = require('zod');

const validate = (schema) => {
    return (req, res, next) => {
        try {
            schema.parse({
                body: req.body,
                query: req.query,
                params: req.params,
            });
            return next();
        } catch (error) {
            return res.status(400).json({
                error: 'Validation failed',
                details: error.errors.map((e) => ({ path: e.path, message: e.message })),
            });
        }
    };
};

const loginSchema = z.object({
    body: z.object({
        email: z.string().email(),
        password: z.string().min(8),
    }),
});

const registerSchema = z.object({
    body: z.object({
        email: z.string().email(),
        password: z.string().min(8),
        role: z.string().optional().default('user'),
        full_name: z.string().optional(),
        fullName: z.string().optional(),
    }).refine((body) => Boolean(body.full_name || body.fullName), {
        message: 'full_name or fullName is required',
        path: ['full_name'],
    }),
});

module.exports = { validate, loginSchema, registerSchema };
