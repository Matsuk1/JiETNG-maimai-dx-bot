"""
配置加载模块

负责加载和管理配置文件、歌曲数据、用户数据等全局配置
"""

import copy
import json
import os
import secrets
import csv
from typing import Dict, List, Any

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
    "domain": "jietng.example.com",
    "port": 5000,
    "file_path": {
        "dxdata_list": "./data/dxdata.json",
        "dxdata_version": "./data/dxdata_version.json",
        "re_dxdata_list": "./data/re_dxdata.json",
        "user_list": "./data/user.json.enc",
        "notice_file": "./data/notice.json",
        "font": "./assets/fonts/mplus-jietng.ttf",
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
        "dxdata": ""
    },
    "line_channel": {
        "account_id": "",
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
admin_id = _config["admin_id"]
ADMIN_PASSWORD = _config["admin_password"]
MAIMAI_VERSION = _config["maimai_version"]

# 域名字段
DOMAIN = _config["domain"]

# 服务端口
PORT = _config["port"]

# 文件路径字段
file_path = _config["file_path"]
dxdata_list = file_path["dxdata_list"]
DXDATA_VERSION_FILE = file_path["dxdata_version"]
re_dxdata_list = file_path["re_dxdata_list"]
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

# LINE 配置字段
line_channel = _config["line_channel"]
LINE_ACCOUNT_ID = line_channel["account_id"]
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

# 用户数据脏标记（用于延迟写入）
_user_data_dirty = False

def read_dxdata(ver="jp"):
    global songs, versions
    dxdata_file = json.load(open(dxdata_list, 'r', encoding='utf-8'))
    songs.clear()
    
    def is_int(s):
        return s.isdigit()

    if ver == "intl":
        csv_map = {}
        with open(re_dxdata_list, 'r', encoding='utf-8') as f:
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
    
    songs.extend(dxdata_file['songs'])
    versions.clear()
    versions.extend(dxdata_file['versions'])

def read_user():
    global users, _user_data_dirty
    if not users:  # 只在未加载时读取
        users.update(read_encrypted_json(user_list, USER_DATA_KEY))
    _user_data_dirty = False

def write_user(force=False):
    """
    写入用户数据

    Args:
        force: 强制写入，忽略脏标记
    """
    global _user_data_dirty
    if force or _user_data_dirty:
        write_encrypted_json(users, user_list, USER_DATA_KEY)
        _user_data_dirty = False

def mark_user_dirty():
    """标记用户数据已修改"""
    global _user_data_dirty
    _user_data_dirty = True
