"""Fixture: Vulnerable Python source file seeded with all 7 security vulnerabilities."""

import hashlib
import os
import pickle
import subprocess
import requests
import yaml
from Crypto.Cipher import DES

# 1. Hardcoded Secret
API_KEY = "CHANGEME"
AWS_SECRET_ACCESS_KEY = "AKIAIOSFODNN7EXAMPLE"


def query_user(cursor, user_id: str, name: str) -> None:
    # 2. SQL built by string concatenation
    query = "SELECT * FROM users WHERE name = '" + name + "'"
    cursor.execute(query)
    # Also f-string interpolation into execute
    cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")


def compute_hashes(data: bytes) -> None:
    # 3. Weak crypto (MD5, SHA1, DES)
    h1 = hashlib.md5(data).hexdigest()
    h2 = hashlib.sha1(data).digest()
    h3 = hashlib.new("md5")
    cipher = DES.new(b"12345678", DES.MODE_ECB)


def load_user_session(raw_data: bytes, yaml_data: str) -> None:
    # 4. Insecure deserialization (pickle, yaml.load)
    session = pickle.loads(raw_data)
    config = yaml.load(yaml_data, Loader=yaml.Loader)


def execute_diagnostic_ping(host: str, cmd: str) -> None:
    # 5. Command injection (os.system, subprocess shell=True)
    os.system("ping -c 1 " + host)
    subprocess.run(cmd, shell=True)


def read_user_file(base_dir: str, user_filename: str) -> str:
    # 6. Path traversal
    filepath = base_dir + "/" + user_filename
    with open(filepath, "r") as f:
        return f.read()


def fetch_remote_metrics(url: str) -> None:
    # 7. Disabled TLS verification
    response = requests.get(url, verify=False)
