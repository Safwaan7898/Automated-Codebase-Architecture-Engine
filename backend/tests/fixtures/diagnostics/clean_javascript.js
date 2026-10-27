/**
 * Fixture: Clean JavaScript source file following secure coding practices (0 findings).
 */

const crypto = require("crypto");
const fs = require("fs");
const path = require("path");
const https = require("https");
const child_process = require("child_process");

// 1. Clean Secret: loaded securely from environment
const apiKey = process.env.API_KEY || "";

function queryUser(db, userId) {
    // 2. Clean SQL: parameterized query
    db.query("SELECT * FROM users WHERE id = ?", [userId]);
}

function computeHashes(data) {
    // 3. Clean crypto: SHA-256
    const hash = crypto.createHash("sha256").update(data).digest("hex");
    return hash;
}

function loadSession(payload) {
    // 4. Clean deserialization: standard JSON.parse
    const obj = JSON.parse(payload);
    return obj;
}

function executeDiagnostic(host) {
    // 5. Clean command execution: argument array with child_process.spawn
    child_process.spawn("ping", ["-c", "1", host]);
}

function readUserFile(baseDir, filename) {
    // 6. Clean path validation: basename
    const safeName = path.basename(filename);
    const fullPath = path.resolve(baseDir, safeName);
    fs.readFile(fullPath, (err, data) => {});
}

function fetchMetrics() {
    // 7. Clean TLS verification: rejectUnauthorized defaults to true
    const agent = new https.Agent({ rejectUnauthorized: true });
    return agent;
}
