"""
配置加载模块

负责加载和管理配置文件、歌曲数据、用户数据等全局配置
"""

import copy
import json
import os
import secrets
import csv

from cryptography.fernet import Fernet
from modules.json_encrypt import *

CONFIG_PATH = "./config.json"

# 默认配置
default_config = {
    "admin_id": [],
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
    "port": 5000,
    "file_path": {
        "dxdata_list": "./data/dxdata.json",
        "dxdata_version": "./data/dxdata_version.json",
        "re_dxdata_list": "./data/re_dxdata.json",
        "user_list": "./data/user.json.enc",
        "notice_file": "./data/notice.json",
        "dev_tokens": "./data/dev_tokens.json",
        "font": "./assets/fonts/mplus-jietng.ttf",
        "logo": "./assets/pics/logo.png",
        "level_cache": "./data/level_cache",
        "covers": "./assets/covers",
        "plates": "./assets/plates",
        "icon_type": "./assets/icon/type",
        "icon_score": "./assets/icon/score",
        "icon_dx_star": "./assets/icon/dx_star",
        "icon_combo": "./assets/icon/combo",
        "icon_sync": "./assets/icon/sync",
        "icon_base": "./assets/icon"
    },
    "record_database": {
        "host": "localhost",
        "user": "root",
        "password": "",
        "database": "records"
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
    "keys": {
        "user_data": "",
        "bind_token": "",
        "imgur_client_id": ""
    }
}

# 自动创建 config 目录
config_dir = os.path.dirname(CONFIG_PATH)
if config_dir:
    os.makedirs(config_dir, exist_ok=True)

def _ensure_fernet_key(value: str) -> str:

    if not isinstance(value, str):
        value = ""

    try:
        Fernet(value.encode())
    except (ValueError, TypeError):
        value = Fernet.generate_key().decode()

    return value

def _ensure_bind_token(value: str) -> str:
    if not isinstance(value, str) or not value:
        value = secrets.token_urlsafe(16)

    return value

# 加载配置，若不存在则创建；若缺字段则补全
if not os.path.exists(CONFIG_PATH):
    _config = copy.deepcopy(default_config)
else:
    with open(CONFIG_PATH, 'r', encoding='utf-8') as file:
        _config = json.load(file)

    # 递归补字段
    def deep_update(default, current):
        for key, value in default.items():
            if key not in current:
                current[key] = value
            elif isinstance(value, dict):
                deep_update(value, current[key])

    deep_update(default_config, _config)

_config["keys"]["user_data"] = _ensure_fernet_key(_config["keys"].get("user_data", ""))
_config["keys"]["bind_token"] = _ensure_bind_token(_config["keys"].get("bind_token", ""))

# 写回更新后的配置
with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
    json.dump(_config, f, indent=4, ensure_ascii=False)

# 顶层字段
ADMIN_ID = _config["admin_id"]
ADMIN_PASSWORD = _config["admin_password"]
MAIMAI_VERSION = _config["maimai_version"]
TEMP_VERSION = _config["temp_version"]

# 域名字段
DOMAIN = _config["domain"]

# 服务端口
PORT = _config["port"]

# 文件路径字段
FILE_PATH = _config["file_path"]
DXDATA_LIST = FILE_PATH["dxdata_list"]
DXDATA_VERSION_FILE = FILE_PATH["dxdata_version"]
RE_DXDATA_LIST = FILE_PATH["re_dxdata_list"]
USER_LIST = FILE_PATH["user_list"]
NOTICE_FILE = FILE_PATH["notice_file"]
DEV_TOKENS_FILE = FILE_PATH["dev_tokens"]
FONT_PATH = FILE_PATH["font"]
LOGO_PATH = FILE_PATH["logo"]
LEVEL_CACHE_DIR = FILE_PATH["level_cache"]
COVERS_DIR = FILE_PATH["covers"]
PLATES_DIR = FILE_PATH["plates"]
ICON_TYPE_DIR = FILE_PATH["icon_type"]
ICON_SCORE_DIR = FILE_PATH["icon_score"]
ICON_DX_STAR_DIR = FILE_PATH["icon_dx_star"]
ICON_COMBO_DIR = FILE_PATH["icon_combo"]
ICON_SYNC_DIR = FILE_PATH["icon_sync"]
ICON_BASE_DIR = FILE_PATH["icon_base"]

# 数据库配置字段
RECORD_DATABASE = _config["record_database"]
DB_HOST = RECORD_DATABASE["host"]
DB_USER = RECORD_DATABASE["user"]
DB_PASSWORD = RECORD_DATABASE["password"]
DB_NAME = RECORD_DATABASE["database"]

# URL 配置字段
URLS = _config["urls"]
LINE_ADDING_URL = URLS["line_adding"]
SUPPORT_PAGE = URLS["support_page"]
DXDATA_URL = URLS["dxdata"]

# LINE 配置字段
LINE_CHANNEL = _config["line_channel"]
LINE_ACCOUNT_ID = LINE_CHANNEL["account_id"]
LINE_CHANNEL_ACCESS_TOKEN = LINE_CHANNEL["access_token"]
LINE_CHANNEL_SECRET = LINE_CHANNEL["secret"]

# key 配置字段
KEYS = _config["keys"]
USER_DATA_KEY = KEYS["user_data"].encode()
BIND_TOKEN_KEY = KEYS["bind_token"].encode()
IMGUR_CLIENT_ID = KEYS.get("imgur_client_id", "")

# 全局缓存数据
SONGS = []
VERSIONS = []
USERS = {}

# 用户数据脏标记（用于延迟写入）
_user_data_dirty = False

def read_dxdata(ver="jp"):
    global SONGS, VERSIONS
    dxdata_file = json.load(open(DXDATA_LIST, 'r', encoding='utf-8'))
    SONGS.clear()

    def is_int(s):
        return s.isdigit()

    if ver == "intl":
        csv_map = {}
        with open(RE_DXDATA_LIST, 'r', encoding='utf-8') as f:
            for row in csv.reader(f):
                if row:
                    csv_map[row[0]] = row[1:]

        for song in dxdata_file['songs']:
            if song['title'] not in csv_map:
                continue
            if song['type'] != csv_map[song['title']][0]:
                continue
            row = csv_map[song['title']][1:]
            *keys, value = row
            cur = song
            for k in keys[:-1]:
                if is_int(k):
                    k = int(k)
                    while len(cur) <= k:
                        cur.append({})
                    cur = cur[k]
                else:
                    cur = cur.setdefault(k, {})
            last = keys[-1]
            if is_int(last):
                last = int(last)
                while len(cur) <= last:
                    cur.append(None)
                cur[last] = value
            else:
                cur[last] = value

    SONGS.extend(dxdata_file['songs'])
    VERSIONS.clear()
    VERSIONS.extend(dxdata_file['versions'])

def load_user():
    global USERS, _user_data_dirty
    if not USERS:  # 只在未加载时读取
        USERS.update(read_encrypted_json(USER_LIST, USER_DATA_KEY))
    _user_data_dirty = False

def write_user(force=False):
    """
    写入用户数据

    Args:
        force: 强制写入，忽略脏标记
    """
    global _user_data_dirty
    if force or _user_data_dirty:
        write_encrypted_json(USERS, USER_LIST, USER_DATA_KEY)
        _user_data_dirty = False

def mark_user_dirty():
    """标记用户数据已修改"""
    global _user_data_dirty
    _user_data_dirty = True
