"""
用户管理模块

提供用户的增删改查功能,包括用户状态管理
"""

from typing import Any, Optional, Dict
import json
import logging
import threading
from datetime import datetime
from modules.record_console import delete_record
from modules.config_loader import read_user, write_user, mark_user_dirty, USERS

logger = logging.getLogger(__name__)

# 用户昵称缓存 (避免频繁调用LINE API)
nickname_cache = {}
nickname_cache_lock = threading.Lock()
NICKNAME_CACHE_TIMEOUT = 300  # 5分钟缓存


def add_user(user_id: str) -> None:
    """
    添加新用户

    Args:
        user_id: LINE用户ID或代理用户ID
    """
    read_user()
    USERS[user_id] = {
        "notice_read": False
    }
    mark_user_dirty()
    write_user()


def delete_user(user_id: str) -> None:
    """
    删除用户及其所有相关数据

    Args:
        user_id: 要删除的用户ID
    """
    read_user()

    if user_id in USERS:
        del USERS[user_id]
        mark_user_dirty()
        write_user()

    # 删除数据库中的记录
    delete_record(user_id, recent=True)
    delete_record(user_id, recent=False)


def edit_user_key(user_id: str, key: str, word: Any, operation: int = 0) -> None:
    """
    编辑用户状态

    Args:
        user_id: 用户ID
        key: 状态键名
        word: 要设置/增加/减少的值
        operation: 操作类型
            0 - 设置值 (默认)
            1 - 增加值
            2 - 减少值
            4 - 删除键
    """
    read_user()

    if user_id not in USERS:
        add_user(user_id)
        return  # add_user 已经写入

    if operation == 0:
        USERS[user_id][key] = word

    elif operation == 1:
        USERS[user_id][key] += word

    elif operation == 2:
        USERS[user_id][key] -= word

    elif operation == 4:
        del USERS[user_id][key]

    mark_user_dirty()
    write_user()


def clear_user_key(key: str, word: Any, operation: int = 0) -> None:
    """
    批量编辑所有用户的状态

    Args:
        key: 状态键名
        word: 要设置/增加/减少的值
        operation: 操作类型 (同 edit_user_key)
    """
    for user_id in list(USERS.keys()):
        edit_user_key(user_id, key, word, operation)


def get_user_key(user_id: str, key: str = "") -> Optional[Any]:
    """
    获取用户状态

    Args:
        user_id: 用户ID
        key: 状态键名,为空则返回全部状态

    Returns:
        指定键的值,或全部状态字典
    """
    read_user()

    if user_id not in USERS:
        add_user(user_id)

    if key:
        return USERS[user_id].get(key, None)
    else:
        return USERS[user_id]


def get_user_nickname(user_id: str, line_bot_api, use_cache: bool = True) -> str:
    """
    通过LINE SDK获取用户昵称

    Args:
        user_id: LINE用户ID
        line_bot_api: MessagingApi实例
        use_cache: 是否使用缓存 (默认True)

    Returns:
        用户昵称字符串
    """
    # 检查缓存
    if use_cache:
        with nickname_cache_lock:
            if user_id in nickname_cache:
                cached_data = nickname_cache[user_id]
                # 检查缓存是否过期
                if (datetime.now() - cached_data['time']).seconds < NICKNAME_CACHE_TIMEOUT:
                    return cached_data['nickname']

    # 缓存未命中或已过期,从API获取
    try:
        profile = line_bot_api.get_profile(user_id)
        nickname = profile.display_name

        # 更新缓存
        with nickname_cache_lock:
            nickname_cache[user_id] = {
                'nickname': nickname,
                'time': datetime.now()
            }

        return nickname
    except Exception as e:
        # 404错误是正常的(用户可能删除了Bot),使用debug级别记录
        if "404" in str(e):
            logger.debug(f"User {user_id} not found (may have blocked/deleted bot)")
            nickname = "Unknown (Blocked/Deleted)"
        else:
            logger.warning(f"Failed to get nickname for {user_id}: {e}")
            nickname = "Unknown (API Error)"

        # 缓存错误结果(避免重复失败的API调用)
        with nickname_cache_lock:
            nickname_cache[user_id] = {
                'nickname': nickname,
                'time': datetime.now()
            }

        return nickname
