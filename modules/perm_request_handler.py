"""
权限请求处理模块

提供发送、接受、拒绝权限请求的功能
"""

import logging
from datetime import datetime
from modules.config_loader import USERS
from modules.user_manager import get_user_value, edit_user_value
from modules.devtoken_manager import load_dev_tokens, save_dev_tokens
from modules.message_manager import (
    segaid_error,
    perm_request_sent,
    perm_request_already_sent,
    perm_request_already_granted,
    perm_request_accepted,
    perm_request_rejected,
    perm_request_not_found
)

logger = logging.getLogger(__name__)


def send_perm_request(token_id: str, to_user_id: str, requester_name: str = None) -> dict:
    """
    发送权限请求

    Args:
        token_id: 请求权限的 token ID
        to_user_id: 目标用户ID
        requester_name: 请求者名称（可选，用于显示）

    Returns:
        包含状态和消息的字典
    """

    # 验证目标用户是否存在
    if to_user_id not in USERS:
        return {
            "success": False,
            "error": "User not found",
            "message": f"User {to_user_id} does not exist"
        }

    # 验证 token 是否存在
    dev_tokens = load_dev_tokens()
    if token_id not in dev_tokens:
        return {
            "success": False,
            "error": "Invalid token",
            "message": "Token ID not found"
        }

    # 检查是否已经拥有权限
    token_permissions = dev_tokens[token_id].get('allowed_users', [])
    if to_user_id in token_permissions:
        return {
            "success": False,
            "error": "Permission already granted",
            "message": f"Token already has access to user {to_user_id}"
        }

    # 检查是否已经发送过请求
    user_perm_requests = USERS[to_user_id].get('perm_requests', [])
    for req in user_perm_requests:
        if req['token_id'] == token_id:
            return {
                "success": False,
                "error": "Request already sent",
                "message": "Permission request already sent, waiting for approval"
            }

    # 生成请求ID和时间戳
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    request_id = datetime.now().strftime('%Y%m%d%H%M%S') + "_" + token_id

    # 获取 token 的描述信息
    token_note = dev_tokens[token_id].get('note', token_id)
    if not requester_name:
        requester_name = token_note

    # 创建请求记录
    request_data = {
        "token_id": token_id,
        "token_note": token_note,
        "requester_name": requester_name,
        "timestamp": timestamp,
        "request_id": request_id
    }

    # 添加到目标用户的请求列表
    user_perm_requests.append(request_data)
    edit_user_value(to_user_id, 'perm_requests', user_perm_requests)

    logger.info(f"Permission request sent: token {token_id} -> user {to_user_id}")

    return {
        "success": True,
        "request_id": request_id,
        "message": f"Permission request sent to user {to_user_id}",
        "user_id": to_user_id
    }


def accept_perm_request(user_id: str, request_id: str) -> dict:
    """
    接受权限请求

    Args:
        user_id: 当前用户ID
        request_id: 请求ID

    Returns:
        包含状态和消息的字典
    """
    if user_id not in USERS:
        return {
            "success": False,
            "error": "User not found",
            "message": f"User {user_id} does not exist"
        }

    # 获取请求列表
    requests = USERS[user_id].get('perm_requests', [])

    # 查找对应的请求
    request_data = None
    for req in requests:
        if req['request_id'] == request_id:
            request_data = req
            break

    if not request_data:
        return {
            "success": False,
            "error": "Request not found",
            "message": "Permission request not found or already processed"
        }

    token_id = request_data['token_id']

    # 验证 token 是否还存在
    dev_tokens = load_dev_tokens()
    if token_id not in dev_tokens:
        # 移除无效请求
        requests.remove(request_data)
        edit_user_value(user_id, 'perm_requests', requests)
        return {
            "success": False,
            "error": "Invalid token",
            "message": "Token no longer exists"
        }

    # 添加权限到 token 的 allowed_users 列表
    token_permissions = dev_tokens[token_id].get('allowed_users', [])
    if user_id not in token_permissions:
        token_permissions.append(user_id)
        dev_tokens[token_id]['allowed_users'] = token_permissions

        # 保存 token 配置
        save_dev_tokens(dev_tokens)

    # 移除请求记录
    requests.remove(request_data)
    edit_user_value(user_id, 'perm_requests', requests)

    logger.info(f"Permission granted: token {token_id} can now access user {user_id}")

    return {
        "success": True,
        "token_id": token_id,
        "token_note": request_data.get('token_note', token_id),
        "requester_name": request_data.get('requester_name', token_id),
        "message": f"Permission granted to token {token_id}"
    }


def reject_perm_request(user_id: str, request_id: str) -> dict:
    """
    拒绝权限请求

    Args:
        user_id: 当前用户ID
        request_id: 请求ID

    Returns:
        包含状态和消息的字典
    """
    if user_id not in USERS:
        return {
            "success": False,
            "error": "User not found",
            "message": f"User {user_id} does not exist"
        }

    # 获取请求列表
    requests = USERS[user_id].get('perm_requests', [])

    # 查找对应的请求
    request_data = None
    for req in requests:
        if req['request_id'] == request_id:
            request_data = req
            break

    if not request_data:
        return {
            "success": False,
            "error": "Request not found",
            "message": "Permission request not found or already processed"
        }

    # 移除请求记录
    requests.remove(request_data)
    edit_user_value(user_id, 'perm_requests', requests)

    logger.info(f"Permission rejected: token {request_data['token_id']} request for user {user_id}")

    return {
        "success": True,
        "token_id": request_data['token_id'],
        "token_note": request_data.get('token_note', request_data['token_id']),
        "requester_name": request_data.get('requester_name', request_data['token_id']),
        "message": f"Permission request from token {request_data['token_id']} rejected"
    }


def get_pending_perm_requests(user_id: str) -> list:
    """
    获取待处理的权限请求列表

    Args:
        user_id: 用户ID

    Returns:
        请求列表
    """
    if user_id not in USERS:
        return []

    return USERS[user_id].get('perm_requests', [])
