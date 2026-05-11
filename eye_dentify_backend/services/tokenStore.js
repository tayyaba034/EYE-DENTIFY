const tokens = new Set();
let latestToken = null;

function add(token) {
    tokens.add(token);
    latestToken = token;
}

function getLatest() {
    return latestToken;
}

function getAll() {
    return Array.from(tokens);
}

module.exports = {
    add,
    getLatest,
    getAll,
};
