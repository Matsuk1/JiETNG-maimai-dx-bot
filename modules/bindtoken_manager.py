"""Short-lived signed tokens for account actions."""

import base64
import hashlib
import hmac
import time

from modules.config_loader import BIND_TOKEN_KEY

TOKEN_EXPIRE_SECONDS = 120
PERM_TOKEN_EXPIRE_SECONDS = 600
SETTINGS_TOKEN_EXPIRE_SECONDS = 1800
UNBIND_TOKEN_EXPIRE_SECONDS = 600


def _generate_token(user_id, purpose=None):
    prefix = f"{purpose}." if purpose else ""
    raw = f"{prefix}{user_id}.{int(time.time())}".encode()
    signature = hmac.new(BIND_TOKEN_KEY, raw, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(raw + b"." + signature).decode()


def _verify_token(token, *, purpose=None, expires, error_label="token"):
    try:
        decoded = base64.urlsafe_b64decode(token.encode())
        if len(decoded) < 34 or decoded[-33] != ord("."):
            raise ValueError("Invalid token format")

        raw, signature = decoded[:-33], decoded[-32:]
        expected = hmac.new(BIND_TOKEN_KEY, raw, hashlib.sha256).digest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError("Invalid token signature")

        payload = raw.decode()
        prefix = f"{purpose}." if purpose else ""
        if prefix and not payload.startswith(prefix):
            raise ValueError("Invalid token purpose")
        user_id, timestamp = payload[len(prefix):].rsplit(".", 1)
        if abs(int(time.time()) - int(timestamp)) > expires:
            raise ValueError("Token expired")
        return user_id
    except Exception as error:
        raise ValueError(f"Invalid {error_label}") from error


def generate_bind_token(user_id: str) -> str:
    return _generate_token(user_id)


def get_user_id_from_token(token: str) -> str:
    return _verify_token(token, expires=TOKEN_EXPIRE_SECONDS)


def generate_settings_token(user_id: str) -> str:
    return _generate_token(user_id, "settings")


def get_user_id_from_settings_token(token: str) -> str:
    return _verify_token(token, purpose="settings", expires=SETTINGS_TOKEN_EXPIRE_SECONDS,
                         error_label="settings token")


def generate_unbind_token(user_id: str) -> str:
    return _generate_token(user_id, "unbind")


def get_user_id_from_unbind_token(token: str) -> str:
    return _verify_token(token, purpose="unbind", expires=UNBIND_TOKEN_EXPIRE_SECONDS,
                         error_label="unbind token")


def generate_perm_token(user_id: str) -> str:
    return _generate_token(user_id, "perm")


def get_user_id_from_perm_token(token: str) -> str:
    return _verify_token(token, purpose="perm", expires=PERM_TOKEN_EXPIRE_SECONDS,
                         error_label="perm token")
