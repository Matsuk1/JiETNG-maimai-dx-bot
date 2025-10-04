import copy
import json
import os
import secrets

from cryptography.fernet import Fernet

from json_encrypt import *

CONFIG_PATH = "./config.json"

# 默认配置
default_config = {
    "admin_id": [],
    "maimai_version": {
        "jp": [],
        "intl": []
    },
    "domain": "jietng.example.com",
    "port": 5000,
    "file_path": {
        "dxdata_list": "./data/dxdata.json",
        "user_list": "./data/user.json.enc",
        "notice_file": "./data/notice.json",
        "font": "./assets/fonts/mplus-1p-regular.ttf",
        "logo": "./assets/pics/logo.png"
    },
    "record_database": {
        "host": "localhost",
        "user": "root",
        "password": "",
        "database": "records"
    },
    "urls": {
        "line_adding": "",
        "dxdata": "",
        "proxy": ""
    },
    "line_channel": {
        "access_token": "",
        "secret": ""
    },
    "keys": {
        "user_data": "",
        "bind_token": ""
    }
}

# 自动创建 config 目录
config_dir = os.path.dirname(CONFIG_PATH)
if config_dir:
    os.makedirs(config_dir, exist_ok=True)


def _ensure_fernet_key(value: str) -> str:
    """确保提供的字符串可以作为 Fernet key 使用，若不合法则重新生成。"""

    if not isinstance(value, str):
        value = ""

    try:
        Fernet(value.encode())
    except (ValueError, TypeError):
        value = Fernet.generate_key().decode()

    return value


def _ensure_bind_token(value: str) -> str:
    """bind_token 允许为空，但为空时自动生成一个随机字符串，避免运行时报错。"""

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
admin_id = _config["admin_id"]
MAIMAI_VERSION = _config["maimai_version"]

# 域名字段
DOMAIN = _config["domain"]

# 服务端口
PORT = _config["port"]

# 文件路径字段
file_path = _config["file_path"]
dxdata_list = file_path["dxdata_list"]
user_list = file_path["user_list"]
NOTICE_FILE = file_path["notice_file"]
font_path = file_path["font"]
LOGO_PATH = file_path["logo"]

# 数据库配置字段
record_database = _config["record_database"]
HOST = record_database["host"]
USER = record_database["user"]
PASSWORD = record_database["password"]
DATABASE = record_database["database"]

# URL 配置字段
urls = _config["urls"]
LINE_ADDING_URL = urls["line_adding"]
DXDATA_URL = urls["dxdata"]
PROXY_URL = urls["proxy"]

# LINE 配置字段
line_channel = _config["line_channel"]
LINE_CHANNEL_ACCESS_TOKEN = line_channel["access_token"]
LINE_CHANNEL_SECRET = line_channel["secret"]

# key 配置字段
keys = _config["keys"]
USER_DATA_KEY = keys["user_data"].encode()
BIND_TOKEN_KEY = keys["bind_token"].encode()

# 全局缓存数据
songs = []
versions = []
users = {}

def read_dxdata():
    global songs, versions
    dxdata_file = json.load(open(dxdata_list, 'r', encoding='utf-8'))
    songs.clear()
    songs.extend(dxdata_file['songs'])
    versions.clear()
    versions.extend(dxdata_file['versions'])

def read_user():
    global users
    users.clear()
    users.update(read_encrypted_json(user_list, USER_DATA_KEY))

def write_user():
    write_encrypted_json(users, user_list, USER_DATA_KEY)
