/**
 * Fixture: Vulnerable JavaScript source file seeded with exactly 7 security vulnerabilities (1 per rule).
 */

const crypto = require("crypto");
const fs = require("fs");
const https = require("https");
const child_process = require("child_process");
const serialize = require("node-serialize");

// 1. Hardcoded Secret (SEC-HARDCODED-SECRET)
const apiKey = "AKIAIOSFODNN7EXAMPLE";

function queryUser(db, userId) {
    // 2. SQL injection via string concatenation (SEC-SQL-CONCAT)
    db.query("SELECT * FROM users WHERE id = '" + userId + "'");
}

function computeHashes(data) {
    // 3. Weak crypto (SEC-WEAK-CRYPTO)
    const hash = crypto.createHash("md5").update(data).digest("hex");
    return hash;
}

function loadSession(payload) {
    // 4. Insecure deserialization (SEC-INSECURE-DESERIALIZATION)
    const obj = serialize.unserialize(payload);
    return obj;
}

function executeDiagnostic(host) {
    // 5. Command injection (SEC-COMMAND-INJECTION)
    child_process.exec("ping -c 1 " + host);
}

function readUserFile(filename) {
    // 6. Path traversal (SEC-PATH-TRAVERSAL)
    fs.readFile("/var/data/" + filename, (err, data) => {});
}

function fetchMetrics() {
    // 7. Disabled TLS verification (SEC-DISABLED-TLS)
    const agent = new https.Agent({ rejectUnauthorized: false });
    return agent;
}
