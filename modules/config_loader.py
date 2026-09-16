"""加载应用配置和缓存后的歌曲数据。"""

import copy
import json
import os
import secrets
import csv
import threading

CONFIG_PATH = "./config.json"

DEFAULT_CONFIG = {
    "admin_password": "",
    "maimai_version": {
        "jp": [],
        "intl": []
    },
    "temp_version": {
        "abbr": "",
        "title": ""
    },
    "domain": "",
    "host": "0.0.0.0",
    "port": 5000,
    "record_database": {
        "host": "localhost",
        "user": "root",
        "password": "",
        "database": "maimai_records"
    },
    "urls": {
        "line_adding": "",
        "support_page": "https://github.com/Matsuk1/JiETNG/blob/main/COMMANDS.md",
        "dxdata": [
            "https://dp4p6x0xfi5o9.cloudfront.net/maimai/data.json",
            "https://raw.githubusercontent.com/gekichumai/dxrating/refs/heads/main/packages/dxdata/dxdata.json"
        ]
    },
    "line_channel": {
        "account_id": "",
        "access_token": "",
        "secret": ""
    },
    "rich_menu": {
        "enabled": False,
        "unbound_id": "",
        "bound_id": "",
        "support_url": "",
        "default_language": "zh",
        "menus": {},
        "aliases": {}
    },
    "keys": {
        "bind_token": ""
    },
    "cloudflare_r2": {
        "enabled": False,
        "account_id": "",
        "access_key_id": "",
        "secret_access_key": "",
        "bucket_name": "",
        "public_url": ""
    },
    "web_push": {
        "vapid_private_key": "",
        "vapid_public_key": "",
        "contact": "mailto:admin@example.com"
    },
    "plugins": {
        "enabled": True,
        "directories": ["./plugins"]
    },
    "ai_monitor": {
        "enabled": True,
        "codex_command": "codex",
        "model": "",
        "timeout_seconds": 90,
        "session_ttl_seconds": 3600
    }
}

def _generate_vapid_keys():
    """生成 VAPID 密钥对（EC P-256），返回 (private_b64, public_b64)"""
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.backends import default_backend
    import base64
    key = ec.generate_private_key(ec.SECP256R1(), default_backend())
    priv_bytes = key.private_numbers().private_value.to_bytes(32, 'big')
    pub = key.public_key().public_numbers()
    pub_bytes = b'\x04' + pub.x.to_bytes(32, 'big') + pub.y.to_bytes(32, 'big')
    return (
        base64.urlsafe_b64encode(priv_bytes).rstrip(b'=').decode(),
        base64.urlsafe_b64encode(pub_bytes).rstrip(b'=').decode()
    )

def _ensure_bind_token(value: str) -> str:
    if not isinstance(value, str) or not value:
        value = secrets.token_urlsafe(16)

    return value


def _merge_defaults(current, defaults):
    """Fill missing or malformed mapping nodes without sharing default values."""
    for key, default in defaults.items():
        if key not in current:
            current[key] = copy.deepcopy(default)
        elif isinstance(default, dict):
            if isinstance(current[key], dict):
                _merge_defaults(current[key], default)
            else:
                current[key] = copy.deepcopy(default)
    return current


def _save_config(config):
    directory = os.path.dirname(CONFIG_PATH)
    if directory:
        os.makedirs(directory, exist_ok=True)
    temporary_path = f"{CONFIG_PATH}.tmp"
    with open(temporary_path, "w", encoding="utf-8") as file:
        json.dump(config, file, indent=4, ensure_ascii=False)
    os.replace(temporary_path, CONFIG_PATH)


def _load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, encoding="utf-8") as file:
            loaded = json.load(file)
        config = loaded if isinstance(loaded, dict) else {}
    else:
        config = {}

    original = copy.deepcopy(config)
    _merge_defaults(config, DEFAULT_CONFIG)
    keys = config["keys"]
    keys["bind_token"] = _ensure_bind_token(keys.get("bind_token", ""))
    web_push = config["web_push"]
    if not web_push.get("vapid_private_key") or not web_push.get("vapid_public_key"):
        web_push["vapid_private_key"], web_push["vapid_public_key"] = _generate_vapid_keys()
    if config != original or not os.path.exists(CONFIG_PATH):
        _save_config(config)
    return config


_config = _load_config()

ADMIN_PASSWORD = _config["admin_password"]
MAIMAI_VERSION = _config["maimai_version"]
TEMP_VERSION = _config["temp_version"]

DOMAIN = _config["domain"]

HOST = _config["host"]
PORT = _config["port"]

LOG_FILE = "./jietng.log"
DXDATA_FILE = "./data/dxdata/dxdata.json"
DXDATA_VERSION_FILE = "./data/dxdata/dxdata_version.json"
OVERRIDE_FILE = "./data/dxdata/override.csv"
INTL_OVERRIDE_FILE = "./data/dxdata/intl_override.csv"
NOTICE_FILE = "./data/notice.json"
TIP_AD_FILE = "./data/tip_ad.json"
DEV_TOKENS_FILE = "./data/dev_tokens.json"

BACKUP_DIR = "./data/backup"
IMG_DIR = "./data/images"
EXPORT_DIR = "./data/exports"

FONT_FILE = "./assets/fonts/line_seed_jietng.ttf"
LOGO_FILE = "./assets/pics/logo.png"
QR_CODE_FILE = "./assets/pics/qrcode.png"

VERSIONS_DIR = "./assets/versions"
COVERS_DIR = "./assets/covers"
PLATES_DIR = "./assets/plates"
ICON_TYPE_DIR = "./assets/icon/type"
ICON_SCORE_DIR = "./assets/icon/score"
ICON_DX_STAR_DIR = "./assets/icon/dx_star"
ICON_COMBO_DIR = "./assets/icon/combo"
ICON_SYNC_DIR = "./assets/icon/sync"
ICON_COMBO_RCD_DIR = "./assets/icon/combo_rcd"
ICON_SYNC_RCD_DIR = "./assets/icon/sync_rcd"
ICON_BASE_DIR = "./assets/icon"
BG_DIR = "./assets/pics/bg"
RATING_DIR = "./assets/pics/rating"

RECORD_DATABASE = _config["record_database"]
DB_HOST = RECORD_DATABASE["host"]
DB_USER = RECORD_DATABASE["user"]
DB_PASSWORD = RECORD_DATABASE["password"]
DB_NAME = RECORD_DATABASE["database"]

URLS = _config["urls"]
LINE_ADDING_URL = URLS["line_adding"]
SUPPORT_PAGE = URLS["support_page"]
DXDATA_URL = URLS["dxdata"]

LINE_CHANNEL = _config["line_channel"]
LINE_ACCOUNT_ID = LINE_CHANNEL["account_id"]
LINE_CHANNEL_ACCESS_TOKEN = LINE_CHANNEL["access_token"]
LINE_CHANNEL_SECRET = LINE_CHANNEL["secret"]

RICH_MENU = _config.get("rich_menu", {})
RICH_MENU_ENABLED = bool(RICH_MENU.get("enabled", False))
RICH_MENU_UNBOUND_ID = RICH_MENU.get("unbound_id", "")
RICH_MENU_BOUND_ID = RICH_MENU.get("bound_id", "")
RICH_MENU_DEFAULT_LANGUAGE = RICH_MENU.get("default_language", "zh")
RICH_MENU_MENUS = RICH_MENU.get("menus", {})

BIND_TOKEN_KEY = _config["keys"]["bind_token"].encode()

R2_CONFIG = _config.get("cloudflare_r2", {})
R2_ENABLED = R2_CONFIG.get("enabled", False)
R2_ACCOUNT_ID = R2_CONFIG.get("account_id", "")
R2_ACCESS_KEY_ID = R2_CONFIG.get("access_key_id", "")
R2_SECRET_ACCESS_KEY = R2_CONFIG.get("secret_access_key", "")
R2_BUCKET_NAME = R2_CONFIG.get("bucket_name", "")
R2_PUBLIC_URL = R2_CONFIG.get("public_url", "")

WEB_PUSH_CONFIG = _config.get("web_push", {})
VAPID_PRIVATE_KEY = WEB_PUSH_CONFIG.get("vapid_private_key", "")
VAPID_PUBLIC_KEY = WEB_PUSH_CONFIG.get("vapid_public_key", "")
VAPID_CONTACT = WEB_PUSH_CONFIG.get("contact", "mailto:admin@example.com")

PLUGIN_CONFIG = _config.get("plugins", {})

AI_MONITOR_CONFIG = _config.get("ai_monitor", {})
AI_MONITOR_ENABLED = bool(AI_MONITOR_CONFIG.get("enabled", True))
AI_MONITOR_CODEX_COMMAND = os.getenv(
    "JIETNG_CODEX_COMMAND",
    AI_MONITOR_CONFIG.get("codex_command", "codex"),
)
AI_MONITOR_MODEL = os.getenv(
    "JIETNG_CODEX_MODEL",
    AI_MONITOR_CONFIG.get("model", ""),
).strip()
try:
    AI_MONITOR_TIMEOUT_SECONDS = max(
        30,
        min(
            300,
            int(os.getenv(
                "JIETNG_CODEX_TIMEOUT",
                AI_MONITOR_CONFIG.get("timeout_seconds", 90),
            )),
        ),
    )
except (TypeError, ValueError):
    AI_MONITOR_TIMEOUT_SECONDS = 90
try:
    AI_MONITOR_SESSION_TTL_SECONDS = max(
        300,
        min(
            86400,
            int(os.getenv(
                "JIETNG_CODEX_SESSION_TTL",
                AI_MONITOR_CONFIG.get("session_ttl_seconds", 3600),
            )),
        ),
    )
except (TypeError, ValueError):
    AI_MONITOR_SESSION_TTL_SECONDS = 3600


def apply_override(songs, override_file):
    """应用 CSV override 文件到歌曲数据"""
    if not os.path.exists(override_file):
        return
    csv_map = {}
    with open(override_file, 'r', encoding='utf-8') as f:
        for row in csv.reader(f):
            if row:
                csv_map.setdefault(row[0], []).append(row[1:])

    for song in songs:
        if song['title'] not in csv_map:
            continue
        for override in csv_map[song['title']]:
            if song['type'] != override[0]:
                continue
            row = override[1:]
            *keys, value = row
            # 自动转换数字类型
            try:
                value = int(value) if value.isdigit() else float(value)
            except (ValueError, AttributeError):
                pass
            cur = song
            for k in keys[:-1]:
                if k.isdigit():
                    k = int(k)
                    while len(cur) <= k:
                        cur.append({})
                    cur = cur[k]
                else:
                    cur = cur.setdefault(k, {})
            last = keys[-1]
            if last.isdigit():
                last = int(last)
                while len(cur) <= last:
                    cur.append(None)
                cur[last] = value
            else:
                cur[last] = value

        for sheet in song.get("sheets", []):
            sheet["internalLevelValue"] = float(sheet["internalLevelValue"])


# dxdata 内存缓存：按 ver 缓存 (mtimes, songs, versions)
# mtimes 任一变化（dxdata.json / override.csv / intl_override.csv）即失效重建
# 注意：返回的 songs/versions 是共享引用，调用方禁止原地修改
_dxdata_cache: dict = {}
_dxdata_cache_lock = threading.Lock()


def read_dxdata(ver="jp"):
    """
    读取歌曲数据（带 mtime 失效缓存）

    Args:
        ver: 版本 "jp" 或 "intl"

    Returns:
        tuple: (songs, versions) — 共享引用，请勿原地修改
    """
    files = [DXDATA_FILE, OVERRIDE_FILE]
    if ver == "intl":
        files.append(INTL_OVERRIDE_FILE)
    mtimes = []
    for path in files:
        try:
            mtimes.append(os.path.getmtime(path))
        except OSError:
            mtimes.append(0.0)
    mtimes = tuple(mtimes)

    with _dxdata_cache_lock:
        cached = _dxdata_cache.get(ver)
        if cached and cached[0] == mtimes:
            return cached[1], cached[2]

    # 缓存未命中或失效；不持锁重建，避免长时间阻塞并发读
    with open(DXDATA_FILE, 'r', encoding='utf-8') as f:
        dxdata_file = json.load(f)
    songs = list(dxdata_file['songs'])

    # 通用 override（所有版本生效）
    apply_override(songs, OVERRIDE_FILE)

    # intl 专用 override
    if ver == "intl":
        apply_override(songs, INTL_OVERRIDE_FILE)

    versions = list(dxdata_file['versions'])

    with _dxdata_cache_lock:
        _dxdata_cache[ver] = (mtimes, songs, versions)
    return songs, versions

def load_user():
    """初始化用户表"""
    from modules.user_db import init_users_table
    init_users_table()
