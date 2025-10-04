import os
import sys
import json
from cryptography.fernet import Fernet

def write_encrypted_json(data: dict, filename: str, key: bytes):
    fernet = Fernet(key)
    json_str = json.dumps(data)
    encrypted = fernet.encrypt(json_str.encode())

    os.makedirs(os.path.dirname(filename) or ".", exist_ok=True)

    with open(filename, 'wb') as f:
        f.write(encrypted)

def read_encrypted_json(filename: str, key: bytes) -> dict:
    fernet = Fernet(key)

    if not os.path.exists(filename):
        write_encrypted_json({}, filename, key)

    with open(filename, 'rb') as f:
        encrypted = f.read()

    decrypted = fernet.decrypt(encrypted).decode()
    return json.loads(decrypted)
