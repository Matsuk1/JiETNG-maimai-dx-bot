import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _setup_module():
    path = ROOT / "scripts" / "setup_rich_menu.py"
    spec = importlib.util.spec_from_file_location("setup_rich_menu_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_account_buttons_are_liff_uri_actions():
    setup = _setup_module()
    liff_id = "2009007637-test"

    start = setup.page_actions("en", "start", liff_id)
    profile = setup.page_actions("en", "profile", liff_id)

    assert start[0] == {
        "type": "uri",
        "label": "Link Account",
        "uri": f"https://liff.line.me/{liff_id}/?action=bind",
    }
    assert profile[3]["uri"].endswith("?action=settings")
    assert profile[4]["uri"].endswith("?action=rebind")
    assert profile[5] == {
        "type": "uri",
        "label": "Unbind",
        "uri": f"https://liff.line.me/{liff_id}/?action=unbind",
    }


def test_other_rich_menu_buttons_remain_message_actions():
    setup = _setup_module()
    actions = setup.page_actions("zh", "main", "test-liff")

    assert all(action["type"] == "message" for action in actions)
