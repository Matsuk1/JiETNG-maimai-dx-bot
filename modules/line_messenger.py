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
from modules.user_manager import get_user_value, edit_user_value
from modules.notice_manager import get_latest_notice
from modules.perm_request_handler import get_pending_perm_requests
from modules.perm_request_generator import generate_perm_request_message
from modules.message_manager import tip_messages, get_notice_header, generate_error_alert_flex

logger = logging.getLogger(__name__)


def get_random_tip(user_id=None):
    """
    从 tip_messages 列表中随机返回一条 tips（支持多语言）

    Args:
        user_id: 用户ID，用于获取用户语言设置

    Returns:
        TextMessage: 随机选择的 tips 消息
    """
    if not tip_messages:
        return None

    # 获取用户语言设置，默认为日语
    language = 'ja'
    if user_id and user_id in USERS:
        language = get_user_value(user_id, "language") or 'ja'

    # 随机选择一条 tip
    tip = random.choice(tip_messages)

    # 获取对应语言的文本，如果不存在则使用日语
    if isinstance(tip, dict):
        tip_text = tip.get(language, tip.get('ja', ''))
    else:
        # 兼容旧格式（纯字符串）
        tip_text = tip

    if tip_text:
        return TextMessage(text=tip_text)
    return None


def smart_reply(user_id: str, reply_token: str, messages, configuration: Configuration, divider: str = "-" * 33):
    """
    智能回复函数 - 自动附加好友申请、未读公告和 tips

    消息优先级：好友申请 > 公告 > Tips
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

        # 优先级2: 公告消息
        if len(messages) < 5:
            if user_id not in USERS:
                notice_read = True
            else:
                notice_read = get_user_value(user_id, "notice_read")

            if not notice_read:
                notice_json = get_latest_notice()
                if notice_json:
                    notice_header = get_notice_header(user_id)
                    notice = f"{notice_header}\n{divider}\n{notice_json['content']}\n{divider}\n{notice_json['date']}"
                    messages.append(TextMessage(text=notice))
                    edit_user_value(user_id, "notice_read", True)

        # 优先级3: Tips 消息（只在还有空间时添加）
        if len(messages) < 5 and random.random() < 0.10:
            tip_msg = get_random_tip(user_id)
            if tip_msg:
                messages.append(tip_msg)

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
            from modules.message_manager import system_error
            smart_reply(user_id, reply_token, system_error(user_id), configuration)
        except Exception as e:
            logger.error(f"Failed to reply user error message: {e}")

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
                    logger.error(f"Failed to notify admin {admin_user_id}: {e}")
        else:
            # 错误信息不长，直接发送 Flex Message
            for admin_user_id in admin_id:
                try:
                    smart_push(admin_user_id, flex_message, configuration)
                except Exception as e:
                    logger.error(f"Failed to notify admin {admin_user_id}: {e}")

    except Exception as e:
        # 通知系统本身出错，记录到日志
        logger.error(f"Error notification system failed: {e}", exc_info=True)
