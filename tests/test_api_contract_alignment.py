import asyncio
import sys
from pathlib import Path

import httpx
from flask import Flask
from PIL import Image


CLIENT_SRC = Path(__file__).resolve().parents[1] / "client" / "src"
if str(CLIENT_SRC) not in sys.path:
    sys.path.insert(0, str(CLIENT_SRC))

from jietng import AsyncjietngClient, jietngClient
import modules.api.api_auth as api_auth_module
import modules.api.image_api as image_api_module
import modules.images.skins as skins_module
from modules.api.image_api import _progress_filter


def test_progress_filter_accepts_documented_values_and_rejects_unknown_value():
    app = Flask(__name__)
    for value in ("uncleared", "unplayed", "cleared", " CLEARED "):
        with app.test_request_context(f"/?filter={value}"):
            mode, error = _progress_filter()
            assert mode == value.strip().lower()
            assert error is None

    with app.test_request_context("/?filter=unexpected"):
        mode, error = _progress_filter()
        response, status = error
        assert mode is None
        assert status == 400
        assert response.get_json()["error"] == "Invalid parameter"


def test_achievement_endpoint_applies_filter(monkeypatch):
    app = Flask(__name__)
    app.register_blueprint(image_api_module.image_api)
    image_api_module.configure_image_api(
        background_filter=lambda user_id: None,
        generate_profile=lambda *args, **kwargs: Image.new("RGB", (1, 1)),
        select_records=lambda *args, **kwargs: ([], [], {}),
    )
    monkeypatch.setattr(api_auth_module, "verify_dev_token", lambda token: {
        "token_id": "token-id", "note": "test",
    })
    monkeypatch.setattr(skins_module, "user_skin", lambda user_id: "default")
    monkeypatch.setattr(image_api_module, "check_rate_limit", lambda *args: False)
    monkeypatch.setattr(image_api_module, "check_user_permission", lambda *args: (
        True, {"version": "jp", "personal_info": {}},
    ))
    monkeypatch.setattr(image_api_module, "read_record", lambda *args, **kwargs: [{}])
    monkeypatch.setattr(image_api_module, "read_dxdata", lambda *args, **kwargs: ([], []))
    monkeypatch.setattr(image_api_module, "build_progress_entries", lambda *args, **kwargs: (
        [{"achieved": False, "achievement_rate": 0}],
        {"achieved": 0, "unachieved": 0, "unplayed": 1, "total": 1},
    ))
    monkeypatch.setattr(
        image_api_module, "generate_level_rank_progress_image",
        lambda *args, **kwargs: Image.new("RGB", (1, 1)),
    )
    monkeypatch.setattr(
        image_api_module, "compose_generated_images",
        lambda *args, **kwargs: Image.new("RGB", (1, 1)),
    )

    client = app.test_client()
    headers = {"Authorization": "Bearer test"}
    assert client.get(
        "/api/v2/users/user-id/achievement?level=14%2B&filter=unplayed",
        headers=headers,
    ).status_code == 200
    assert client.get(
        "/api/v2/users/user-id/achievement?level=14%2B&filter=cleared",
        headers=headers,
    ).status_code == 404
    assert client.get(
        "/api/v2/users/user-id/achievement?level=14%2B&filter=invalid",
        headers=headers,
    ).status_code == 400


def test_sync_sdk_forwards_song_version_filter_and_base64_format():
    requests = []

    def handler(request):
        requests.append(request)
        if request.url.params.get("format") == "base64":
            return httpx.Response(200, json={"success": True, "format": "base64", "image": "abc"})
        return httpx.Response(200, content=b"png", headers={"Content-Type": "image/png"})

    with jietngClient(token="test", transport=httpx.MockTransport(handler)) as client:
        assert client.songs.info("song-id", ver="intl") == b"png"
        encoded = client.images.plate(
            "user-id", title="真神", filter_mode="uncleared", format="BASE64",
        )

    assert encoded == {"success": True, "format": "base64", "image": "abc"}
    assert requests[0].url.params["ver"] == "intl"
    assert requests[0].url.params["format"] == "png"
    assert requests[1].url.params["filter"] == "uncleared"
    assert requests[1].url.params["format"] == "base64"


def test_async_sdk_forwards_song_version_and_base64_format():
    requests = []

    def handler(request):
        requests.append(request)
        if request.url.params.get("format") == "base64":
            return httpx.Response(200, json={"success": True, "format": "base64", "image": "xyz"})
        return httpx.Response(200, content=b"png", headers={"Content-Type": "image/png"})

    async def exercise():
        async with AsyncjietngClient(
            token="test", transport=httpx.MockTransport(handler),
        ) as client:
            assert await client.songs.info("song-id", ver="intl") == b"png"
            return await client.images.achievement(
                "user-id", level="14+", rank="sss", filter_mode="unplayed",
                format="base64",
            )

    encoded = asyncio.run(exercise())
    assert encoded == {"success": True, "format": "base64", "image": "xyz"}
    assert requests[0].url.params["ver"] == "intl"
    assert requests[1].url.params["filter"] == "unplayed"
    assert requests[1].url.params["format"] == "base64"


def test_sdk_rejects_undocumented_image_format_before_request():
    with jietngClient(token="test", transport=httpx.MockTransport(lambda request: None)) as client:
        try:
            client.images.records("user-id", format="jpeg")
        except ValueError as exc:
            assert str(exc) == "format must be 'png' or 'base64'"
        else:
            raise AssertionError("invalid image format was accepted")
