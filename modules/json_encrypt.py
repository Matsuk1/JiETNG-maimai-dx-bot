import os
import sys
import json
from cryptography.fernet import Fernet

def write_encrypted_json(data: dict, filename: str, key: bytes):
    fernet = Fernet(key)
    json_str = json.dumps(data)
    encrypted = fernet.encrypt(json_str.encode())

    with open(filename, 'wb') as f:
        f.write(encrypted)

def read_encrypted_json(filename: str, key: bytes) -> dict:
    fernet = Fernet(key)
    with open(filename, 'rb') as f:
        encrypted = f.read()

    decrypted = fernet.decrypt(encrypted).decode()
    return json.loads(decrypted)

def encrypt_file(filepath):
    try:
        if not os.path.exists(filepath):
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=4)
            print(f"Created empty JSON file: {filepath}")

        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        write_encrypted_json(data, filepath + '.enc', KEY)
        print(f"Encrypted: {filepath}")
    except Exception as e:
        print(f"Failed to encrypt: {filepath}, Error: {e}")

def decrypt_file(filepath):
    try:
        if not os.path.exists(filepath):
            write_encrypted_json({}, filepath, KEY)
            print(f"Created empty encrypted file: {filepath}")

        data = read_encrypted_json(filepath, KEY)
        print(json.dumps(data, indent=4, ensure_ascii=False))
    except Exception as e:
        print(f"Failed to decrypt {filepath}: {e}")

def encrypt_directory_recursively(directory):
    for root, _, files in os.walk(directory):
        for file in files:
            full_path = os.path.join(root, file)
            if full_path.endswith('.enc'):
                continue
            if os.path.isfile(full_path):
                encrypt_file(full_path)

def decrypt_directory_recursively(directory):
    for root, _, files in os.walk(directory):
        for file in files:
            full_path = os.path.join(root, file)
            if full_path.endswith('.enc'):
                continue
            if os.path.isfile(full_path):
                decrypt_file(full_path)
