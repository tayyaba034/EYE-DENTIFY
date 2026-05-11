const logger = require('./loggerService');
const GEMINI_MODEL = process.env.GEMINI_MODEL || 'gemini-1.5-flash-latest';

async function generateAlertSummaryGemini(payload) {
    const apiKey = process.env.GEMINI_API_KEY;
    if (!apiKey) return null;

    const prompt = [
        'You are an alert system for missing persons. Generate a clear, urgent, 2-sentence alert summary for emergency responders.',
        `Missing person: ${payload.name}, Age: ${payload.age}, Last seen: ${payload.lastSeenLocation}`,
        `Detection: Camera ${payload.cameraName} at ${payload.location}, Time: ${payload.detectedAt}`,
        `Similarity score: ${payload.score}%, Clothing match: ${payload.clothingScore}%`,
        'Output only the summary. No preamble.',
    ].join('\n');

    const url = `https://generativelanguage.googleapis.com/v1beta/models/${GEMINI_MODEL}:generateContent?key=${apiKey}`;
    const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            contents: [{ parts: [{ text: prompt }] }],
        }),
    });
    if (!response.ok) {
        const text = await response.text();
        logger.error('Gemini summary failed', { status: response.status, body: text });
        return null;
    }
    const data = await response.json();
    const text = data?.candidates?.[0]?.content?.parts?.[0]?.text || null;
    return text ? String(text).trim() : null;
}

async function generateCaseDescriptionGemini(fields) {
    const apiKey = process.env.GEMINI_API_KEY;
    if (!apiKey) {
        throw new Error('GEMINI_API_KEY is missing');
    }

    const prompt = [
        'Write a polished public missing-person case description in 2-3 paragraphs.',
        'Tone: factual, compassionate, no speculation.',
        `Name: ${fields.name || 'Unknown'}`,
        `Age: ${fields.age || 'Unknown'}`,
        `Gender: ${fields.gender || 'Unknown'}`,
        `Last seen location: ${fields.last_seen_location || 'Unknown'}`,
        `Last seen date: ${fields.last_seen_date || 'Unknown'}`,
        `Clothing: ${fields.clothing_description || 'Unknown'}`,
        `Distinguishing features: ${fields.distinguishing_features || 'Unknown'}`,
        'Output only the final description.',
    ].join('\n');

    const url = `https://generativelanguage.googleapis.com/v1beta/models/${GEMINI_MODEL}:generateContent?key=${apiKey}`;
    const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            contents: [{ parts: [{ text: prompt }] }],
        }),
    });

    if (!response.ok) {
        const text = await response.text();
        throw new Error(`Gemini API failed: ${response.status} ${text}`);
    }
    const data = await response.json();
    const output = data?.candidates?.[0]?.content?.parts?.[0]?.text;
    if (!output) throw new Error('Gemini returned empty output');
    return String(output).trim();
}

module.exports = {
    generateAlertSummaryGemini,
    generateCaseDescriptionGemini,
};
