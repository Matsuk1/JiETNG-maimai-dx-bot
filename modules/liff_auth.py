"""Server-side verification for LIFF ID tokens."""

import re

import requests

_VERIFY_URL = "https://api.line.me/oauth2/v2.1/verify"
_USER_ID_RE = re.compile(r"U[0-9a-f]{32}")


def verify_liff_id_token(id_token: str, channel_id: str, *, timeout: int = 8) -> str:
    """Verify a raw LIFF ID token with LINE and return its provider-scoped user ID."""
    if not id_token or len(id_token) > 8192 or not channel_id:
        raise ValueError("Invalid LIFF authentication input")

    try:
        response = requests.post(
            _VERIFY_URL,
            data={"id_token": id_token, "client_id": channel_id},
            timeout=timeout,
        )
    except requests.RequestException as error:
        raise ValueError("LINE ID token verification request failed") from error
    if response.status_code != 200:
        raise ValueError(f"LINE rejected the LIFF ID token ({response.status_code})")

    try:
        payload = response.json() or {}
    except requests.JSONDecodeError as error:
        raise ValueError("LINE returned an invalid verification response") from error
    user_id = str(payload.get("sub", ""))
    if not _USER_ID_RE.fullmatch(user_id):
        raise ValueError("LINE response did not contain a valid user ID")
    return user_id
