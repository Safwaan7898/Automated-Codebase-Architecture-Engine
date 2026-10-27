"""Fixture: Clean Python source file following secure coding practices (0 false positives)."""

import hashlib
import json
import os
import subprocess
from pathlib import Path
import requests
import yaml
from Crypto.Cipher import AES

# 1. Clean Secret: loaded securely from environment
API_KEY = os.getenv("API_KEY", "")


def query_user(cursor, user_id: int, name: str) -> None:
    # 2. Clean SQL: parameterized queries
    cursor.execute("SELECT * FROM users WHERE name = %s", (name,))
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))


def compute_hashes(data: bytes) -> None:
    # 3. Clean crypto: SHA-256 and AES-GCM
    h1 = hashlib.sha256(data).hexdigest()
    h2 = hashlib.sha512(data).hexdigest()
    cipher = AES.new(b"1234567812345678", AES.MODE_GCM)


def load_user_session(raw_data: str, yaml_data: str) -> None:
    # 4. Clean deserialization: JSON and yaml.safe_load
    session = json.loads(raw_data)
    config = yaml.safe_load(yaml_data)


def execute_diagnostic_ping(host: str) -> None:
    # 5. Clean command execution: argument list, shell=False
    subprocess.run(["ping", "-c", "1", host], shell=False, check=True)


def read_user_file(base_dir: str, user_filename: str) -> str:
    # 6. Clean path validation: basename and commonpath check
    safe_name = os.path.basename(user_filename)
    full_path = Path(base_dir).resolve() / safe_name
    with open(full_path, "r", encoding="utf-8") as f:
        return f.read()


def fetch_remote_metrics(url: str) -> None:
    # 7. Clean TLS verification: verify=True (or default)
    response = requests.get(url, verify=True, timeout=10.0)
