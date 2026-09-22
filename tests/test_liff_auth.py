from unittest.mock import Mock, patch

import pytest

from modules.liff_auth import verify_liff_id_token


VALID_USER_ID = "U" + "a" * 32


def test_verify_liff_id_token_returns_verified_subject():
    response = Mock(status_code=200)
    response.json.return_value = {"sub": VALID_USER_ID}

    with patch("modules.liff_auth.requests.post", return_value=response) as post:
        assert verify_liff_id_token("header.payload.signature", "2009007637") == VALID_USER_ID

    post.assert_called_once_with(
        "https://api.line.me/oauth2/v2.1/verify",
        data={"id_token": "header.payload.signature", "client_id": "2009007637"},
        timeout=8,
    )


@pytest.mark.parametrize("status,payload", [
    (400, {}),
    (200, {}),
    (200, {"sub": "not-a-line-user"}),
])
def test_verify_liff_id_token_rejects_invalid_responses(status, payload):
    response = Mock(status_code=status)
    response.json.return_value = payload

    with patch("modules.liff_auth.requests.post", return_value=response), pytest.raises(ValueError):
        verify_liff_id_token("token", "2009007637")
