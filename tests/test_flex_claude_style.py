from unittest.mock import patch

from modules.messages import layout, service


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
    assert "cornerRadius" not in header
    assert "borderColor" not in header
    assert "backgroundColor" not in header


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
