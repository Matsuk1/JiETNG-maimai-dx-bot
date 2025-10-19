"""
用户管理模块

提供用户的增删改查功能,包括用户状态管理
"""

from typing import Any, Optional, Dict
import json
from modules.record_console import delete_record
from modules.config_loader import read_user, write_user, users


def add_user(user_id: str) -> None:
    """
    添加新用户

    Args:
        user_id: LINE用户ID或代理用户ID
    """
    read_user()
    users[user_id] = {
        "status": {
            "notice_read": False,
        }
    }
    write_user()


def delete_user(user_id: str) -> None:
    """
    删除用户及其所有相关数据

    Args:
        user_id: 要删除的用户ID
    """
    read_user()

    if user_id in users:
        del users[user_id]
        write_user()

    # 删除数据库中的记录
    delete_record(user_id, recent=True)
    delete_record(user_id, recent=False)


def edit_user_status(user_id: str, key: str, word: Any, operation: int = 0) -> None:
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

    if user_id not in users:
        add_user(user_id)

    if operation == 0:
        users[user_id]["status"][key] = word

    elif operation == 1:
        users[user_id]["status"][key] += word

    elif operation == 2:
        users[user_id]["status"][key] -= word

    elif operation == 4:
        del users[user_id]["status"][key]  # 修复: user -> users

    write_user()


def edit_user_status_of_all(key: str, word: Any, operation: int = 0) -> None:
    """
    批量编辑所有用户的状态

    Args:
        key: 状态键名
        word: 要设置/增加/减少的值
        operation: 操作类型 (同 edit_user_status)
    """
    for user_id in list(users.keys()):
        edit_user_status(user_id, key, word, operation)


def get_user_status(user_id: str, key: str = "") -> Optional[Any]:
    """
    获取用户状态

    Args:
        user_id: 用户ID
        key: 状态键名,为空则返回全部状态

    Returns:
        指定键的值,或全部状态字典
    """
    read_user()

    if user_id not in users:
        add_user(user_id)

    if key:
        return users[user_id]["status"].get(key, None)
    else:
        return users[user_id]["status"]
