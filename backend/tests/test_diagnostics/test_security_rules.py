"""Tests for AST-based security rules (Python and Java)."""

from pathlib import Path

from diagnostics.models import Severity
from diagnostics.rules.security.command_injection import CommandInjectionRule
from diagnostics.rules.security.disabled_tls import DisabledTlsVerificationRule
from diagnostics.rules.security.hardcoded_secrets import HardcodedSecretsRule
from diagnostics.rules.security.insecure_deserialization import InsecureDeserializationRule
from diagnostics.rules.security.path_traversal import PathTraversalRule
from diagnostics.rules.security.sql_injection import SqlConcatenationRule
from diagnostics.rules.security.weak_crypto import WeakCryptoRule


class TestSqlConcatenationRule:
    rule = SqlConcatenationRule()

    def test_python_sql_concat_detected(self) -> None:
        code = 'q = "SELECT * FROM users WHERE name = \'" + user_input + "\'"\ncursor.execute(q)'
        findings = self.rule.check_file(Path("test.py"), code, "python")
        assert len(findings) >= 1
        assert findings[0].severity == Severity.CRITICAL
        assert "CWE-89" in (findings[0].cwe or "")

    def test_python_fstring_sql_detected(self) -> None:
        code = 'cursor.execute(f"SELECT * FROM items WHERE id = {item_id}")'
        findings = self.rule.check_file(Path("test.py"), code, "python")
        assert len(findings) >= 1

    def test_python_parameterized_sql_clean(self) -> None:
        code = 'cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))'
        findings = self.rule.check_file(Path("test.py"), code, "python")
        assert len(findings) == 0

    def test_python_non_sql_concat_clean(self) -> None:
        code = 'msg = "Hello, " + username + "! Welcome back."'
        findings = self.rule.check_file(Path("test.py"), code, "python")
        assert len(findings) == 0

    def test_java_sql_concat_detected(self) -> None:
        code = """
        class Repo {
            void run(Statement stmt, String id) throws Exception {
                stmt.executeQuery("SELECT * FROM accounts WHERE id = '" + id + "'");
            }
        }
        """
        findings = self.rule.check_file(Path("Repo.java"), code, "java")
        assert len(findings) >= 1

    def test_java_prepared_statement_clean(self) -> None:
        code = """
        class Repo {
            void run(Connection conn, String id) throws Exception {
                PreparedStatement ps = conn.prepareStatement("SELECT * FROM accounts WHERE id = ?");
                ps.setString(1, id);
                ps.executeQuery();
            }
        }
        """
        findings = self.rule.check_file(Path("Repo.java"), code, "java")
        assert len(findings) == 0


class TestHardcodedSecretsRule:
    rule = HardcodedSecretsRule()

    def test_python_hardcoded_api_key_detected(self) -> None:
        code = 'API_KEY = "AKIAIOSFODNN7EXAMPLE"'
        findings = self.rule.check_file(Path("config.py"), code, "python")
        assert len(findings) >= 1
        assert findings[0].severity == Severity.HIGH
        assert "CWE-798" in (findings[0].cwe or "")

    def test_python_placeholder_secret_clean(self) -> None:
        code = 'API_KEY = "CHANGEME"\nSECRET = ""'
        findings = self.rule.check_file(Path("config.py"), code, "python")
        assert len(findings) == 0

    def test_python_env_var_secret_clean(self) -> None:
        code = 'import os\napi_key = os.getenv("API_KEY", "")'
        findings = self.rule.check_file(Path("config.py"), code, "python")
        assert len(findings) == 0


class TestWeakCryptoRule:
    rule = WeakCryptoRule()

    def test_python_hashlib_md5_detected(self) -> None:
        code = "import hashlib\nh = hashlib.md5(b'data').hexdigest()"
        findings = self.rule.check_file(Path("crypto.py"), code, "python")
        assert len(findings) >= 1
        assert "CWE-327" in (findings[0].cwe or "")

    def test_python_des_cipher_detected(self) -> None:
        code = "from Crypto.Cipher import DES\nc = DES.new(key, DES.MODE_ECB)"
        findings = self.rule.check_file(Path("crypto.py"), code, "python")
        assert len(findings) >= 1

    def test_python_sha256_clean(self) -> None:
        code = "import hashlib\nh = hashlib.sha256(b'data').hexdigest()"
        findings = self.rule.check_file(Path("crypto.py"), code, "python")
        assert len(findings) == 0

    def test_java_weak_md5_detected(self) -> None:
        code = 'class H { void m() throws Exception { MessageDigest.getInstance("MD5"); } }'
        findings = self.rule.check_file(Path("H.java"), code, "java")
        assert len(findings) >= 1

    def test_java_sha256_clean(self) -> None:
        code = 'class H { void m() throws Exception { MessageDigest.getInstance("SHA-256"); } }'
        findings = self.rule.check_file(Path("H.java"), code, "java")
        assert len(findings) == 0


class TestInsecureDeserializationRule:
    rule = InsecureDeserializationRule()

    def test_python_pickle_loads_detected(self) -> None:
        code = "import pickle\nobj = pickle.loads(payload)"
        findings = self.rule.check_file(Path("ser.py"), code, "python")
        assert len(findings) >= 1
        assert findings[0].severity == Severity.CRITICAL

    def test_python_yaml_load_unsafe_detected(self) -> None:
        code = "import yaml\nd = yaml.load(raw, Loader=yaml.Loader)"
        findings = self.rule.check_file(Path("ser.py"), code, "python")
        assert len(findings) >= 1

    def test_python_yaml_safe_load_clean(self) -> None:
        code = "import yaml, json\nd = yaml.safe_load(raw)\nj = json.loads(raw)"
        findings = self.rule.check_file(Path("ser.py"), code, "python")
        assert len(findings) == 0

    def test_java_object_input_stream_detected(self) -> None:
        code = """
        class S {
            Object read(FileInputStream fis) throws Exception {
                ObjectInputStream ois = new ObjectInputStream(fis);
                return ois.readObject();
            }
        }
        """
        findings = self.rule.check_file(Path("S.java"), code, "java")
        assert len(findings) >= 1


class TestCommandInjectionRule:
    rule = CommandInjectionRule()

    def test_python_os_system_detected(self) -> None:
        code = "import os\nos.system('ping ' + host)"
        findings = self.rule.check_file(Path("exec.py"), code, "python")
        assert len(findings) >= 1
        assert findings[0].severity == Severity.CRITICAL

    def test_python_subprocess_shell_true_detected(self) -> None:
        code = "import subprocess\nsubprocess.run(user_cmd, shell=True)"
        findings = self.rule.check_file(Path("exec.py"), code, "python")
        assert len(findings) >= 1

    def test_python_subprocess_list_args_clean(self) -> None:
        code = 'import subprocess\nsubprocess.run(["ping", "-c", "1", host], shell=False)'
        findings = self.rule.check_file(Path("exec.py"), code, "python")
        assert len(findings) == 0

    def test_python_subprocess_variable_arg_detected(self) -> None:
        code = "import subprocess\nsubprocess.run(user_cmd, shell=False)"
        findings = self.rule.check_file(Path("exec.py"), code, "python")
        assert len(findings) >= 1

    def test_python_subprocess_string_concat_arg_detected(self) -> None:
        code = 'import subprocess\nsubprocess.run("ping " + host, shell=False)'
        findings = self.rule.check_file(Path("exec.py"), code, "python")
        assert len(findings) >= 1

    def test_python_subprocess_fstring_arg_detected(self) -> None:
        code = 'import subprocess\nsubprocess.run(f"ping {host}", shell=False)'
        findings = self.rule.check_file(Path("exec.py"), code, "python")
        assert len(findings) >= 1

    def test_python_subprocess_literal_list_default_shell_clean(self) -> None:
        code = 'import subprocess\nsubprocess.run(["echo", "hello"])'
        findings = self.rule.check_file(Path("exec.py"), code, "python")
        assert len(findings) == 0

    def test_python_subprocess_list_first_arg_variable_detected(self) -> None:
        code = 'import subprocess\nsubprocess.run([user_cmd, "-c", "1"])'
        findings = self.rule.check_file(Path("exec.py"), code, "python")
        assert len(findings) >= 1

    def test_python_subprocess_list_first_arg_concat_detected(self) -> None:
        code = 'import subprocess\nsubprocess.run(["/bin/" + user_tool, "arg"])'
        findings = self.rule.check_file(Path("exec.py"), code, "python")
        assert len(findings) >= 1

    def test_java_runtime_exec_detected(self) -> None:
        code = 'class R { void m(String c) throws Exception { Runtime.getRuntime().exec("sh -c " + c); } }'
        findings = self.rule.check_file(Path("R.java"), code, "java")
        assert len(findings) >= 1


class TestPathTraversalRule:
    rule = PathTraversalRule()

    def test_python_path_concat_open_detected(self) -> None:
        code = 'with open("/var/data/" + user_input) as f:\n    content = f.read()'
        findings = self.rule.check_file(Path("io.py"), code, "python")
        assert len(findings) >= 1

    def test_python_basename_clean(self) -> None:
        code = """
        import os
        safe = os.path.basename(user_input)
        with open("/var/data/" + safe) as f:
            content = f.read()
        """
        findings = self.rule.check_file(Path("io.py"), code, "python")
        assert len(findings) == 0

    def test_java_file_concat_detected(self) -> None:
        code = 'class F { File get(String d, String u) { return new File(d + "/" + u); } }'
        findings = self.rule.check_file(Path("F.java"), code, "java")
        assert len(findings) >= 1


class TestDisabledTlsVerificationRule:
    rule = DisabledTlsVerificationRule()

    def test_python_requests_verify_false_detected(self) -> None:
        code = 'import requests\nr = requests.get("https://example.com", verify=False)'
        findings = self.rule.check_file(Path("client.py"), code, "python")
        assert len(findings) >= 1
        assert findings[0].severity == Severity.HIGH

    def test_python_requests_verify_true_clean(self) -> None:
        code = 'import requests\nr = requests.get("https://example.com", verify=True)'
        findings = self.rule.check_file(Path("client.py"), code, "python")
        assert len(findings) == 0

    def test_java_disabled_hostname_verifier_detected(self) -> None:
        code = "class T { void m() { HttpsURLConnection.setDefaultHostnameVerifier((h, s) -> true); } }"
        findings = self.rule.check_file(Path("T.java"), code, "java")
        assert len(findings) >= 1

    def test_javascript_reject_unauthorized_false_detected(self) -> None:
        code = "const agent = new https.Agent({ rejectUnauthorized: false });"
        findings = self.rule.check_file(Path("client.js"), code, "javascript")
        assert len(findings) >= 1
        assert "CWE-295" in (findings[0].cwe or "")


class TestJavaScriptSecuritySnippets:
    """Comprehensive tests for high-risk JavaScript and Python snippets."""

    def test_js_command_injection_child_process_exec(self) -> None:
        rule = CommandInjectionRule()
        code = 'const { exec } = require("child_process");\nexec("ping -c 1 " + req.query.host);'
        findings = rule.check_file(Path("server.js"), code, "javascript")
        assert len(findings) >= 1
        assert findings[0].severity == Severity.CRITICAL
        assert "CWE-78" in (findings[0].cwe or "")

    def test_js_dynamic_execution_eval(self) -> None:
        rule = CommandInjectionRule()
        code = 'eval("const x = " + userInput);'
        findings = rule.check_file(Path("app.js"), code, "javascript")
        assert len(findings) >= 1
        assert "CWE-95" in (findings[0].cwe or "")

    def test_js_dynamic_execution_function(self) -> None:
        rule = CommandInjectionRule()
        code = 'const fn = new Function("arg", userInput);'
        findings = rule.check_file(Path("app.js"), code, "javascript")
        assert len(findings) >= 1
        assert "CWE-95" in (findings[0].cwe or "")

    def test_python_eval_and_exec_detected(self) -> None:
        rule = CommandInjectionRule()
        code = 'eval("1 + " + user_input)\nexec("print(" + cmd + ")")'
        findings = rule.check_file(Path("script.py"), code, "python")
        assert len(findings) >= 2

    def test_js_sql_injection_string_concat(self) -> None:
        rule = SqlConcatenationRule()
        code = 'db.query("SELECT * FROM users WHERE email = \'" + email + "\'");'
        findings = rule.check_file(Path("db.js"), code, "javascript")
        assert len(findings) >= 1
        assert "CWE-89" in (findings[0].cwe or "")

    def test_js_sql_injection_template_literal(self) -> None:
        rule = SqlConcatenationRule()
        code = "db.query(`SELECT * FROM users WHERE id = ${userId}`);"
        findings = rule.check_file(Path("db.js"), code, "javascript")
        assert len(findings) >= 1

    def test_js_deserialization_unserialize(self) -> None:
        rule = InsecureDeserializationRule()
        code = 'const serialize = require("node-serialize");\nconst obj = serialize.unserialize(payload);'
        findings = rule.check_file(Path("handler.js"), code, "javascript")
        assert len(findings) >= 1
        assert "CWE-502" in (findings[0].cwe or "")

    def test_js_hardcoded_secrets(self) -> None:
        rule = HardcodedSecretsRule()
        code = 'const AWS_SECRET_KEY = "AKIAIOSFODNN7EXAMPLEEXAMPLE";'
        findings = rule.check_file(Path("config.js"), code, "javascript")
        assert len(findings) >= 1
        assert "CWE-798" in (findings[0].cwe or "")

    def test_js_weak_crypto_md5(self) -> None:
        rule = WeakCryptoRule()
        code = 'const hash = crypto.createHash("md5").update(data).digest("hex");'
        findings = rule.check_file(Path("crypto.js"), code, "javascript")
        assert len(findings) >= 1
        assert "CWE-327" in (findings[0].cwe or "")

    def test_js_path_traversal(self) -> None:
        rule = PathTraversalRule()
        code = 'fs.readFile("/var/www/" + req.query.filename, (err, data) => {});'
        findings = rule.check_file(Path("routes.js"), code, "javascript")
        assert len(findings) >= 1
        assert "CWE-22" in (findings[0].cwe or "")
