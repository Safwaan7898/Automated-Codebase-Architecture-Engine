package com.example.clean;

import java.io.File;
import java.io.FileInputStream;
import java.security.MessageDigest;
import javax.crypto.Cipher;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;

public class CleanJava {

    // 1. Clean Secret: retrieved from environment
    private String apiKey = System.getenv("API_KEY");

    public void queryAccount(Connection conn, String accountId) throws Exception {
        // 2. Clean SQL: PreparedStatement
        String sql = "SELECT * FROM accounts WHERE id = ?";
        try (PreparedStatement ps = conn.prepareStatement(sql)) {
            ps.setString(1, accountId);
            try (ResultSet rs = ps.executeQuery()) {
                // Process results
            }
        }
    }

    public void hashAndEncrypt(byte[] data, byte[] key) throws Exception {
        // 3. Clean crypto: SHA-256 and AES-GCM
        MessageDigest md = MessageDigest.getInstance("SHA-256");
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
    }

    public void runSystemCommand(String host) throws Exception {
        // 5. Clean command execution: ProcessBuilder with arguments
        ProcessBuilder pb = new ProcessBuilder("ping", "-c", "1", host);
        pb.start();
    }

    public File openUserData(File baseDir, String userInput) throws Exception {
        // 6. Clean path traversal check: canonical path check
        File file = new File(baseDir, userInput);
        if (!file.getCanonicalPath().startsWith(baseDir.getCanonicalPath())) {
            throw new SecurityException("Path traversal attempt detected");
        }
        return file;
    }
}
