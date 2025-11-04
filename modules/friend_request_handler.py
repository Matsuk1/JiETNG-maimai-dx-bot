"""
好友申请处理模块

提供发送、接受、拒绝好友申请的功能
"""

import logging
from datetime import datetime
from linebot.v3.messaging import TextMessage
from modules.config_loader import USERS
from modules.user_manager import get_user_value, edit_user_value, read_user
from modules.reply_text import (
    segaid_error,
    friendid_error,
    friendid_self_error,
    friend_request_sent,
    friend_request_already_sent,
    friend_request_already_friend,
    friend_request_accepted,
    friend_request_rejected,
    friend_request_not_found,
    friend_request_mutual_accepted
)

logger = logging.getLogger(__name__)


def send_friend_request(from_user_id: str, to_user_id: str) -> TextMessage:
    """
    发送好友申请

    Args:
        from_user_id: 发送申请的用户ID
        to_user_id: 接收申请的用户ID

    Returns:
        TextMessage对象
    """
    read_user()

    # 验证发送者是否存在
    if from_user_id not in USERS:
        return segaid_error

    # 验证接收者是否存在
    if to_user_id not in USERS:
        return friendid_error

    # 不能给自己发送申请
    if from_user_id == to_user_id:
        return friendid_self_error

    # 检查是否已经是好友
    from_friends_list = USERS[from_user_id].get('line_friends', [])
    if to_user_id in from_friends_list:
        to_user_name = to_user_id
        if 'personal_info' in USERS[to_user_id] and 'name' in USERS[to_user_id]['personal_info']:
            to_user_name = USERS[to_user_id]['personal_info']['name']
        return friend_request_already_friend(to_user_name)

    # 检查是否已经发送过申请
    to_requests = USERS[to_user_id].get('friend_requests', [])
    for req in to_requests:
        if req['from_user_id'] == from_user_id:
            return friend_request_already_sent

    # 检查对方是否也给自己发送过申请（双向申请自动通过）
    from_requests = USERS[from_user_id].get('friend_requests', [])
    mutual_request = None
    for req in from_requests:
        if req['from_user_id'] == to_user_id:
            mutual_request = req
            break

    if mutual_request:
        # 双向申请，自动通过
        # 双向添加好友
        from_friends = USERS[from_user_id].get('line_friends', [])
        if to_user_id not in from_friends:
            from_friends.append(to_user_id)
            edit_user_value(from_user_id, 'line_friends', from_friends)

        to_friends = USERS[to_user_id].get('line_friends', [])
        if from_user_id not in to_friends:
            to_friends.append(from_user_id)
            edit_user_value(to_user_id, 'line_friends', to_friends)

        # 移除双方的申请记录
        from_requests.remove(mutual_request)
        edit_user_value(from_user_id, 'friend_requests', from_requests)

        # 获取对方昵称
        to_user_name = to_user_id
        if 'personal_info' in USERS[to_user_id] and 'name' in USERS[to_user_id]['personal_info']:
            to_user_name = USERS[to_user_id]['personal_info']['name']

        return friend_request_mutual_accepted(to_user_name)

    # 生成申请ID和时间戳
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    request_id = datetime.now().strftime('%Y%m%d%H%M%S') + "_" + from_user_id

    # 获取发送者昵称
    from_user_name = from_user_id
    if 'personal_info' in USERS[from_user_id] and 'name' in USERS[from_user_id]['personal_info']:
        from_user_name = USERS[from_user_id]['personal_info']['name']

    # 创建申请记录
    request_data = {
        "from_user_id": from_user_id,
        "from_user_name": from_user_name,
        "timestamp": timestamp,
        "request_id": request_id
    }

    # 添加到接收者的申请列表
    to_requests.append(request_data)
    edit_user_value(to_user_id, 'friend_requests', to_requests)

    # 获取接收者昵称
    to_user_name = to_user_id
    if 'personal_info' in USERS[to_user_id] and 'name' in USERS[to_user_id]['personal_info']:
        to_user_name = USERS[to_user_id]['personal_info']['name']

    return friend_request_sent(to_user_name)


def accept_friend_request(user_id: str, request_id: str) -> TextMessage:
    """
    接受好友申请

    Args:
        user_id: 当前用户ID
        request_id: 申请ID

    Returns:
        TextMessage对象
    """
    read_user()

    if user_id not in USERS:
        return segaid_error

    # 获取申请列表
    requests = USERS[user_id].get('friend_requests', [])

    # 查找对应的申请
    request_data = None
    for req in requests:
        if req['request_id'] == request_id:
            request_data = req
            break

    if not request_data:
        return friend_request_not_found

    from_user_id = request_data['from_user_id']

    # 验证发送者是否还存在
    if from_user_id not in USERS:
        # 移除无效申请
        requests.remove(request_data)
        edit_user_value(user_id, 'friend_requests', requests)
        return friendid_error

    # 双向添加好友
    # 添加到当前用户的好友列表
    user_friends = USERS[user_id].get('line_friends', [])
    if from_user_id not in user_friends:
        user_friends.append(from_user_id)
        edit_user_value(user_id, 'line_friends', user_friends)

    # 添加到发送者的好友列表
    from_user_friends = USERS[from_user_id].get('line_friends', [])
    if user_id not in from_user_friends:
        from_user_friends.append(user_id)
        edit_user_value(from_user_id, 'line_friends', from_user_friends)

    # 移除申请记录
    requests.remove(request_data)
    edit_user_value(user_id, 'friend_requests', requests)

    # 获取双方昵称
    from_user_name = request_data.get('from_user_name', from_user_id)

    return friend_request_accepted(from_user_name)


def reject_friend_request(user_id: str, request_id: str) -> TextMessage:
    """
    拒绝好友申请

    Args:
        user_id: 当前用户ID
        request_id: 申请ID

    Returns:
        TextMessage对象
    """
    read_user()

    if user_id not in USERS:
        return segaid_error

    # 获取申请列表
    requests = USERS[user_id].get('friend_requests', [])

    # 查找对应的申请
    request_data = None
    for req in requests:
        if req['request_id'] == request_id:
            request_data = req
            break

    if not request_data:
        return friend_request_not_found

    # 移除申请记录
    requests.remove(request_data)
    edit_user_value(user_id, 'friend_requests', requests)

    from_user_name = request_data.get('from_user_name', '相手')

    return friend_request_rejected(from_user_name)


def get_pending_requests(user_id: str) -> list:
    """
    获取待处理的好友申请列表

    Args:
        user_id: 用户ID

    Returns:
        申请列表
    """
    if user_id not in USERS:
        return []

    return USERS[user_id].get('friend_requests', [])
