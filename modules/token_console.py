import base64
import hmac
import hashlib
import time
from config_loader import BIND_TOKEN_KEY

def generate_token(user_id: str) -> str:
    timestamp = str(int(time.time()))
    raw = f"{user_id}.{timestamp}".encode('utf-8')

    signature = hmac.new(BIND_TOKEN_KEY, raw, hashlib.sha256).digest()

    token = base64.urlsafe_b64encode(raw + b"." + signature).decode('utf-8')
    return token


TOKEN_EXPIRE_SECONDS = 120

def get_user_id_from_token(token: str) -> str:
    try:
        decoded = base64.urlsafe_b64decode(token.encode('utf-8'))

        parts = decoded.split(b".", 2)
        if len(parts) != 3:
            raise ValueError("Invalid token format")

        user_id_bytes, timestamp_bytes, signature = parts
        raw = user_id_bytes + b"." + timestamp_bytes

        expected_signature = hmac.new(BIND_TOKEN_KEY, raw, hashlib.sha256).digest()
        if not hmac.compare_digest(signature, expected_signature):
            raise ValueError("Invalid token signature")

        timestamp = int(timestamp_bytes.decode('utf-8'))
        now = int(time.time())
        if abs(now - timestamp) > TOKEN_EXPIRE_SECONDS:
            raise ValueError("Token expired")

        return user_id_bytes.decode('utf-8')

    except Exception as e:
        raise ValueError("Invalid token") from e
