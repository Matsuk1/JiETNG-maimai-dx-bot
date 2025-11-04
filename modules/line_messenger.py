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
from modules.friend_request_handler import get_pending_requests
from modules.friend_request import generate_friend_request_message
from modules.reply_text import tip_messages

logger = logging.getLogger(__name__)


def get_random_tip():
    """
    从 tip_messages 列表中随机返回一条 tips

    Returns:
        TextMessage: 随机选择的 tips 消息
    """
    if tip_messages:
        tip_text = random.choice(tip_messages)
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

    # 只有当消息数量小于5时，才添加附加消息
    if len(messages) < 5:
        # 优先级1: 好友申请消息
        if user_id in USERS:
            pending_requests = get_pending_requests(user_id)
            if pending_requests and len(messages) < 5:
                friend_request_msg = generate_friend_request_message(pending_requests)
                if friend_request_msg:
                    messages.append(friend_request_msg)

        # 优先级2: 公告消息
        if len(messages) < 5:
            if user_id not in USERS:
                notice_read = True
            else:
                notice_read = get_user_value(user_id, "notice_read")

            if not notice_read:
                notice_json = get_latest_notice()
                if notice_json:
                    notice = f"📢 お知らせ\n{divider}\n{notice_json['content']}\n{divider}\n{notice_json['date']}"
                    messages.append(TextMessage(text=notice))
                    edit_user_value(user_id, "notice_read", True)

        # 优先级3: Tips 消息（只在还有空间时添加）
        if len(messages) < 5:
            tip_msg = get_random_tip()
            if tip_msg:
                messages.append(tip_msg)

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
    max_length: int = 4000
):
    """
    通知管理员发生错误

    Args:
        error_title: 错误标题
        error_details: 错误详情
        context: 上下文信息
        admin_id: 管理员ID列表
        configuration: LINE API配置对象
        error_notification_enabled: 是否启用错误通知
        max_length: 错误消息最大长度
    """
    if not error_notification_enabled:
        return

    try:
        # 构建错误消息
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        message_parts = [
            f"🚨 System Error Alert",
            f"Time: {timestamp}",
            f"",
            f"Error: {error_title}",
            f"",
            f"Details:",
            error_details[:2000] if len(error_details) > 2000 else error_details
        ]

        # 添加上下文信息
        if context:
            message_parts.append("")
            message_parts.append("Context:")
            for key, value in context.items():
                message_parts.append(f"  {key}: {value}")

        full_message = "\n".join(message_parts)

        # 如果错误信息过长，使用文本文件
        if len(full_message) > max_length:
            # 截断消息
            short_message = "\n".join([
                f"🚨 System Error Alert",
                f"Time: {timestamp}",
                f"",
                f"Error: {error_title}",
                f"",
                f"⚠️ Error details too long, sending as text file..."
            ])

            # 创建详细错误文件内容
            file_content = "\n".join([
                f"System Error Report",
                f"=" * 50,
                f"Time: {timestamp}",
                f"",
                f"Error: {error_title}",
                f"",
                f"Full Details:",
                f"-" * 50,
                error_details,
                f"",
            ])

            if context:
                file_content += "\nContext Information:\n"
                file_content += "-" * 50 + "\n"
                for key, value in context.items():
                    file_content += f"{key}: {value}\n"

            # 保存到临时文件
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
                f.write(file_content)
                temp_file_path = f.name

            # 发送给所有管理员
            for admin_user_id in admin_id:
                try:
                    # 先发送简短消息
                    smart_push(admin_user_id, TextMessage(text=short_message), configuration)

                    # 分段发送详细信息
                    detail_chunks = [error_details[i:i+900] for i in range(0, len(error_details), 900)]
                    for i, chunk in enumerate(detail_chunks[:3]):  # 最多发送3段
                        chunk_msg = f"Details ({i+1}/{min(len(detail_chunks), 3)}):\n{chunk}"
                        smart_push(admin_user_id, TextMessage(text=chunk_msg), configuration)
                except Exception as e:
                    logger.error(f"Failed to notify admin {admin_user_id}: {e}")

            # 清理临时文件
            try:
                os.unlink(temp_file_path)
            except:
                pass
        else:
            # 错误信息不长，直接发送
            for admin_user_id in admin_id:
                try:
                    smart_push(admin_user_id, TextMessage(text=full_message), configuration)
                except Exception as e:
                    logger.error(f"Failed to notify admin {admin_user_id}: {e}")

    except Exception as e:
        # 通知系统本身出错，记录到日志
        logger.error(f"Error notification system failed: {e}", exc_info=True)
