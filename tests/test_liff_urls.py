from urllib.parse import parse_qs, urlparse

from modules.liff_urls import build_account_action_url


def test_legacy_url_is_default_and_preserves_parameters():
    url = build_account_action_url(
        "example.com",
        "rebind",
        "sega_bind",
        {"token": "abc==", "mode": "rebind"},
    )

    parsed = urlparse(url)
    assert parsed.scheme == "https"
    assert parsed.netloc == "example.com"
    assert parsed.path == "/linebot/sega_bind"
    assert parse_qs(parsed.query) == {"token": ["abc=="], "mode": ["rebind"]}


def test_liff_url_is_used_only_when_enabled_and_configured():
    url = build_account_action_url(
        "example.com",
        "settings",
        "/settings",
        {"token": "settings-token"},
        liff_enabled=True,
        liff_id="1234567890-AbcdEfgh",
    )

    assert url == "https://liff.line.me/1234567890-AbcdEfgh/?action=settings&token=settings-token"


def test_missing_liff_id_falls_back_to_legacy_url():
    url = build_account_action_url(
        "example.com/",
        "settings",
        "settings",
        {"token": "token"},
        liff_enabled=True,
        liff_id="",
    )

    assert url == "https://example.com/linebot/settings?token=token"
