from unittest.mock import patch
from pathlib import Path

from modules.messages import layout, service
from modules.commands.command_help import generate_help_index_flex
from modules.perm_request_generator import generate_perm_request_message
from modules.storelist_generator import generate_store_buttons


def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def test_shared_flex_palette_uses_warm_claude_accent():
    assert layout.COLOR_BRAND == "#C96442"
    assert layout.COLOR_BRAND_SOFT == "#F6E7E0"
    assert layout.COLOR_SURFACE == "#FDFCFB"


def test_product_header_is_sparse_not_a_nested_card():
    header = layout.standard_product_header("Profile", "JiETNG")
    assert header["contents"][0]["text"] == "Profile"
    assert [node.get("text") for node in walk(header) if node.get("type") == "text"] == ["Profile"]
    assert "cornerRadius" not in header
    assert "borderColor" not in header
    assert "backgroundColor" not in header


def test_copy_actions_render_as_compact_icons_without_visible_labels():
    user = {
        "sega_id": "example",
        "version": "jp",
        "personal_info": {"name": "Player", "rating": 15000},
    }
    with patch.object(service, "get_user", return_value=user), \
         patch.object(service, "get_user_language", return_value="ja"):
        profile = service.generate_user_info_flex("U123").to_dict()
        export = service.generate_export_flex("U123", {
            "size": 2048,
            "fmt": "json",
            "best_count": 50,
            "recent_count": 10,
            "ttl_minutes": 15,
            "url": "https://example.test/export",
        }).to_dict()

    for payload in (profile, export):
        clipboard_box = next(
            node for node in walk(payload)
            if node.get("action", {}).get("type") == "clipboard"
        )
        assert clipboard_box["width"] == "32px"
        assert clipboard_box["height"] == "32px"
        assert clipboard_box["contents"][0]["text"] == "⧉"
        visible_text = [node.get("text") for node in walk(clipboard_box) if node.get("type") == "text"]
        assert visible_text == ["⧉"]


def test_profile_flex_uses_dividers_instead_of_gray_row_cards():
    user = {
        "sega_id": "example",
        "version": "jp",
        "personal_info": {"name": "Player", "rating": 15000},
    }
    with patch.object(service, "get_user", return_value=user), \
         patch.object(service, "get_user_language", return_value="en"):
        payload = service.generate_user_info_flex("U123").to_dict()

    nodes = list(walk(payload))
    colors = {node.get("backgroundColor") for node in nodes if node.get("backgroundColor")}
    assert "#3C7FE8" not in colors
    assert "#F8FAFC" not in colors
    assert layout.COLOR_SURFACE in colors
    assert any(node.get("type") == "separator" and node.get("color") == layout.COLOR_BORDER for node in nodes)


def test_profile_line_id_stays_on_one_adaptive_line_before_copy_icon():
    line_id = "U0b3989b7f797f4d22d2bd1b89ca530b3"
    with patch.object(service, "get_user", return_value=None), \
         patch.object(service, "get_user_language", return_value="ja"):
        payload = service.generate_user_info_flex(line_id).to_dict()

    line_id_text = next(
        node for node in walk(payload)
        if node.get("type") == "text" and node.get("text") == line_id
    )
    assert line_id_text["size"] == "xs"
    assert line_id_text["wrap"] is False
    assert line_id_text["adjustMode"] == "shrink-to-fit"


def test_all_flex_generators_reject_legacy_generic_blue_and_cold_gray():
    root = Path(__file__).resolve().parents[1]
    sources = [
        root / "modules/messages/layout.py",
        root / "modules/messages/scores.py",
        root / "modules/messages/service.py",
        root / "modules/commands/command_help.py",
        root / "modules/perm_request_generator.py",
        root / "modules/storelist_generator.py",
    ]
    legacy_tokens = ("#3C7FE8", "#315B7D", "#007AFF", "#E8EEF5", "#F8FAFC")
    combined = "\n".join(path.read_text() for path in sources)
    for token in legacy_tokens:
        assert token not in combined


def test_representative_flex_families_build_with_the_warm_contract():
    user = {
        "sega_id": "example",
        "version": "jp",
        "personal_info": {"name": "Player", "rating": 15000},
    }
    export_meta = {
        "size": 2048,
        "fmt": "json",
        "best_count": 50,
        "recent_count": 10,
        "ttl_minutes": 15,
        "url": "https://example.test/export",
    }
    with patch.object(service, "get_user", return_value=user), \
         patch.object(service, "get_user_language", return_value="en"), \
         patch.object(service, "get_user_timezone", return_value=9), \
         patch.object(service, "_tip_ad_boxes", return_value=[]):
        messages = [
            service.generate_status_flex("Status", "Ready"),
            service.generate_account_action_flex("settings", "https://example.test/settings"),
            service.generate_welcome_flex(bind_url="https://example.test/bind"),
            service.generate_export_flex("user", export_meta),
            service.generate_notice_flex({"content": "Notice", "date": "2026-10-27"}, "user"),
            service.generate_user_info_flex("user"),
            service.generate_update_result_flex("user", "2026-10-27", 1.2, {"User Info": True}),
            service.generate_song_list_flex("user", "Songs", [{"id": "000001", "title": "Song", "artist": "Artist"}], 1, "search-song", "Song"),
            service.generate_ranking_flex("user", [{"rank": 1, "name": "Player", "rating": 15000, "is_user": True}]),
            service.generate_friend_buttons("user", "Friends", [{"name": "Friend", "rating": 14000, "friend_id": "friend"}], 6),
            service.generate_rc_flex(14.0, [(100.5, 300)]),
            service.generate_bot_status_flex("1h", 0, 0, 10, 1000, "2026-10-27"),
            generate_perm_request_message([{
                "token_id": "jt_example",
                "requester_name": "Example App",
                "timestamp": "2026-10-27 12:00:00",
                "request_id": "request-example",
            }], "user"),
            generate_store_buttons("user", "Nearby stores", [{
                "name": "Arcade",
                "address": "Tokyo",
                "distance": "1.2 km",
                "lat": 35.0,
                "lng": 139.0,
            }]),
        ]

    for message in messages:
        payload = message.to_dict()
        serialized = str(payload)
        assert payload["type"] == "flex"
        assert "#3C7FE8" not in serialized
        assert "#315B7D" not in serialized
        assert "#007AFF" not in serialized


def test_shared_metric_and_utility_primitives_are_flat_not_pills():
    metric = layout.metric_card("Uptime", "1h")
    utility = layout.round_icon_action("→", {"type": "message", "label": "Open", "text": "open"})
    page_action = layout.pill_action_box("Next", {"type": "message", "label": "Next", "text": "next"})

    assert "backgroundColor" not in metric
    assert "cornerRadius" not in metric
    assert utility["width"] == utility["height"] == "32px"
    assert utility["cornerRadius"] == "8px"
    assert page_action["cornerRadius"] == "8px"


def test_help_directory_uses_flat_rows_and_icon_only_drill_in_actions():
    payload = generate_help_index_flex().to_dict()
    nodes = list(walk(payload))
    action_nodes = [node for node in nodes if node.get("action", {}).get("type") == "postback"]

    assert action_nodes
    assert all(node["contents"][0]["text"] == "→" for node in action_nodes)
    assert not any(node.get("cornerRadius") in {"16px", "999px", "md"} for node in nodes)
