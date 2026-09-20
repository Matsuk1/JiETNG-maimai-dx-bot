"""
LINE消息发送模块

提供smart_reply和smart_push功能,集成公告推送
"""

import logging
import functools
import traceback as _traceback
from contextlib import contextmanager
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    PushMessageRequest,
)
from modules.user_db import user_exists
from modules.notification_manager import record_notification
from modules.user_manager import (
    has_user_read_notice,
    record_notice_read
)
from modules.notice_manager import get_latest_published_notice
from modules.perm_request_handler import get_pending_perm_requests
from modules.perm_request_generator import generate_perm_request_message
from modules.messages.service import generate_notice_flex

logger = logging.getLogger(__name__)


def smart_reply(user_id: str, reply_token: str, messages, configuration: Configuration,
                addition: bool = True, source_type: str = "user"):
    """
    智能回复函数 - 自动附加好友申请、未读公告

    消息优先级：好友申请 > 公告
    仅当消息数量 < 5 时才添加附加消息

    Args:
        user_id: LINE用户ID
        reply_token: 回复令牌
        messages: 要发送的消息(单个或列表)
        configuration: LINE API配置对象
        addition: 是否自动附加权限申请/公告
        source_type: LINE source 类型，只有私聊(user)会附加权限申请/公告
    """
    if not isinstance(messages, list):
        messages = [messages]

    can_append_private_additions = addition and source_type == "user"

    # 只有私聊且消息数量小于5时，才添加附加消息
    if len(messages) < 5 and can_append_private_additions:
        # 优先级1: 好友申请与权限申请消息
        if user_exists(user_id):
            perm_requests = get_pending_perm_requests(user_id)
            if perm_requests and len(messages) < 5:
                perm_request_msg = generate_perm_request_message(perm_requests, user_id)
                if perm_request_msg:
                    messages.append(perm_request_msg)

        # 优先级2: 公告消息
        if len(messages) < 5 and user_id:
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

    # LINE displays quick replies from the last message in a reply batch.
    # Keep the actionable image after any automatically appended notices.
    for index in range(len(messages) - 1, -1, -1):
        if getattr(messages[index], "quick_reply", None):
            messages.append(messages.pop(index))
            break

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


def notify_on_error(title: str, context: dict = None, reraise: bool = True):
    """
    装饰器 / 上下文管理器：捕获异常后自动发送错误通知邮件。

    用法（装饰器）：
        @notify_on_error("Worker Error", reraise=False)
        def my_func(): ...

    用法（with 语句）：
        with notify_on_error("Webhook Error", context={"body": body[:200]}):
            handler.handle(body, signature)
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                _uid = None
                if args:
                    a0 = args[0]
                    if hasattr(a0, 'source'):
                        _uid = getattr(a0.source, 'user_id', None)
                    elif isinstance(a0, str) and a0.startswith('U'):
                        _uid = a0
                notify_admins_error(
                    error_title=title,
                    error_details=f"{type(e).__name__}: {str(e)}\n\n{_traceback.format_exc()}",
                    context=context or {"Function": func.__name__, "Error": type(e).__name__},
                    user_id=_uid
                )
                if reraise:
                    raise
        return wrapper

    # 同时支持 with 语句
    @contextmanager
    def ctx_manager():
        try:
            yield
        except Exception as e:
            notify_admins_error(
                error_title=title,
                error_details=f"{type(e).__name__}: {str(e)}\n\n{_traceback.format_exc()}",
                context=context or {"Error": type(e).__name__}
            )
            if reraise:
                raise

    # 让同一个对象既能当装饰器又能当上下文管理器
    decorator.__enter__ = ctx_manager().__enter__
    decorator.__exit__ = lambda *a: None  # 占位，实际由 ctx_manager 处理

    # 包一层，使 with 语法正确工作
    class _Notifier:
        def __call__(self, func):
            return decorator(func)

        def __enter__(self):
            self._ctx = ctx_manager()
            return self._ctx.__enter__()

        def __exit__(self, *args):
            return self._ctx.__exit__(*args)

    return _Notifier()


def notify_admins_error(error_title: str, error_details: str, context: dict, user_id: str = None, **_):
    """
    记录错误通知到 admin panel。

    Args:
        error_title: 错误标题
        error_details: 错误详情（含堆栈）
        context: 上下文信息
        user_id: 触发错误的用户ID
    """
    record_notification(error_title, error_details, user_id=user_id, context=context)
