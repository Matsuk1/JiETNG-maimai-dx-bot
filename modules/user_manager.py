"""
用户管理模块

提供用户的增删改查功能,包括用户状态管理
"""

from typing import Any, Optional, Dict
import logging
import threading
from datetime import datetime
from modules.record_manager import delete_record
from modules.config_loader import write_user, mark_user_dirty, USERS
from modules.notice_manager import get_latest_published_notice

logger = logging.getLogger(__name__)

# 用户昵称缓存 (避免频繁调用LINE API)
nickname_cache = {}
nickname_cache_lock = threading.Lock()
NICKNAME_CACHE_TIMEOUT = 43200  # 12小时缓存


def add_user(user_id: str) -> None:
    """
    添加新用户

    Args:
        user_id: LINE用户ID或代理用户ID
    """

    if user_id in USERS:
        return

    USERS[user_id] = {
        "notice_interactions": {}
    }
    mark_user_dirty()
    write_user()


def delete_user(user_id: str) -> None:
    """
    删除用户及其所有相关数据

    Args:
        user_id: 要删除的用户ID
    """

    if user_id in USERS:
        del USERS[user_id]
        mark_user_dirty()
        write_user()

    # 删除数据库中的记录
    delete_record(user_id, recent=True)
    delete_record(user_id, recent=False)


def edit_user_value(user_id: str, key: str, word: Any, operation: int = 0) -> None:
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
    if user_id not in USERS:
        add_user(user_id)

    if operation == 0:
        USERS[user_id][key] = word

    elif operation == 1:
        USERS[user_id][key] += word

    elif operation == 2:
        USERS[user_id][key] -= word

    elif operation == 4:
        del USERS[user_id][key]

    mark_user_dirty()
    write_user(force=True)


def clear_user_value(key: str, word: Any, operation: int = 0) -> None:
    """
    批量编辑所有用户的状态

    Args:
        key: 状态键名
        word: 要设置/增加/减少的值
        operation: 操作类型 (同 edit_user_value)
    """
    for user_id in list(USERS.keys()):
        edit_user_value(user_id, key, word, operation)


def get_user_value(user_id: str, key: str = "") -> Optional[Any]:
    """
    获取用户状态

    Args:
        user_id: 用户ID
        key: 状态键名,为空则返回全部状态

    Returns:
        指定键的值,或全部状态字典
    """
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
            logger.warning(f"[User] ⚠ User not found: user_id={user_id}, reason=may_have_blocked_bot")
            nickname = "Unknown (Blocked/Deleted)"
        else:
            logger.error(f"[User] ✗ Failed to get nickname: user_id={user_id}, error={e}")
            nickname = "Unknown (API Error)"

        # 缓存错误结果(避免重复失败的API调用)
        with nickname_cache_lock:
            nickname_cache[user_id] = {
                'nickname': nickname,
                'time': datetime.now()
            }

        return nickname


# ==================== 公告交互追踪功能 ====================

def _migrate_user_notice_data(user_id: str) -> None:
    """
    迁移用户公告数据到v2格式
    从旧的 notice_read 布尔值迁移到 notice_interactions 对象

    Args:
        user_id: 用户ID
    """
    if user_id not in USERS:
        add_user(user_id)
        return

    user_data = USERS[user_id]

    # 如果已有新格式,跳过
    if 'notice_interactions' in user_data:
        return

    # 迁移旧的 notice_read 布尔值
    old_notice_read = user_data.get('notice_read', True)

    # 初始化新结构
    user_data['notice_interactions'] = {}

    # 如果用户未读最新公告,标记最新公告为未读
    if not old_notice_read:
        latest_notice = get_latest_published_notice()
        if latest_notice:
            notice_id = latest_notice['id']
            user_data['notice_interactions'][notice_id] = {
                'read': False,
                'read_at': None,
                'vote': None,
                'voted_at': None
            }

    # 删除旧字段
    if 'notice_read' in user_data:
        del user_data['notice_read']

    mark_user_dirty()


def record_notice_read(user_id: str, notice_id: str) -> None:
    """
    记录用户阅读公告

    Args:
        user_id: 用户ID
        notice_id: 公告ID
    """
    if user_id not in USERS:
        add_user(user_id)

    _migrate_user_notice_data(user_id)

    if 'notice_interactions' not in USERS[user_id]:
        USERS[user_id]['notice_interactions'] = {}

    if notice_id not in USERS[user_id]['notice_interactions']:
        USERS[user_id]['notice_interactions'][notice_id] = {
            'read': False,
            'read_at': None,
            'vote': None,
            'voted_at': None
        }

    USERS[user_id]['notice_interactions'][notice_id]['read'] = True
    USERS[user_id]['notice_interactions'][notice_id]['read_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    mark_user_dirty()
    write_user(force=True)


def record_notice_vote(user_id: str, notice_id: str, vote_type: str) -> bool:
    """
    记录用户投票

    Args:
        user_id: 用户ID
        notice_id: 公告ID
        vote_type: 'support' 或 'oppose'

    Returns:
        bool: 是否成功
    """
    if user_id not in USERS:
        return False

    _migrate_user_notice_data(user_id)

    if 'notice_interactions' not in USERS[user_id]:
        USERS[user_id]['notice_interactions'] = {}

    if notice_id not in USERS[user_id]['notice_interactions']:
        USERS[user_id]['notice_interactions'][notice_id] = {
            'read': True,
            'read_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'vote': None,
            'voted_at': None
        }

    USERS[user_id]['notice_interactions'][notice_id]['vote'] = vote_type
    USERS[user_id]['notice_interactions'][notice_id]['voted_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # 确保投票时也标记为已读
    if not USERS[user_id]['notice_interactions'][notice_id]['read']:
        USERS[user_id]['notice_interactions'][notice_id]['read'] = True
        USERS[user_id]['notice_interactions'][notice_id]['read_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    mark_user_dirty()
    write_user(force=True)

    return True


def get_notice_interaction(user_id: str, notice_id: str) -> Optional[Dict]:
    """
    获取用户与公告的交互状态

    Args:
        user_id: 用户ID
        notice_id: 公告ID

    Returns:
        交互状态字典或None
    """
    if user_id not in USERS:
        return None

    _migrate_user_notice_data(user_id)

    interactions = USERS[user_id].get('notice_interactions', {})
    return interactions.get(notice_id)


def has_user_read_notice(user_id: str, notice_id: str) -> bool:
    """
    检查用户是否已阅读指定公告

    Args:
        user_id: 用户ID
        notice_id: 公告ID

    Returns:
        bool: 是否已阅读
    """
    interaction = get_notice_interaction(user_id, notice_id)
    return interaction.get('read', False) if interaction else False


def clear_notice_read_status(notice_id: str) -> None:
    """
    清除所有用户对指定公告的阅读状态(发布新公告时使用)

    Args:
        notice_id: 公告ID
    """
    for user_id in list(USERS.keys()):
        _migrate_user_notice_data(user_id)

        if 'notice_interactions' not in USERS[user_id]:
            USERS[user_id]['notice_interactions'] = {}

        USERS[user_id]['notice_interactions'][notice_id] = {
            'read': False,
            'read_at': None,
            'vote': None,
            'voted_at': None
        }

    mark_user_dirty()
    write_user()
