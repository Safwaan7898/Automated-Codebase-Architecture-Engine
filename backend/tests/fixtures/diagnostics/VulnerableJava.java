package com.example.vulnerable;

import java.io.File;
import java.io.FileInputStream;
import java.io.ObjectInputStream;
import java.security.MessageDigest;
import javax.crypto.Cipher;
import javax.net.ssl.HttpsURLConnection;
import javax.net.ssl.SSLContext;
import javax.net.ssl.TrustManager;
import javax.net.ssl.X509TrustManager;
import java.security.cert.X509Certificate;
import java.sql.Connection;
import java.sql.Statement;

public class VulnerableJava {

    // 1. Hardcoded Secret
    private String apiKey = "AKIAIOSFODNN7EXAMPLE";

    public void queryAccount(Connection conn, String accountId) throws Exception {
        // 2. SQL built by string concatenation
        Statement stmt = conn.createStatement();
        stmt.executeQuery("SELECT * FROM accounts WHERE id = '" + accountId + "'");
    }

    public void hashAndEncrypt(byte[] data, byte[] key) throws Exception {
        // 3. Weak crypto (MD5, DES)
        MessageDigest md = MessageDigest.getInstance("MD5");
        MessageDigest sha1 = MessageDigest.getInstance("SHA-1");
        Cipher cipher = Cipher.getInstance("DES/CBC/PKCS5Padding");
    }

    public Object deserializeData(FileInputStream fis) throws Exception {
        // 4. Insecure deserialization (ObjectInputStream)
        ObjectInputStream ois = new ObjectInputStream(fis);
        return ois.readObject();
    }

    public void runSystemCommand(String cmd) throws Exception {
        // 5. Command injection (Runtime.exec)
        Runtime.getRuntime().exec("sh -c " + cmd);
    }

    public File openUserData(String baseDir, String userInput) {
        // 6. Path traversal
        return new File(baseDir + "/" + userInput);
    }

    public void disableTlsChecks() {
        // 7. Disabled TLS verification
        HttpsURLConnection.setDefaultHostnameVerifier((hostname, session) -> true);

        TrustManager[] trustAllCerts = new TrustManager[] {
            new X509TrustManager() {
                public X509Certificate[] getAcceptedIssuers() { return null; }
                public void checkClientTrusted(X509Certificate[] certs, String authType) { }
                public void checkServerTrusted(X509Certificate[] certs, String authType) { }
            }
        };
    }
}
