#!/usr/bin/env python3
"""
Create JiETNG multilingual advanced LINE rich menus.

Creates 13 menus:
- 1 start(A) menu: en/start
- 4 languages × 3 pages: main(B), extra(C), profile(D)

BCD pages have a top switch bar backed by LINE rich menu aliases.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import requests
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config.json"
ASSET_DIR = ROOT / "assets" / "richmenu"
UPLOAD_DIR = ASSET_DIR / "_upload"

WIDTH = 2500
SHORT_HEIGHT = 843
TALL_HEIGHT = 1686
MAX_UPLOAD_BYTES = 1024 * 1024
LINE_API = "https://api.line.me/v2/bot"
LINE_DATA_API = "https://api-data.line.me/v2/bot"

LANGUAGES = ("zh", "zh-tw", "en", "ja")
SWITCH_PAGES = ("main", "extra", "profile")
MENU_KEYS = (("en", "start"),) + tuple((lang, page) for lang in LANGUAGES for page in SWITCH_PAGES)
IMAGE_DIR_BY_LANG = {"zh": "zh", "zh-tw": "zh_tw", "en": "en", "ja": "ja"}
IMAGE_FILE_BY_PAGE = {
    "start": "A_start.png",
    "main": "B_main.png",
    "extra": "C_extra.png",
    "profile": "D_profile.png",
}

LABELS = {
    "zh": {
        "tab_main": "通常",
        "tab_extra": "拓展",
        "tab_profile": "个人",
        "bind": "绑定账号",
        "help": "帮助",
        "update": "更新数据",
        "b50": "B50",
        "b40": "B40",
        "ap50": "AP50",
        "ranking": "排行榜",
        "friends": "好友列表",
        "random": "随机选曲",
        "docs": "文档",
        "status": "状态",
        "rebind": "重新绑定",
        "settings": "设置",
        "unbind": "解除绑定",
        "profile": "个人资料",
        "export": "导出 JSON",
    },
    "zh-tw": {
        "tab_main": "通常",
        "tab_extra": "擴充",
        "tab_profile": "個人",
        "bind": "綁定帳號",
        "help": "說明",
        "update": "更新資料",
        "b50": "B50",
        "b40": "B40",
        "ap50": "AP50",
        "ranking": "排行榜",
        "friends": "好友列表",
        "random": "隨機選曲",
        "docs": "文件",
        "status": "狀態",
        "rebind": "重新綁定",
        "settings": "設定",
        "unbind": "解除綁定",
        "profile": "個人資料",
        "export": "匯出 JSON",
    },
    "en": {
        "tab_main": "Main",
        "tab_extra": "More",
        "tab_profile": "Profile",
        "bind": "Link Account",
        "help": "Help",
        "update": "Update",
        "b50": "B50",
        "b40": "B40",
        "ap50": "AP50",
        "ranking": "Ranking",
        "friends": "Friends",
        "random": "Random",
        "docs": "Docs",
        "status": "Status",
        "rebind": "Rebind",
        "settings": "Settings",
        "unbind": "Unbind",
        "profile": "Profile",
        "export": "Export JSON",
    },
    "ja": {
        "tab_main": "通常",
        "tab_extra": "拡張",
        "tab_profile": "個人",
        "bind": "アカウント連携",
        "help": "ヘルプ",
        "update": "データ更新",
        "b50": "B50",
        "b40": "B40",
        "ap50": "AP50",
        "ranking": "ランキング",
        "friends": "フレンド",
        "random": "ランダム",
        "docs": "ドキュメント",
        "status": "状態",
        "rebind": "再連携",
        "settings": "設定",
        "unbind": "連携解除",
        "profile": "プロフィール",
        "export": "JSON出力",
    },
}

PAGE_SIZE = {
    "start": (WIDTH, SHORT_HEIGHT),
    "main": (WIDTH, TALL_HEIGHT),
    "extra": (WIDTH, TALL_HEIGHT),
    "profile": (WIDTH, TALL_HEIGHT),
}

SWITCH_BOXES = [
    (125, 113, 806, 264),
    (906, 113, 1590, 264),
    (1696, 113, 2379, 264),
]

CONTENT_BOXES = {
    "start": [
        (120, 109, 1183, 735),
        (1316, 109, 2379, 735),
    ],
    "main": [
        (125, 337, 976, 1538),
        (1053, 337, 1668, 891),
        (1764, 337, 2379, 891),
        (1053, 983, 1668, 1538),
        (1764, 983, 2379, 1538),
    ],
    "extra": [
        (125, 337, 1199, 891),
        (1301, 337, 2379, 891),
        (125, 983, 1199, 1538),
        (1301, 983, 2379, 1538),
    ],
    "profile": [
        (125, 337, 806, 891),
        (906, 337, 1590, 891),
        (1696, 337, 2379, 891),
        (125, 983, 806, 1538),
        (906, 983, 1590, 1538),
        (1696, 983, 2379, 1538),
    ],
}


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise SystemExit("config.json not found. Start the app once or create config.json first.")
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_config(config: dict) -> None:
    with CONFIG_PATH.open("w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
        f.write("\n")


def alias_id(lang: str, page: str) -> str:
    return f"jietng-{lang}-{page}".lower()


def switch_action(lang: str, page: str) -> dict:
    return {
        "type": "richmenuswitch",
        "label": LABELS[lang][f"tab_{page}"],
        "richMenuAliasId": alias_id(lang, page),
        "data": f"richmenu={page}&lang={lang}",
    }


def message_action(label: str, text: str) -> dict:
    return {"type": "message", "label": label, "text": text}


def liff_uri_action(label: str, liff_id: str, action: str) -> dict:
    return {
        "type": "uri",
        "label": label,
        "uri": f"https://liff.line.me/{liff_id}/?action={action}",
    }


def page_actions(lang: str, page: str, liff_id: str) -> list[dict]:
    t = LABELS[lang]
    if page == "start":
        return [
            liff_uri_action(t["bind"], liff_id, "bind"),
            message_action(t["help"], "help"),
        ]
    if page == "main":
        return [
            message_action(t["update"], "maimai update"),
            message_action(t["b50"], "b50"),
            message_action(t["ap50"], "ap50"),
            message_action(t["b40"], "b40"),
            message_action("R50", "r50"),
        ]
    if page == "extra":
        return [
            message_action(t["ranking"], "ranking"),
            message_action(t["friends"], "friends"),
            message_action(t["random"], "random"),
            message_action(t["docs"], "help"),
        ]
    if page == "profile":
        return [
            message_action(t["profile"], "profile"),
            message_action(t["status"], "status"),
            message_action(t["export"], "export json"),
            liff_uri_action(t["settings"], liff_id, "settings"),
            liff_uri_action(t["rebind"], liff_id, "rebind"),
            liff_uri_action(t["unbind"], liff_id, "unbind"),
        ]
    raise ValueError(page)


def content_boxes(page: str) -> list[tuple[int, int, int, int]]:
    return CONTENT_BOXES[page]


def image_path(lang: str, page: str) -> Path:
    return ASSET_DIR / IMAGE_DIR_BY_LANG[lang] / IMAGE_FILE_BY_PAGE[page]


def ensure_images() -> dict[str, dict[str, Path]]:
    images = {}
    for lang, page in MENU_KEYS:
        images.setdefault(lang, {})
        path = image_path(lang, page)
        if not path.exists():
            raise SystemExit(f"Missing rich menu image: {path}")
        with Image.open(path) as img:
            expected_size = PAGE_SIZE[page]
            if img.size != expected_size:
                raise SystemExit(f"{path} must be {expected_size[0]}x{expected_size[1]}px, got {img.size[0]}x{img.size[1]}px")
            if img.format not in ("PNG", "JPEG"):
                raise SystemExit(f"{path} must be PNG or JPEG, got {img.format}")
        images[lang][page] = path
    return images


def prepare_upload_image(source: Path, lang: str, page: str) -> tuple[Path, str]:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    if source.stat().st_size <= MAX_UPLOAD_BYTES and source.suffix.lower() in (".png", ".jpg", ".jpeg"):
        content_type = "image/png" if source.suffix.lower() == ".png" else "image/jpeg"
        return source, content_type

    target = UPLOAD_DIR / f"{lang}_{page}.jpg"
    with Image.open(source) as img:
        rgb = img.convert("RGB")
        for quality in (92, 88, 84, 80, 76, 72, 68):
            rgb.save(target, "JPEG", quality=quality, optimize=True, progressive=True)
            if target.stat().st_size <= MAX_UPLOAD_BYTES:
                return target, "image/jpeg"
    raise SystemExit(f"Could not compress {source} below 1MB for LINE upload")


def request_json(method: str, url: str, token: str, **kwargs) -> dict:
    headers = kwargs.pop("headers", {})
    headers["Authorization"] = f"Bearer {token}"
    resp = requests.request(method, url, headers=headers, timeout=20, **kwargs)
    if not (200 <= resp.status_code < 300):
        raise RuntimeError(f"{method} {url} failed: {resp.status_code} {resp.text}")
    if not resp.text:
        return {}
    return resp.json()


def menu_payload(lang: str, page: str, liff_id: str) -> dict:
    areas = []
    if page in SWITCH_PAGES:
        for box, switch_page in zip(SWITCH_BOXES, SWITCH_PAGES):
            x0, y0, x1, y1 = box
            areas.append({"bounds": {"x": x0, "y": y0, "width": x1 - x0, "height": y1 - y0}, "action": switch_action(lang, switch_page)})

    actions = page_actions(lang, page, liff_id)
    for box, action in zip(content_boxes(page), actions):
        x0, y0, x1, y1 = box
        areas.append({"bounds": {"x": x0, "y": y0, "width": x1 - x0, "height": y1 - y0}, "action": action})

    return {
        "size": {"width": PAGE_SIZE[page][0], "height": PAGE_SIZE[page][1]},
        "selected": True,
        "name": f"JiETNG {lang} {page}",
        "chatBarText": "JiETNG",
        "areas": areas,
    }


def create_menu(token: str, lang: str, page: str, payload: dict, path: Path) -> str:
    created = request_json(
        "POST",
        f"{LINE_API}/richmenu",
        token,
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
    )
    rich_menu_id = created["richMenuId"]
    upload_path, content_type = prepare_upload_image(path, lang, page)
    with upload_path.open("rb") as f:
        request_json(
            "POST",
            f"{LINE_DATA_API}/richmenu/{rich_menu_id}/content",
            token,
            headers={"Content-Type": content_type},
            data=f.read(),
        )
    print(f"{lang}/{page}: {rich_menu_id} ({upload_path.stat().st_size} bytes)")
    return rich_menu_id


def create_or_update_alias(token: str, rich_menu_alias_id: str, rich_menu_id: str) -> None:
    body = {"richMenuAliasId": rich_menu_alias_id, "richMenuId": rich_menu_id}
    headers = {"Content-Type": "application/json"}
    try:
        request_json("POST", f"{LINE_API}/richmenu/alias", token, headers=headers, data=json.dumps(body).encode("utf-8"))
        print(f"alias created: {rich_menu_alias_id}")
    except RuntimeError as e:
        error_text = str(e)
        is_conflict = "409" in error_text or "conflict richmenu alias id" in error_text
        if not is_conflict:
            raise
        update_body = {"richMenuId": rich_menu_id}
        request_json(
            "POST",
            f"{LINE_API}/richmenu/alias/{rich_menu_alias_id}",
            token,
            headers=headers,
            data=json.dumps(update_body).encode("utf-8"),
        )
        print(f"alias updated: {rich_menu_alias_id}")


def delete_rich_menu(token: str, rich_menu_id: str) -> None:
    if not rich_menu_id:
        return
    resp = requests.delete(
        f"{LINE_API}/richmenu/{rich_menu_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=20,
    )
    if resp.status_code in (200, 404):
        print(f"rich menu deleted: {rich_menu_id}")
        return
    raise RuntimeError(f"DELETE {LINE_API}/richmenu/{rich_menu_id} failed: {resp.status_code} {resp.text}")


def has_complete_menu_config(config: dict) -> bool:
    menus = (config.get("rich_menu", {}) or {}).get("menus", {})
    return all(menus.get(lang, {}).get(page) for lang, page in MENU_KEYS)


def build_aliases() -> dict[str, dict[str, str]]:
    return {
        lang: {page: alias_id(lang, page) for page in SWITCH_PAGES}
        for lang in LANGUAGES
    }


def existing_menu_ids(config: dict) -> list[str]:
    rich_menu = config.get("rich_menu", {}) or {}
    ids = []
    for pages in (rich_menu.get("menus", {}) or {}).values():
        ids.extend(rich_menu_id for rich_menu_id in pages.values() if rich_menu_id)
    ids.extend(
        rich_menu_id
        for rich_menu_id in (rich_menu.get("unbound_id"), rich_menu.get("bound_id"))
        if rich_menu_id
    )
    return list(dict.fromkeys(ids))


def write_rich_menu_config(config: dict, menus: dict, aliases: dict, support_url: str) -> None:
    config.setdefault("rich_menu", {})
    config["rich_menu"].update(
        {
            "enabled": True,
            "default_language": "zh",
            "menus": menus,
            "aliases": aliases,
            "unbound_id": menus.get("en", {}).get("start", ""),
            "bound_id": menus.get("zh", {}).get("main", ""),
            "support_url": support_url,
        }
    )
    save_config(config)


def update_aliases(token: str, menus: dict, aliases: dict) -> None:
    for lang in LANGUAGES:
        for page in SWITCH_PAGES:
            rich_menu_id = menus.get(lang, {}).get(page)
            if not rich_menu_id:
                raise SystemExit(f"Missing rich menu id for {lang}/{page}; cannot update aliases.")
            create_or_update_alias(token, aliases[lang][page], rich_menu_id)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="generate images and print payloads only")
    parser.add_argument("--aliases-only", action="store_true", help="only create/update aliases from config.json; do not create menus")
    parser.add_argument("--delete-existing", action="store_true", help="delete menu IDs currently recorded in config.json before rebuilding")
    parser.add_argument("--force", action="store_true", help="rebuild menus; requires --delete-existing when config already has a complete set")
    args = parser.parse_args()

    os.chdir(ROOT)
    config = load_config()
    token = config.get("line_channel", {}).get("access_token", "")
    liff_id = str((config.get("liff", {}) or {}).get("id", "")).strip()
    if not liff_id:
        raise SystemExit("liff.id is empty in config.json; rich menu account links require LIFF")
    domain = config.get("domain", "").rstrip("/")
    urls = config.get("urls", {})
    support_url = (config.get("rich_menu", {}) or {}).get("support_url") or urls.get("support_page") or f"https://{domain}/"

    images = ensure_images()
    payloads = {}
    for lang, page in MENU_KEYS:
        payloads.setdefault(lang, {})[page] = menu_payload(lang, page, liff_id)

    if args.dry_run:
        print(json.dumps(payloads, indent=2, ensure_ascii=False))
        print("Images:")
        for lang, page in MENU_KEYS:
            print(f"- {images[lang][page]}")
        return 0

    if not token:
        raise SystemExit("line_channel.access_token is empty in config.json")
    aliases = build_aliases()
    existing_menus = (config.get("rich_menu", {}) or {}).get("menus", {}) or {}

    if args.aliases_only:
        if not has_complete_menu_config(config):
            raise SystemExit("config.json does not have complete rich_menu.menus; cannot run --aliases-only.")
        update_aliases(token, existing_menus, aliases)
        write_rich_menu_config(config, existing_menus, aliases, support_url)
        print("Aliases updated from existing config.json menu IDs.")
        return 0

    if has_complete_menu_config(config) and not args.force:
        print("config.json already has a complete rich_menu.menus set; updating aliases only.")
        print("Use --force --delete-existing to delete the recorded menus and rebuild them.")
        update_aliases(token, existing_menus, aliases)
        write_rich_menu_config(config, existing_menus, aliases, support_url)
        return 0

    if has_complete_menu_config(config) and args.force and not args.delete_existing:
        raise SystemExit("--force would create another full set. Use --force --delete-existing to rebuild without leaving recorded old menus.")

    if args.delete_existing:
        if not args.force:
            raise SystemExit("--delete-existing must be used together with --force.")
        for rich_menu_id in existing_menu_ids(config):
            delete_rich_menu(token, rich_menu_id)
        existing_menus = {}
        write_rich_menu_config(config, {}, aliases, support_url)

    menus: dict[str, dict[str, str]] = {
        lang: dict(existing_menus.get(lang, {}))
        for lang in LANGUAGES
    }
    for lang, page in MENU_KEYS:
        menus.setdefault(lang, {})
        if menus[lang].get(page):
            print(f"{lang}/{page}: reuse {menus[lang][page]}")
            continue
        menus[lang][page] = create_menu(token, lang, page, payloads[lang][page], images[lang][page])
        write_rich_menu_config(config, menus, aliases, support_url)

    update_aliases(token, menus, aliases)
    write_rich_menu_config(config, menus, aliases, support_url)
    print("config.json updated. Restart the bot to load the new rich menu IDs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
