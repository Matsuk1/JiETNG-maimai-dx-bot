"""
LINE消息发送模块

提供smart_reply和smart_push功能,集成公告推送
"""

import logging
import tempfile
import os
import random
from datetime import datetime
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    PushMessageRequest,
    TextMessage
)
from modules.config_loader import USERS
from modules.user_manager import (
    get_user_value,
    edit_user_value,
    _migrate_user_notice_data,
    has_user_read_notice,
    record_notice_read
)
from modules.notice_manager import get_latest_notice, get_latest_published_notice
from modules.perm_request_handler import get_pending_perm_requests
from modules.perm_request_generator import generate_perm_request_message
from modules.message_manager import generate_notice_flex, generate_error_alert_flex, system_error

logger = logging.getLogger(__name__)


def smart_reply(user_id: str, reply_token: str, messages, configuration: Configuration, divider: str = "-" * 33):
    """
    智能回复函数 - 自动附加好友申请、未读公告

    消息优先级：好友申请 > 公告
    仅当消息数量 < 5 时才添加附加消息

    Args:
        user_id: LINE用户ID
        reply_token: 回复令牌
        messages: 要发送的消息(单个或列表)
        configuration: LINE API配置对象
        divider: 分隔线字符串
    """
    if not isinstance(messages, list):
        messages = [messages]

    # 保存原始消息中的 quick_reply（如果存在）
    saved_quick_reply = None
    for msg in messages:
        if hasattr(msg, 'quick_reply') and msg.quick_reply is not None:
            saved_quick_reply = msg.quick_reply
            msg.quick_reply = None  # 移除原消息的 quick_reply
            break

    # 只有当消息数量小于5时，才添加附加消息
    if len(messages) < 5:
        # 优先级1: 好友申请与权限申请消息
        if user_id in USERS:
            perm_requests = get_pending_perm_requests(user_id)
            if perm_requests and len(messages) < 5:
                perm_request_msg = generate_perm_request_message(perm_requests, user_id)
                if perm_request_msg:
                    messages.append(perm_request_msg)

        # 优先级2: 公告消息（使用新的交互追踪系统）
        if len(messages) < 5 and user_id:
            # 执行用户数据迁移（如果需要）
            _migrate_user_notice_data(user_id)

            # 获取最新已发布的公告
            latest_notice = get_latest_published_notice()

            if latest_notice:
                notice_id = latest_notice['id']

                # 检查用户是否已阅读
                has_read = has_user_read_notice(user_id, notice_id)

                if not has_read:
                    # 推送公告并标记为已读
                    notice_flex = generate_notice_flex(latest_notice, user_id)
                    messages.append(notice_flex)
                    record_notice_read(user_id, notice_id)

    # 如果有保存的 quick_reply，将其移动到最后一条消息上
    if saved_quick_reply is not None and messages:
        messages[-1].quick_reply = saved_quick_reply

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=messages
            )
        )


def smart_push(user_id: str, messages, configuration: Configuration):
    """
    推送消息函数

    Args:
        user_id: LINE用户ID
        messages: 要推送的消息(单个或列表)
        configuration: LINE API配置对象
    """
    if not isinstance(messages, list):
        messages = [messages]

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.push_message(
            PushMessageRequest(
                to=user_id,
                messages=messages
            )
        )


def notify_admins_error(
    error_title: str,
    error_details: str,
    context: dict,
    admin_id: list,
    configuration: Configuration,
    error_notification_enabled: bool = True,
    max_length: int = 4000,
    user_id: str = None,
    reply_token: str = None
):
    """
    通知管理员发生错误，并可选择性地回复用户

    Args:
        error_title: 错误标题
        error_details: 错误详情
        context: 上下文信息
        admin_id: 管理员ID列表
        configuration: LINE API配置对象
        error_notification_enabled: 是否启用错误通知
        max_length: 错误消息最大长度
        user_id: 用户ID（可选，用于回复用户）
        reply_token: 回复令牌（可选，用于回复用户）
    """
    # 先回复用户（如果提供了参数）
    if user_id and reply_token:
        try:
            smart_reply(user_id, reply_token, system_error(user_id), configuration)
        except Exception as e:
            logger.error(f"[LineMessenger] ✗ Failed to reply error message: error={e}")

    if not error_notification_enabled:
        return

    try:
        # 构建错误消息
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 生成 Flex Message
        flex_message = generate_error_alert_flex(error_title, error_details, context, timestamp)

        # 如果错误信息过长，需要分段发送额外的详细信息
        if len(error_details) > 800:
            # 发送给所有管理员
            for admin_user_id in admin_id:
                try:
                    # 先发送 Flex Message（包含截断的详情）
                    smart_push(admin_user_id, flex_message, configuration)

                    # 分段发送完整详细信息
                    detail_chunks = [error_details[i:i+900] for i in range(0, len(error_details), 900)]
                    for i, chunk in enumerate(detail_chunks):
                        chunk_msg = f"Details ({i+1}/{len(detail_chunks)}):\n{chunk}"
                        smart_push(admin_user_id, TextMessage(text=chunk_msg), configuration)
                except Exception as e:
                    logger.error(f"[LineMessenger] ✗ Failed to notify admin: admin_id={admin_user_id}, error={e}")
        else:
            # 错误信息不长，直接发送 Flex Message
            for admin_user_id in admin_id:
                try:
                    smart_push(admin_user_id, flex_message, configuration)
                except Exception as e:
                    logger.error(f"[LineMessenger] ✗ Failed to notify admin: admin_id={admin_user_id}, error={e}")

    except Exception as e:
        # 通知系统本身出错，记录到日志
        logger.error(f"[LineMessenger] ✗ Error notification system failed: error={e}", exc_info=True)
