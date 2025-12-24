"""
JiETNG Maimai DX LINE Bot 主程序
"""

import os
import sys
import random
import requests
import json
import re
import traceback
import numpy as np
import threading
import queue
import logging
import psutil
import platform
import socket
import secrets
import copy
import asyncio
import aiohttp
import urllib3
import time
import subprocess

from functools import wraps
from datetime import datetime

from PIL import Image, ImageDraw
from io import BytesIO

from pyzbar.pyzbar import decode

from flask import (
    Flask,
    request,
    abort,
    render_template,
    redirect,
    session,
    jsonify,
    send_file
)
from flask_wtf.csrf import CSRFProtect

from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    MessagingApiBlob,
    TextMessage,
    ImageMessage,
    TemplateMessage,
    ButtonsTemplate,
    MessageAction,
    PostbackAction,
    URIAction,
    FlexMessage,
    FlexContainer
)
from linebot.v3.webhooks import (
    MessageEvent,
    PostbackEvent,
    TextMessageContent,
    ImageMessageContent,
    LocationMessageContent
)

# Song and record generators
from modules.song_generator import song_info_generate, generate_version_list
from modules.record_generator import *

# User and data managers
from modules.user_manager import *
from modules.bindtoken_manager import generate_bind_token, get_user_id_from_token
from modules.notice_manager import *
from modules.notice_stats import *
from modules.tip_ad_manager import load_tip_ad_data, get_all_tip_ads, create_tip_ad, update_tip_ad, delete_tip_ad, get_tip_ad_by_id
from modules.maimai_manager import *
from modules.dxdata_manager import update_dxdata_with_comparison
from modules.record_manager import *
from modules.devtoken_manager import (
    verify_dev_token,
    load_dev_tokens,
    create_dev_token,
    save_dev_tokens,
    list_dev_tokens,
    revoke_dev_token,
    get_token_info
)

from modules.perm_request_handler import (
    send_perm_request,
    accept_perm_request,
    reject_perm_request,
    get_pending_perm_requests
)

# Config loader
from modules.config_loader import *

# Backup manager
from modules.backup_manager import create_backup

# UI and message modules
from modules.message_manager import *

# Image processing
from modules.image_uploader import smart_upload
from modules.image_manager import *

# System utilities
from modules.system_checker import run_system_check, clean_unbound_users
from modules.rate_limiter import check_rate_limit
from modules.line_messenger import smart_reply, smart_push, notify_admins_error
from modules.song_matcher import find_matching_songs, is_exact_song_match, normalize_text
from modules.memory_manager import memory_manager, cleanup_user_caches, cleanup_rate_limiter_tracking

# Module aliases for specific use cases
import modules.user_manager as user_manager_module
import modules.rate_limiter as rate_limiter_module

from modules.storelist_generator import generate_store_buttons

# ==================== 常量定义 ====================

# 分隔线
DIVIDER = "-" * 33

# 队列配置
MAX_QUEUE_SIZE = 15
MAX_CONCURRENT_IMAGE_TASKS = 8  # 图片生成并发数
WEB_MAX_CONCURRENT_TASKS = 5    # 网络任务并发数
TASK_TIMEOUT_SECONDS = 120

# 搜索结果限制
MAX_SEARCH_RESULTS = 10
# 是否启用错误通知
ERROR_NOTIFICATION_ENABLED = True

# ==================== 日志配置 ====================

# 配置日志
# 带颜色的日志格式化器
class ColoredFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': '\033[36m',    # 青色
        'INFO': '\033[32m',     # 绿色
        'WARNING': '\033[33m',  # 黄色
        'ERROR': '\033[31m',    # 红色
        'CRITICAL': '\033[35m', # 紫色
    }
    RESET = '\033[0m'
    GRAY = '\033[90m'

    def format(self, record):
        # 为级别名添加颜色
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.RESET}"

        # 时间戳使用灰色
        formatted = super().format(record)
        formatted = formatted.replace(record.asctime, f"{self.GRAY}{record.asctime}{self.RESET}", 1)

        return formatted

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 配置日志
file_handler = logging.FileHandler('jietng.log', encoding='utf-8')
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
))

console_handler = logging.StreamHandler()
console_handler.setFormatter(ColoredFormatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
))

logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, console_handler]
)

logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='assets', static_url_path='/static')
app.secret_key = secrets.token_hex(32)  # 用于session加密

# 启用 CSRF 保护
csrf = CSRFProtect(app)

# 配置安全响应头
@app.after_request
def set_security_headers(response):
    """设置安全响应头"""
    # 防止 XSS 攻击
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'

    # Content Security Policy
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "script-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self' data:;"
    )

    # Strict Transport Security (如果使用 HTTPS)
    # response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

    return response

# 记录服务启动时间和统计
SERVICE_START_TIME = datetime.now()

# 使用字典存储统计数据,避免global变量问题
STATS = {
    'tasks_processed': 0,
    'response_time': 0.0
}
stats_lock = threading.Lock()  # 保护统计数据的线程锁

# ==================== 任务队列系统 ====================

# 图片生成任务队列 (处理图片生成任务，如 b50 等)
image_queue = queue.Queue(maxsize=MAX_QUEUE_SIZE)
image_concurrency_limit = threading.Semaphore(MAX_CONCURRENT_IMAGE_TASKS)

# Web任务队列 (处理耗时的网络请求，如 maimai_update 等)
webtask_queue = queue.Queue(maxsize=MAX_QUEUE_SIZE)
webtask_concurrency_limit = threading.Semaphore(WEB_MAX_CONCURRENT_TASKS)


def run_task_with_limit(func: callable, args: tuple, sem: threading.Semaphore,
                        q: queue.Queue, task_id: str = None, is_web_task: bool = False) -> None:
    """
    在并发限制下运行任务

    Args:
        func: 要执行的函数
        args: 函数参数元组
        sem: 信号量,用于控制并发数
        q: 任务队列
        task_id: 任务 ID
        is_web_task: 是否是 web 任务
    """
    start_time = datetime.now()

    # 检查任务是否已被取消
    if task_id:
        with task_tracking_lock:
            if task_id in task_tracking['cancelled']:
                # 任务已取消，从取消列表中移除并从排队中移除
                task_tracking['cancelled'].discard(task_id)
                task_tracking['queued'] = [t for t in task_tracking['queued'] if t.get('id') != task_id]
                logger.info(f"[Task] ⚠ Cancelled: task_id={task_id}")
                q.task_done()
                return

    # 添加到运行中的任务
    if task_id:
        with task_tracking_lock:
            # 从排队中移除
            task_tracking['queued'] = [t for t in task_tracking['queued'] if t.get('id') != task_id]
            # 添加到运行中
            # 智能提取 user_id：尝试多种方式
            user_id_for_tracking = 'Unknown'
            if args:
                if hasattr(args[0], 'source'):  # Event 对象
                    user_id_for_tracking = args[0].source.user_id
                elif isinstance(args[0], str) and args[0].startswith('U'):  # 直接传入的 user_id 字符串
                    user_id_for_tracking = args[0]

            task_info = {
                'id': task_id,
                'function': func.__name__,
                'start_time': start_time.strftime('%Y-%m-%d %H:%M:%S'),
                'user_id': user_id_for_tracking
            }
            task_tracking['running'].append(task_info)

    with sem:
        task_done = threading.Event()

        def target():
            try:
                func(*args)
            except Exception as e:
                logger.error(f"[Task] ✗ Execution error: function={func.__name__}, error={e}", exc_info=True)

                # 尝试获取用户信息以便回复
                user_id = None
                reply_token = None
                if args:
                    if hasattr(args[0], 'source') and hasattr(args[0], 'reply_token'):
                        # Event 对象
                        user_id = args[0].source.user_id
                        reply_token = args[0].reply_token
                    elif isinstance(args[0], str) and args[0].startswith('U'):
                        # 直接传入的 user_id 字符串
                        user_id = args[0]
                        # reply_token 可能在 args[1]
                        if len(args) > 1 and isinstance(args[1], str):
                            reply_token = args[1]

                # 通知管理员并回复用户
                notify_admins_error(
                    error_title=f"Task Execution Failed: {func.__name__}",
                    error_details=f"{type(e).__name__}: {str(e)}\n\n{traceback.format_exc()}",
                    context={
                        "Task": func.__name__,
                        "Error Type": type(e).__name__,
                        "User ID": user_id or "Unknown"
                    },
                    admin_id=ADMIN_ID,
                    configuration=configuration,
                    error_notification_enabled=ERROR_NOTIFICATION_ENABLED,
                    user_id=user_id,
                    reply_token=reply_token
                )
            finally:
                task_done.set()

        thread = threading.Thread(target=target)
        thread.start()

        timer = threading.Timer(TASK_TIMEOUT_SECONDS, cancel_if_timeout, args=(task_done,))
        timer.start()

        thread.join()
        timer.cancel()

        # 任务完成后更新统计(在主流程中,不在子线程中)
        end_time = datetime.now()
        response_time = (end_time - start_time).total_seconds() * 1000

        # 从运行中的任务移除，并添加到已完成列表
        if task_id:
            with task_tracking_lock:
                # 找到运行中的任务信息
                task_info = None
                for t in task_tracking['running']:
                    if t.get('id') == task_id:
                        task_info = t.copy()
                        break

                # 从运行中移除
                task_tracking['running'] = [t for t in task_tracking['running'] if t.get('id') != task_id]

                # 添加到已完成列表
                if task_info:
                    task_info['end_time'] = end_time.strftime('%Y-%m-%d %H:%M:%S')
                    task_info['duration'] = f"{response_time/1000:.2f}s"

                    # 在列表开头插入（最新的在前面）
                    task_tracking['completed'].insert(0, task_info)

                    # 保持最多20个已完成任务
                    if len(task_tracking['completed']) > MAX_COMPLETED_TASKS:
                        task_tracking['completed'] = task_tracking['completed'][:MAX_COMPLETED_TASKS]

        with stats_lock:
            STATS['tasks_processed'] += 1
            STATS['response_time'] += response_time
            logger.info(f"[Task] ✓ Completed: function={func.__name__}, total={STATS['tasks_processed']}, avg_time={STATS['response_time']/STATS['tasks_processed']:.1f}ms")

        q.task_done()


def image_worker() -> None:
    """图片生成任务队列的工作线程"""
    while True:
        try:
            item = image_queue.get()
            if len(item) == 3:
                func, args, task_id = item
            else:
                func, args = item
                task_id = None
            run_task_with_limit(func, args, image_concurrency_limit, image_queue, task_id, False)
        except Exception as e:
            logger.error(f"[Worker] ✗ Image worker error: error={e}", exc_info=True)
            notify_admins_error(
                error_title="Image Task Worker Error",
                error_details=f"{type(e).__name__}: {str(e)}\n\n{traceback.format_exc()}",
                context={"Worker": "image_worker"},
                admin_id=ADMIN_ID,
                configuration=configuration,
                error_notification_enabled=ERROR_NOTIFICATION_ENABLED
            )
            image_queue.task_done()


def webtask_worker() -> None:
    """Web任务队列的工作线程"""
    while True:
        try:
            item = webtask_queue.get()
            if len(item) == 3:
                func, args, task_id = item
            else:
                func, args = item
                task_id = None
            run_task_with_limit(func, args, webtask_concurrency_limit, webtask_queue, task_id, True)
        except Exception as e:
            logger.error(f"[Worker] ✗ Web worker error: error={e}", exc_info=True)
            notify_admins_error(
                error_title="Web Task Worker Error",
                error_details=f"{type(e).__name__}: {str(e)}\n\n{traceback.format_exc()}",
                context={"Worker": "webtask_worker"},
                admin_id=ADMIN_ID,
                configuration=configuration,
                error_notification_enabled=ERROR_NOTIFICATION_ENABLED
            )
            webtask_queue.task_done()



def cancel_if_timeout(task_done: threading.Event) -> None:
    """
    检查任务是否超时

    Args:
        task_done: 任务完成事件
    """
    if not task_done.is_set():
        logger.warning(f"[Task] ⚠ Execution timeout: timeout={TASK_TIMEOUT_SECONDS}s")

configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# ==================== API 认证装饰器 ====================

def require_dev_token(f):
    """
    验证开发者 token 的装饰器

    使用方法:
    @app.route('/api/endpoint')
    @require_dev_token
    def endpoint():
        # token_info 会被添加到 request 对象中
        token_info = request.token_info
        return jsonify({"status": "success"})
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 从 Authorization header 获取 token
        auth_header = request.headers.get('Authorization')

        if not auth_header:
            return jsonify({
                "error": "No authorization header",
                "message": "Authorization header is required"
            }), 401

        # 检查 Bearer token 格式
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return jsonify({
                "error": "Invalid authorization header",
                "message": "Authorization header must be in format: Bearer <token>"
            }), 401

        token = parts[1]

        # 验证 token
        token_info = verify_dev_token(token)
        if not token_info:
            return jsonify({
                "error": "Invalid token",
                "message": "Token is invalid or has been revoked"
            }), 401

        # 将 token 信息添加到 request 对象中
        request.token_info = token_info

        return f(*args, **kwargs)

    return decorated_function


def require_user_permission(f):
    """
    验证 token 是否有权限访问指定用户的装饰器

    必须在 @require_dev_token 之后使用

    使用方法:
    @app.route('/api/endpoint/<user_id>')
    @csrf.exempt
    @require_dev_token
    @require_user_permission
    def endpoint(user_id):
        # 此时已验证 token 有权限访问 user_id
        return jsonify({"status": "success"})

    权限检查逻辑:
    1. 如果用户是通过该 token 创建的 (registered_via_token) - 允许访问
    2. 如果 token 的 allowed_users 列表包含该用户 - 允许访问
    3. 否则拒绝访问
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 获取 user_id 参数
        user_id = kwargs.get('user_id')
        if not user_id:
            return jsonify({
                "error": "Missing parameter",
                "message": "user_id is required"
            }), 400

        # 获取 token 信息（由 require_dev_token 装饰器提供）
        token_info = request.token_info
        token_id = token_info['token_id']

        # 使用辅助函数检查权限
        has_permission, error_response = check_user_permission(user_id, token_id)
        if not has_permission:
            return error_response

        return f(*args, **kwargs)

    return decorated_function


def require_owner_permission(f):
    """
    验证 token 是否为用户的所有者（创建者）的装饰器

    只允许创建该用户的 token 访问，不允许被授权的 token 访问
    用于敏感操作如：删除用户、管理权限等

    必须在 @require_dev_token 之后使用

    使用方法:
    @app.route('/api/endpoint/<user_id>')
    @csrf.exempt
    @require_dev_token
    @require_owner_permission
    def endpoint(user_id):
        # 此时已验证 token 是 user_id 的所有者（创建者）
        return jsonify({"status": "success"})

    权限检查逻辑:
    只检查用户是否通过该 token 创建 (registered_via_token)
    不检查 allowed_users 列表
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 获取 user_id 参数
        user_id = kwargs.get('user_id')
        if not user_id:
            return jsonify({
                "error": "Missing parameter",
                "message": "user_id is required"
            }), 400

        # 检查用户是否存在
        if user_id not in USERS:
            return jsonify({
                "error": "User not found",
                "message": f"User {user_id} does not exist"
            }), 404

        # 获取 token 信息（由 require_dev_token 装饰器提供）
        token_info = request.token_info
        token_id = token_info['token_id']

        # 只检查是否为所有者（创建者）
        if USERS[user_id].get('registered_via_token') != token_id:
            return jsonify({
                "error": "Forbidden",
                "message": "Only the owner token (creator) can perform this operation"
            }), 403

        return f(*args, **kwargs)

    return decorated_function


def check_user_permission(user_id, token_id):
    """
    检查 token 是否有权限访问指定用户的辅助函数

    Args:
        user_id: 用户ID
        token_id: Token ID

    Returns:
        tuple: (has_permission: bool, error_response: dict or None)
    """

    # 检查用户是否存在
    if user_id not in USERS:
        return False, jsonify({
            "error": "User not found",
            "message": f"User {user_id} does not exist"
        }), 404

    # 检查权限：方式1 - 用户是通过该 token 创建的
    if 'registered_via_token' in USERS[user_id] and USERS[user_id]['registered_via_token'] == token_id:
        return True, None

    # 检查权限：方式2 - token 的 allowed_users 列表包含该用户
    dev_tokens = load_dev_tokens()
    if token_id in dev_tokens:
        allowed_users = dev_tokens[token_id].get('allowed_users', [])
        if user_id in allowed_users:
            return True, None

    # 没有权限
    return False, jsonify({
        "error": "Permission denied",
        "message": f"Token does not have permission to access user {user_id}"
    }), 403

# ==================== Flask 路由 ====================

@app.route("/linebot/webhook", methods=['POST'])
@csrf.exempt  # LINE Webhook 使用签名验证，无需 CSRF token
def linebot_reply():
    """
    LINE Webhook 接收端点

    接收并处理来自LINE平台的webhook事件

    Returns:
        tuple: ('OK', 200) 表示成功接收
    """
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)
    logger.info("[Webhook] → Received request")

    try:
        json_data = json.loads(body)
        destination = json_data.get("destination")
        request.destination = destination
        handler.handle(body, signature)

    except json.JSONDecodeError as e:
        logger.error(f"[Webhook] ✗ JSON parse failed: error={e}")
        notify_admins_error(
            error_title="Webhook JSON Parse Failed",
            error_details=f"{type(e).__name__}: {str(e)}",
            context={"Body": body[:200]},
            admin_id=ADMIN_ID,
            configuration=configuration,
            error_notification_enabled=ERROR_NOTIFICATION_ENABLED
        )
        abort(400)

    except InvalidSignatureError as e:
        logger.error(f"[Webhook] ✗ LINE signature verification failed: error={e}")
        notify_admins_error(
            error_title="LINE Signature Verification Failed",
            error_details=f"{type(e).__name__}: {str(e)}",
            context={"Signature": signature[:50]},
            admin_id=ADMIN_ID,
            configuration=configuration,
            error_notification_enabled=ERROR_NOTIFICATION_ENABLED
        )
        abort(400)

    except Exception as e:
        logger.error(f"[Webhook] ✗ Handling error: error={e}", exc_info=True)
        notify_admins_error(
            error_title="Webhook Handling Error",
            error_details=f"{type(e).__name__}: {str(e)}\n\n{traceback.format_exc()}",
            context={"Event": "Webhook"},
            admin_id=ADMIN_ID,
            configuration=configuration,
            error_notification_enabled=ERROR_NOTIFICATION_ENABLED
        )
        abort(500)

    return 'OK', 200

@app.route("/linebot/adding", methods=["GET"])
@app.route("/linebot/add", methods=["GET"])
def line_add_page():
    """重定向到LINE添加好友页面"""
    return redirect(LINE_ADDING_URL)


@app.route("/linebot/sega_bind", methods=["GET", "POST"])
def website_segaid_bind():
    """
    SEGA账户绑定页面

    GET: 显示绑定表单
    POST: 处理绑定请求

    Query Args:
        token: 绑定Token (GET/POST)

    Form Data (POST):
        segaid: SEGA ID
        password: 密码
        ver: 服务器版本 (jp/intl)
    """
    token = request.args.get("token")
    if not token:
        # Token 未提供的错误消息（此时还没有 user_id，三语同时显示）
        token_missing_message = """トークンが提供されていません。<br />
Token not provided. <br />
未提供令牌。"""
        return render_template("error.html", message=token_missing_message, language="ja"), 400

    try:
        user_id = get_user_id_from_token(token)
        if user_id not in USERS or "language" not in USERS[user_id]:
            token_invalid_message = "トークンが無効です。<br />Invalid token. <br />令牌无效。"
            return render_template("error.html", message=token_invalid_message, language="ja"), 400
        
    except Exception as e:
        logger.error(f"[Auth] ✗ Token verification failed: error={e}")
        # Token 无效的错误消息（此时还没有 user_id，三语同时显示）
        token_invalid_message = "トークンが無効です。<br />Invalid token. <br />令牌无效。"
        return render_template("error.html", message=token_invalid_message, language="ja"), 400

    if request.method == "POST":
        segaid = request.form.get("segaid")
        password = request.form.get("password")
        user_version = request.form.get("ver", "jp")

        # 从用户数据中获取语言设置，默认为 ja
        user_language = USERS.get(user_id, {}).get("language", "ja")

        # 检查用户是否已经绑定账号
        user_data = USERS.get(user_id, {})
        has_account = all(key in user_data for key in ['sega_id', 'sega_pwd', 'version'])
        if has_account:
            error_messages = {
                "ja": "すでに SEGA アカウントが連携されています。再度連携する場合は、先に unbind コマンドで連携を解除してください。",
                "en": "A SEGA account is already linked. To rebind, please use the unbind command first to unlink your account.",
                "zh": "已绑定 SEGA 账号。如需重新绑定，请先使用 unbind 命令解除绑定。"
            }
            return render_template("error.html", message=error_messages.get(user_language, error_messages["ja"]), language=user_language), 400

        if not segaid or not password:
            missing_fields_messages = {
                "ja": "すべての項目を入力してください。",
                "en": "Please fill in all fields.",
                "zh": "请填写所有字段。"
            }
            return render_template("error.html", message=missing_fields_messages.get(user_language, missing_fields_messages["ja"]), language=user_language), 400

        result = asyncio.run(process_sega_credentials(user_id, segaid, password, user_version, user_language))
        if result == "MAINTENANCE":
            maintenance_messages = {
                "ja": "公式サイトがメンテナンス中です。しばらくしてからもう一度お試しください。",
                "en": "The official website is under maintenance. Please try again later.",
                "zh": "官方网站正在维护中。请稍后再试。"
            }
            return render_template("error.html", message=maintenance_messages.get(user_language, maintenance_messages["ja"]), language=user_language), 503
        elif result:
            return render_template("success.html", language=user_language)
        else:
            invalid_credentials_messages = {
                "ja": "SEGA ID または パスワード が正しくありません。もう一度確認してください。",
                "en": "Invalid SEGA ID or password. Please check and try again.",
                "zh": "SEGA ID 或密码不正确。请检查后重试。"
            }
            return render_template("error.html", message=invalid_credentials_messages.get(user_language, invalid_credentials_messages["ja"]), language=user_language), 500

    # GET 请求时，从用户数据中获取语言设置
    user_language = USERS.get(user_id, {}).get("language", "ja")
    return render_template("bind_form.html", user_language=user_language)


async def process_sega_credentials(user_id, segaid, password, ver="jp", language="ja"):
    base = (
        "https://maimaidx-eng.com/maimai-mobile"
        if ver == "intl"
        else "https://maimaidx.jp/maimai-mobile"
    )

    cookies = await login_to_maimai(segaid, password, ver=ver)
    if cookies == "MAINTENANCE":
        return "MAINTENANCE"
    if not cookies:
        logger.warning(f"[Auth] ⚠ Login failed for user_id={user_id}")
        return False

    # 验证登录是否成功
    connector = aiohttp.TCPConnector(ssl=False, limit=10)
    timeout = aiohttp.ClientTimeout(total=30, connect=10)
    async with aiohttp.ClientSession(cookies=cookies, connector=connector, timeout=timeout) as session:
        session_id = id(session)
        dom = await fetch_dom(session, f"{base}/home/", session_id, ver)

        if dom is None:
            return False

    user_bind_sega_id(user_id, segaid)
    user_bind_sega_pwd(user_id, password)
    user_set_version(user_id, ver)
    user_set_language(user_id, language)
    if "registered_via_token" not in USERS[user_id]:
        smart_push(user_id, bind_msg(user_id), configuration)
    return True



# ==================== 用户管理函数 ====================

def user_unbind(user_id):
    msg = unbind_msg(user_id)
    delete_user(user_id)
    return msg

def user_bind_sega_id(user_id, sega_id):
    if user_id not in USERS:
        add_user(user_id)
    edit_user_value(user_id, 'sega_id', sega_id)

def user_bind_sega_pwd(user_id, sega_pwd):
    if user_id not in USERS:
        add_user(user_id)
    edit_user_value(user_id, 'sega_pwd', sega_pwd)

def user_set_version(user_id, version):
    if user_id not in USERS:
        add_user(user_id)
    edit_user_value(user_id, 'version', version)

def user_set_language(user_id, language):
    if user_id not in USERS:
        add_user(user_id)
    edit_user_value(user_id, 'language', language)


# ==================== 异步任务处理函数 ====================

def async_maimai_update_task(event):
    """异步maimai更新任务 - 在webtask_queue中执行"""
    user_id = event.source.user_id
    reply_token = event.reply_token

    # 获取用户版本
    ver = "jp"
    if user_id in USERS and 'version' in USERS[user_id]:
        ver = USERS[user_id]['version']

    reply_msg = maimai_update(user_id, ver)
    if reply_token:
        smart_reply(user_id, reply_token, reply_msg, configuration, DIVIDER)

def async_generate_friend_b50_task(event):
    """异步生成好友B50任务 - 在webtask_queue中执行"""
    user_message = event.message.text.strip()
    user_id = event.source.user_id
    reply_token = event.reply_token
    friend_code = user_message.replace("friend-b50 ", "").strip()

    # 获取用户版本
    ver = "jp"
    if user_id in USERS and 'version' in USERS[user_id]:
        ver = USERS[user_id]['version']

    # 直接通过网页爬取获取好友信息
    reply_msg = generate_friend_b50(user_id, friend_code, ver)

    smart_reply(user_id, reply_token, reply_msg, configuration, DIVIDER)

def async_generate_image_task(event):
    """异步图片生成任务 - 在image_queue中执行"""
    handle_sync_text_command(event)

def async_admin_maimai_update_task(event):
    """管理员触发的maimai更新任务 - 在webtask_queue中执行"""
    user_id = event.source.user_id

    # 获取用户版本
    ver = "jp"
    if user_id in USERS and 'version' in USERS[user_id]:
        ver = USERS[user_id]['version']

    # 执行更新
    messages = maimai_update(user_id, ver)

    # 推送通知给管理员
    for admin_user_id in ADMIN_ID:
        try:
            smart_push(admin_user_id, TextMessage(
                text=f"✅ Admin triggered update completed\nUser: {user_id}\nStatus: Success"
            ), configuration)
        except Exception as e:
            logger.error(f"[Notification] ✗ Failed to notify admin: admin_id={admin_user_id}, error={e}")

# ==================== 主程序入口 ====================

def maimai_update(user_id, ver="jp"):
    # 记录开始时间
    start_time = time.time()

    messages = []
    func_status = {
        "User Info": True,
        "Best Records": True,
        "Recent Records": True,
        "Favorite Friends": 0
    }

    if user_id not in USERS:
        return segaid_error(user_id)

    elif 'sega_id' not in USERS[user_id] or 'sega_pwd' not in USERS[user_id]:
        return segaid_error(user_id)

    sega_id = USERS[user_id]['sega_id']
    sega_pwd = USERS[user_id]['sega_pwd']

    # 定义数据获取函数（在重试循环外定义一次）
    async def fetch_all_data(cookies):
        return await asyncio.gather(
            get_maimai_info(cookies, ver),
            get_maimai_records(cookies, ver),
            get_recent_records(cookies, ver),
            get_friends_list(cookies, ver)
        )

    user_info = maimai_records = recent_records = friends_list = None

    cookies = asyncio.run(login_to_maimai(sega_id, sega_pwd, ver))
    if cookies is None:
        logger.warning(f"[User] ⚠ Login failed: user_id={user_id}")
        return segaid_error(user_id)
    if cookies == "MAINTENANCE":
        return maintenance_error(user_id)

    # 使用异步函数并发获取所有数据
    user_info, maimai_records, recent_records, friends_list = asyncio.run(fetch_all_data(cookies))

    if (user_info == "MAINTENANCE" or
        maimai_records == "MAINTENANCE" or
        recent_records == "MAINTENANCE" or
        friends_list == "MAINTENANCE"):
        return maintenance_error(user_id)

    if not user_info or not maimai_records or not recent_records:
        logger.warning(f"[User] ⚠ Data fetch incomplete: user_id={user_id}, user_info={bool(user_info)}, records={bool(maimai_records)}, recent={bool(recent_records)}")

    error = False

    if user_info and user_info['rating'] != "ERROR":
        edit_user_value(user_id, "personal_info", user_info)
    else:
        func_status["User Info"] = False
        error = True

    if maimai_records:
        write_record(user_id, maimai_records)
    else:
        func_status["Best Records"] = False
        error = True

    if recent_records:
        write_record(user_id, recent_records, recent=True)
    else:
        func_status["Recent Records"] = False
        error = True

    if friends_list:
        edit_user_value(user_id, "mai_friends", friends_list)
        func_status["Favorite Friends"] = len(friends_list)

    details = DIVIDER
    for func, status in func_status.items():
        if not status and status != 0:
            details += f"\n「{func}」Error"

    # 计算耗时
    elapsed_time = time.time() - start_time

    if not error:
        # 记录更新时间
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        edit_user_value(user_id, "last_update", current_time)

        # 获取用户信息
        user_data = USERS[user_id]
        username = user_data.get('personal_info', {}).get('name', 'N/A')
        rating = user_data.get('personal_info', {}).get('rating', 'N/A')

        # 使用 flex message 显示更新结果
        messages.append(generate_update_result_flex(
            user_id=user_id,
            username=username,
            rating=rating,
            update_time=current_time,
            elapsed_time=elapsed_time,
            func_status=func_status,
            success=True
        ))
    else:
        # 获取用户信息
        user_data = USERS[user_id]
        username = user_data.get('personal_info', {}).get('name', 'N/A')
        rating = user_data.get('personal_info', {}).get('rating', 'N/A')
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 使用 flex message 显示错误结果
        messages.append(generate_update_result_flex(
            user_id=user_id,
            username=username,
            rating=rating,
            update_time=current_time,
            elapsed_time=elapsed_time,
            func_status=func_status,
            success=False
        ))

    return messages

def handle_rc_command(msg: str, user_id: str):
    """
    处理 RC 命令，验证输入并生成 Rating 对照表

    Args:
        msg: 用户输入的消息（如 "rc 13.2"）
        user_id: 用户ID

    Returns:
        FlexMessage 或 TextMessage（错误消息）
    """
    # 提取数字
    level_str = re.sub(r"^rc\b[ 　]*", "", msg, flags=re.IGNORECASE).strip()

    # 尝试转换为浮点数
    try:
        level = float(level_str)
    except ValueError:
        language = get_user_language(user_id)
        error_texts = {
            'ja': '無効な定数です。1.0～15.0の範囲で入力してください。',
            'en': 'Invalid constant. Please enter a value between 1.0 and 15.0.',
            'zh': '无效的定数。请输入 1.0~15.0 范围内的数值。'
        }
        return TextMessage(text=error_texts.get(language, error_texts['ja']))

    # 验证范围：1.0 到 15.0
    if level < 1.0 or level > 15.0:
        language = get_user_language(user_id)
        error_texts = {
            'ja': f'定数 {level} は範囲外です。1.0～15.0の範囲で入力してください。',
            'en': f'Constant {level} is out of range. Please enter a value between 1.0 and 15.0.',
            'zh': f'定数 {level} 超出范围。请输入 1.0~15.0 范围内的数值。'
        }
        return TextMessage(text=error_texts.get(language, error_texts['ja']))

    # 验证小数位数：最多一位
    if round(level, 1) != level:
        language = get_user_language(user_id)
        error_texts = {
            'ja': f'定数 {level} は無効です。小数点以下は1桁まで入力可能です（例：13.2）。',
            'en': f'Constant {level} is invalid. Only one decimal place is allowed (e.g., 13.2).',
            'zh': f'定数 {level} 无效。仅支持一位小数（例如：13.2）。'
        }
        return TextMessage(text=error_texts.get(language, error_texts['ja']))

    return get_rc(level, user_id)


def get_rc(level: float, user_id=None):
    """
    生成指定难度的Rating对照表 FlexMessage

    Args:
        level: 谱面定数 (如 14.5)
        user_id: 用户ID（用于多语言）

    Returns:
        FlexMessage: Rating对照表
    """
    rc_data = []
    last_ra = 0

    for score in np.arange(97, 100.5001, 0.0001):
        ra = get_single_ra(level, score)
        if ra != last_ra:
            rc_data.append((score, ra))
            last_ra = ra

    return generate_rc_flex(level, rc_data, user_id)

def random_song(user_id, key="", ver="jp"):
    read_dxdata(ver)
    length = len(SONGS)
    is_exit = False
    valid_songs = []
    result = []

    if key:
        level_values = parse_level_value(key)

    for song in SONGS:
        for sheet in song['sheets']:
            if sheet['regions']['jp']:
                if not key or sheet['internalLevelValue'] in level_values:
                    valid_songs.append(song)
                    break

    if not valid_songs:
        return song_error(user_id)

    song = random.choice(valid_songs)
    song_id = song.get('id')

    original_url, preview_url = smart_upload(song_info_generate(song))
    result.append(ImageMessage(original_content_url=original_url, preview_image_url=preview_url))
    result.append(generate_calc_button(song_id, user_id))
    return result

def search_song(user_id, acronym, ver="jp"):
    """
    搜索歌曲并返回歌曲信息图片

    Args:
        user_id: 用户ID
        acronym: 搜索关键词
        ver: 服务器版本 (jp/intl)

    Returns:
        搜索结果消息列表 或搜索结果flex message 或错误消息
    """
    read_dxdata(ver)

    # 使用优化的歌曲匹配函数
    matching_songs = find_matching_songs(acronym, SONGS, max_results=MAX_SEARCH_RESULTS, threshold=0.85)

    # 没有匹配结果
    if not matching_songs:
        return song_error(user_id)

    # 返回搜索结果列表
    if len(matching_songs) > 1:
        return generate_search_results_flex(user_id, matching_songs)

    # 单个结果：返回图片 + 按钮
    result = []
    for song in matching_songs:
        original_url, preview_url = smart_upload(song_info_generate(song))
        message = ImageMessage(original_content_url=original_url, preview_image_url=preview_url)
        result.append(message)
        song_id = song.get('id')
        result.append(generate_calc_button(song_id, user_id))

    return result

def search_song_by_id(user_id, song_id, ver="jp"):
    """
    通过歌曲ID搜索歌曲并返回歌曲信息图片

    Args:
        user_id: 用户ID
        song_id: 歌曲唯一ID (6个字符)
        ver: 服务器版本 (jp/intl)

    Returns:
        歌曲信息图片消息 或错误消息
    """
    read_dxdata(ver)

    # 在SONGS中查找匹配的歌曲
    matching_song = None
    for song in SONGS:
        if song.get('id') == song_id:
            matching_song = song
            break

    # 没有匹配结果
    if not matching_song:
        return song_error(user_id)

    # 返回图片 + 按钮
    original_url, preview_url = smart_upload(song_info_generate(matching_song))
    image_message = ImageMessage(original_content_url=original_url, preview_image_url=preview_url)
    return [image_message, generate_calc_button(song_id, user_id)]

def calc_by_id(user_id, song_id, ver="jp"):
    """
    通过歌曲ID搜索歌曲并返回歌曲calc结果

    Args:
        user_id: 用户ID
        song_id: 歌曲唯一ID (6个字符)
        ver: 服务器版本 (jp/intl)

    Returns:
        歌曲信息图片消息和calc结果列表 或错误消息
    """
    read_dxdata(ver)

    # 在SONGS中查找匹配的歌曲
    matching_song = None
    for song in SONGS:
        if song.get('id') == song_id:
            matching_song = song
            break

    # 没有匹配结果
    if not matching_song:
        return song_error(user_id)

    # 收集calc数据
    calc_data = []
    for sheet in matching_song.get('sheets', []):
        difficulty = sheet.get('difficulty', 'unknown')

        # 只处理master和remaster难度
        if difficulty not in ['master', 'remaster']:
            continue

        notes_counts = sheet.get('noteCounts', {})
        level = sheet.get('internalLevelValue', 0)
        notes = {
            'tap': notes_counts.get('tap', 0),
            'hold': notes_counts.get('hold', 0),
            'slide': notes_counts.get('slide', 0),
            'touch': notes_counts.get('touch', 0),
            'break': notes_counts.get('break', 0)
        }

        # 计算分数
        scores = get_note_score(notes)
        calc_data.append((notes, scores, difficulty, level))

    calc_carousel = generate_calc_carousel(calc_data)
    return calc_carousel

def get_friend_list(user_id):
    if user_id not in USERS:
        return segaid_error(user_id)

    elif 'mai_friends' not in USERS[user_id]:
        return friend_error(user_id)

    friend_list = copy.deepcopy(get_user_value(user_id, "mai_friends"))
    if not friend_list:
        friend_list = []

    friend_num = len(friend_list)
    
    if friend_num <= 10:
        group_size = 10
    elif 14 < friend_num <= 16:
        group_size = 8
    elif 17 <= friend_num <= 18:
        group_size = 9
    else:
        group_size = 7

    return generate_friend_buttons(user_id, get_friend_list_alt_text(user_id), friend_list, group_size)

def get_bot_status(user_id):
    """
    获取 Bot 状态信息

    Args:
        user_id: 用户ID（用于多语言）

    Returns:
        FlexMessage: Bot 状态信息
    """
    # 计算运行时长
    uptime = datetime.now() - SERVICE_START_TIME
    days = uptime.days
    hours, remainder = divmod(uptime.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str = f"{days}d {hours}h {minutes}m"

    # 获取系统信息
    cpu_percent = round(psutil.cpu_percent(interval=0.1), 1)

    memory = psutil.virtual_memory()
    memory_percent = round(memory.percent, 1)
    total_memory = round(memory.total / (1024**3), 1)  # GB
    memory_used_gb = round(memory.used / (1024**3), 1)  # GB

    # 线程安全地读取统计数据
    with stats_lock:
        total_tasks = STATS['tasks_processed']
        total_time = STATS['response_time']

    # 计算平均响应时间
    if total_tasks > 0:
        avg_response = f"{round(total_time / total_tasks, 1)} ms"
    else:
        avg_response = "N/A"

    return generate_bot_status_flex(
        uptime_str=uptime_str,
        cpu_percent=cpu_percent,
        memory_percent=memory_percent,
        memory_used_gb=memory_used_gb,
        total_memory=total_memory,
        avg_response_time=avg_response,
        user_id=user_id
    )

def get_song_record(user_id, acronym, ver="jp"):
    """
    查询用户在特定歌曲上的游玩记录

    Args:
        user_id: 用户ID
        acronym: 歌曲搜索关键词
        ver: 服务器版本 (jp/intl)

    Returns:
        包含用户成绩的歌曲信息图片消息列表 或搜索结果flex message 或错误消息
    """
    read_dxdata(ver)

    song_record = read_record(user_id)

    if not len(song_record):
        return record_error(user_id)

    # 使用优化的歌曲匹配函数
    matching_songs = find_matching_songs(acronym, SONGS, max_results=MAX_SEARCH_RESULTS, threshold=0.85)

    if not matching_songs:
        return song_error(user_id)

    # 过滤出有游玩记录的歌曲
    songs_with_records = []
    for song in matching_songs:
        has_record = False
        for rcd in song_record:
            if is_exact_song_match(rcd['cover_name'], song['cover_name']) and rcd['type'] == song['type']:
                has_record = True
                break
        if has_record:
            songs_with_records.append(song)

    # 没有找到任何有记录的歌曲
    if len(songs_with_records) == 0:
        return song_error(user_id)

    # 返回搜索结果列表
    if len(songs_with_records) > 1:
        return generate_search_record_results_flex(user_id, songs_with_records)

    # 生成图片消息列表
    result = []
    for song in songs_with_records:
        played_data = []

        # 使用优化的精确匹配函数
        for rcd in song_record:
            if is_exact_song_match(rcd['cover_name'], song['cover_name']) and rcd['type'] == song['type']:
                rcd['rank'] = ""
                played_data.append(rcd)

        original_url, preview_url = smart_upload(song_info_generate(song, played_data))
        message = ImageMessage(original_content_url=original_url, preview_image_url=preview_url)
        result.append(message)

    return result

def get_song_record_by_id(user_id, song_id, ver="jp"):
    """
    通过歌曲ID查询用户在特定歌曲上的游玩记录

    Args:
        user_id: 用户ID
        song_id: 歌曲唯一ID (6个字符)
        ver: 服务器版本 (jp/intl)

    Returns:
        包含用户成绩的歌曲信息图片消息 或错误消息
    """
    read_dxdata(ver)

    song_record = read_record(user_id)

    if not len(song_record):
        return record_error(user_id)

    # 在SONGS中查找匹配的歌曲
    matching_song = None
    for song in SONGS:
        if song.get('id') == song_id:
            matching_song = song
            break

    # 没有匹配结果
    if not matching_song:
        return song_error(user_id)

    # 查找用户的游玩记录
    played_data = []
    for rcd in song_record:
        if is_exact_song_match(rcd['cover_name'], matching_song['cover_name']) and rcd['type'] == matching_song['type']:
            rcd['rank'] = ""
            played_data.append(rcd)

    # 如果该歌曲没有游玩记录
    if not played_data:
        return song_error(user_id)

    # 生成歌曲信息图片
    original_url, preview_url = smart_upload(song_info_generate(matching_song, played_data))
    result = ImageMessage(original_content_url=original_url, preview_image_url=preview_url)

    return result

def generate_plate_rcd(user_id, title, ver="jp"):
    if not (len(title) == 2 or len(title) == 3):
        return plate_error(user_id)

    read_dxdata(ver)

    song_record = read_record(user_id)

    if not len(song_record):
        return record_error(user_id)

    if "personal_info" not in USERS[user_id]:
        return info_error(user_id)

    version_name = title[0]
    plate_type = title[1:].replace("极", "極")

    target_version = []
    target_icon = []
    target_type = ""

    if version_name in TEMP_VERSION["abbr"]:
        target_version.append(TEMP_VERSION["title"])

    for version in VERSIONS:
        if version_name in version['abbr']:
            target_version.append(version['version'])

    if not len(target_version):
        return version_error(user_id)

    if plate_type == "極":
        target_type = "combo"
        target_icon = ["fc", "fcp", "ap", "app"]

    elif plate_type == "将":
        target_type = "score"
        target_icon = ["sss", "sssp"]

    elif plate_type == "神":
        target_type = "combo"
        target_icon = ["ap", "app"]

    elif plate_type == "舞舞":
        target_type = "sync"
        target_icon = ["fdx", "fdxp"]

    else:
        return plate_error(user_id)

    version_rcd_data = list(filter(lambda x: x['version'] in target_version, song_record))
    if not version_rcd_data:
        return version_error(user_id)

    target_data = []
    target_num = {
        'basic': {'all': 0, 'clear': 0},
        'advanced': {'all': 0, 'clear': 0},
        'expert': {'all': 0, 'clear': 0},
        'master': {'all': 0, 'clear': 0}
    }

    # 优化：构建用户记录的哈希表，避免嵌套循环 O(n*m*p) -> O(n*m)
    # 使用多个key策略保持与 is_exact_song_match 的兼容性

    rcd_map = {}
    for rcd in version_rcd_data:
        name = rcd['name']
        difficulty = rcd['difficulty']
        type = rcd['type']

        # 策略1: 精确匹配
        key1 = (name, difficulty, type)
        rcd_map[key1] = rcd

        # 策略2: 标准化匹配 (处理全角半角、特殊符号等)
        normalized_name = normalize_text(name)
        key2 = (normalized_name, difficulty, type)
        rcd_map[key2] = rcd

    for song in SONGS:
        if song['version'] not in target_version or song['type'] == 'utage':
            continue

        for sheet in song['sheets']:
            if not sheet['regions']['jp'] or sheet["difficulty"] not in target_num:
                continue

            icon = "back"
            target_num[sheet['difficulty']]['all'] += 1

            # O(1) 哈希查找，尝试多种匹配策略
            song_title = song['title']
            difficulty = sheet['difficulty']
            song_type = song['type']

            # 尝试精确匹配
            key1 = (song_title, difficulty, song_type)
            if key1 in rcd_map:
                rcd = rcd_map[key1]
                icon = rcd[f'{target_type}_icon']
                if icon in target_icon:
                    target_num[difficulty]['clear'] += 1
            else:
                # 尝试标准化匹配
                normalized_title = normalize_text(song_title)
                key2 = (normalized_title, difficulty, song_type)
                if key2 in rcd_map:
                    rcd = rcd_map[key2]
                    icon = rcd[f'{target_type}_icon']
                    if icon in target_icon:
                        target_num[difficulty]['clear'] += 1

            if sheet['difficulty'] == "master":
                # 构建 complete_info：检查所有难度是否符合牌子条件
                complete_info = {}
                for diff in ["basic", "advanced", "expert", "master"]:
                    # 尝试查找该难度的记录
                    key_check = (song_title, diff, song_type)
                    key_check_normalized = (normalize_text(song_title), diff, song_type)

                    meets_condition = False
                    if key_check in rcd_map:
                        rcd = rcd_map[key_check]
                        diff_icon = rcd[f'{target_type}_icon']
                        meets_condition = diff_icon in target_icon
                    elif key_check_normalized in rcd_map:
                        rcd = rcd_map[key_check_normalized]
                        diff_icon = rcd[f'{target_type}_icon']
                        meets_condition = diff_icon in target_icon

                    complete_info[diff] = meets_condition

                target_data.append({
                    "img": generate_cover(song['cover_url'], song_type, icon, target_type, cover_name=song.get('cover_name'), complete_info=complete_info),
                    "level": sheet['level']
                })

    img = generate_plate_image(target_data, title, headers = target_num)

    # 获取用户信息并创建用户信息图片
    user_info = USERS[user_id]['personal_info']
    img = compose_images([create_user_info_img(user_info), img])

    original_url, preview_url = smart_upload(img)
    message = ImageMessage(original_content_url=original_url, preview_image_url=preview_url)

    return message

def generate_internallevel_songs(user_id, level, ver="jp"):
    """
    生成指定定数范围的歌曲列表图片（现场生成）

    参数:
        level: 难度等级（如 "13", "13+", "14", "14+"）
        ver: 服务器版本（"jp" 或 "intl"）
    """

    # 检查等级是否支持（只支持12及以上）
    supported_levels = ["12", "12+", "13", "13+", "14", "14+", "15"]
    if level not in supported_levels:
        return level_not_supported(user_id)

    try:
        logger.info(f"[LevelList] → Generating level list: user_id={user_id}, level={level}, server={ver.upper()}")

        # 读取数据
        read_dxdata(ver)

        # 收集符合条件的歌曲信息
        song_data_list = []
        region_key = ver

        for song in SONGS:
            if song['type'] == 'utage':
                continue

            for sheet in song['sheets']:
                if not sheet['regions'].get(region_key, False):
                    continue

                # 14+ 包含 14+ 和 15 级别
                if level == "14+":
                    if sheet['level'] not in ["14+", "15"]:
                        continue
                else:
                    if sheet['level'] != level:
                        continue

                song_data_list.append({
                    "cover_url": song['cover_url'],
                    "cover_name": song.get('cover_name'),
                    "type": song['type'],
                    "internal_level": sheet['internalLevelValue']
                })

        if not song_data_list:
            logger.warning(f"[LevelList] ⚠ No songs found: level={level}, server={ver.upper()}")
            return system_error(user_id)

        # 生成封面图片（使用已下载的图片）
        target_data = []
        for song_data in song_data_list:
            cover_url = song_data['cover_url']
            cover_img = generate_cover(cover_url, song_data['type'], size=135, cover_name=song_data.get('cover_name'))
            target_data.append({
                "img": cover_img,
                "internal_level": song_data['internal_level']
            })

        if not target_data:
            logger.warning(f"[LevelList] ⚠ Failed: level={level}, server={ver.upper()}")
            return system_error(user_id)

        # 生成图片
        level_img = generate_internallevel_image(target_data, level)

        # 用compose函数包装
        final_img = compose_images([level_img])

        # 上传图片
        original_url, preview_url = smart_upload(final_img)

        return ImageMessage(original_content_url=original_url, preview_image_url=preview_url)

    except Exception as e:
        logger.error(f"[LevelList] ✗ Generation failed: user_id={user_id}, level={level}, error={e}", exc_info=True)
        return system_error(user_id)

def create_user_info_img(user_info, scale=1.7):
    """
    创建用户信息图片

    Args:
        user_info: 用户个人信息字典（包含 name, rating, icon_url 等）
        scale: 图片缩放比例

    Returns:
        PIL.Image: 用户信息图片
    """

    img_width = 802
    img_height = 128
    info_img = Image.new("RGBA", (img_width, img_height), (255, 255, 255))
    draw = ImageDraw.Draw(info_img)

    def paste_image(key, position, size):
        nonlocal user_info
        if key in user_info and user_info[key]:
            try:
                url = user_info[key]

                # 默认不带 headers
                headers = None

                if url.startswith("https://maimaidx-eng.com"):
                    headers = {
                        "Referer": "https://lng-tgk-aime-gw.am-all.net/common_auth/login?site_id=maimaidxex&redirect_url=https://maimaidx-eng.com/maimai-mobile/&back_url=https://maimai.sega.com/",
                        "User-Agent": (
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/127.0.0.0 Safari/537.36"
                        ),
                        "Host": "maimaidx-eng.com",
                    }

                response = requests.get(url, headers=headers, verify=False)
                response.raise_for_status()

                img = Image.open(BytesIO(response.content))
                if img.mode != "RGBA":
                    img = img.convert("RGBA")
                img_resized = img.resize(size)
                info_img.paste(img_resized, position, img_resized)
                return True

            except Exception as e:
                logger.error(f"[Image] ✗ Failed to load image: url={user_info[key]}, error={e}")
                return None
        return None

    paste_image("nameplate_url", (0, 0), (802, 128))

    paste_image("icon_url", (15, 13), (100, 100))

    paste_image("rating_block_url", (129, 13), (131, 34))

    # 使用等宽方式绘制 rating 数字
    rating_text = user_info['rating'].rjust(5)
    char_width = 13  # 每个字符的固定宽度
    start_x = 188
    for i, char in enumerate(rating_text):
        draw.text((start_x + i * char_width, 17), char, fill=(255, 255, 255), font=font_stadium)

    # 绘制带灰色边框的圆角矩形
    draw.rounded_rectangle([129, 51, 129 + 266, 51 + 33], radius=10, fill=(255, 255, 255), outline=(180, 180, 180), width=2)
    draw.text((138, 54), user_info['name'], fill=(0, 0, 0), font=font_stadium)

    paste_image("class_rank_url", (296, 9), (70, 40))
    paste_image("cource_rank_url", (322, 54), (69, 28))
    paste_image("trophy_url", (129, 92), (266, 21))

    trophy_content = truncate_text(draw, user_info['trophy_content'], font_small, 253)
    bbox = draw.textbbox((0, 0), trophy_content, font=font_small)
    text_width = bbox[2] - bbox[0]
    rect_width = 266
    center_x = 129 + (rect_width - text_width) // 2
    draw.text((center_x, 90), trophy_content, fill=(0, 0, 0), font=font_small)

    info_img = info_img.resize((int(img_width * scale), int(img_height * scale)), Image.Resampling.LANCZOS)
    return info_img

def select_records(song_record, type, command, ver):
    if not command == "":
        cmds = re.findall(r"-(\w+)\s+([^ -][^-]*)", command)
        for cmd, cmd_num in cmds:
            if cmd == "lv":
                parts = cmd_num.split()
                if len(parts) == 1:
                    lv_start = float(parts[0])
                    song_record = list(filter(lambda x: x['internalLevelValue'] >= lv_start, song_record))
                else:
                    lv_start, lv_stop = map(float, parts[:2])
                    song_record = list(filter(lambda x: lv_start <= x['internalLevelValue'] <= lv_stop, song_record))
            elif cmd == "ra":
                parts = cmd_num.split()
                if len(parts) == 1:
                    ra_start = int(parts[0])
                    song_record = list(filter(lambda x: x['ra'] >= ra_start, song_record))
                else:
                    ra_start, ra_stop = map(int, parts[:2])
                    song_record = list(filter(lambda x: ra_start <= x['ra'] <= ra_stop, song_record))
            elif cmd == "dx":
                parts = cmd_num.split()
                if len(parts) == 1:
                    dx_score = int(re.sub(r"\D", "", parts[0]))
                    song_record = list(filter(lambda x: eval(x['dx_score'].replace(",", "")) * 100 >= dx_score, song_record))
                else:
                    dx_start = int(re.sub(r"\D", "", parts[0]))
                    dx_stop = int(re.sub(r"\D", "", parts[1]))
                    song_record = list(filter(lambda x: dx_start <= eval(x['dx_score'].replace(",", "")) * 100 <= dx_stop, song_record))
            elif cmd == "scr":
                parts = cmd_num.split()
                if len(parts) == 1:
                    score = float(re.sub(r"[^0-9.]", "", parts[0]))
                    song_record = list(filter(lambda x: eval(x['score'].replace("%", "")) >= score, song_record))
                else:
                    scr_start = float(re.sub(r"[^0-9.]", "", parts[0]))
                    scr_stop = float(re.sub(r"[^0-9.]", "", parts[1]))
                    song_record = list(filter(lambda x: scr_start <= eval(x['score'].replace("%", "")) <= scr_stop, song_record))
            elif cmd == "ver":
                # 处理版本筛选：-ver [version1] [version2] ...
                raw_versions = cmd_num.split()
                versions = []
                for v in raw_versions:
                    if v.strip():
                        # 将 + 替换为 " PLUS"
                        processed = v.strip().replace("+", " PLUS").lower().replace("dx", "maimaiでらっくす").replace("deluxe", "maimaiでらっくす")
                        versions.append(processed)
                # 筛选歌曲版本在指定列表中的记录（忽略大小写）
                song_record = list(filter(lambda x: (x.get('version') or '').lower() in versions, song_record))

    up_songs = down_songs = []

    up_songs_data = list(filter(lambda x: x['new_song'] == False, song_record))
    down_songs_data = list(filter(lambda x: x['new_song'] == True, song_record))

    if type == "best50":
        up_songs = sorted(up_songs_data, key=lambda x: -x["ra"])[:35]
        down_songs = sorted(down_songs_data, key=lambda x: -x["ra"])[:15]

    elif type == "best100":
        up_songs = sorted(up_songs_data, key=lambda x: -x["ra"])[:70]
        down_songs = sorted(down_songs_data, key=lambda x: -x["ra"])[:30]

    elif type == "best35":
        up_songs = sorted(up_songs_data, key=lambda x: -x["ra"])[:35]

    elif type == "best15":
        down_songs = sorted(down_songs_data, key=lambda x: -x["ra"])[:15]

    elif type == "allb50":
        up_songs = sorted(song_record, key=lambda x: -x["ra"])[:50]

    elif type == "allb100":
        up_songs = sorted(song_record, key=lambda x: -x["ra"])[:100]

    elif type == "allb200":
        up_songs = sorted(song_record, key=lambda x: -x["ra"])[:200]

    elif type == "allb35":
        up_songs = sorted(song_record, key=lambda x: -x["ra"])[:35]

    elif type == "apb50":
        up_songs_data = [x for x in up_songs_data if x.get("combo_icon") in ("ap", "app")]
        up_songs = sorted(up_songs_data, key=lambda x: x.get("ra", 0), reverse=True)[:35]

        down_songs_data = [x for x in down_songs_data if x.get("combo_icon") in ("ap", "app")]
        down_songs = sorted(down_songs_data, key=lambda x: x.get("ra", 0), reverse=True)[:15]

    elif type == "fdxb50":
        up_songs_data = [x for x in up_songs_data if x.get("sync_icon") in ("fdx", "fdxp")]
        up_songs = sorted(up_songs_data, key=lambda x: x.get("ra", 0), reverse=True)[:35]

        down_songs_data = [x for x in down_songs_data if x.get("sync_icon") in ("fdx", "fdxp")]
        down_songs = sorted(down_songs_data, key=lambda x: x.get("ra", 0), reverse=True)[:15]

    elif type == "UNKNOWN":
        up_songs = list(filter(lambda x: x['version'] == "UNKNOWN", song_record))

    elif type == "rct50":
        up_songs = song_record

    elif type == "idealb50":
        for rcd in up_songs_data:
            ideal_score, score_icon = get_ideal_score(float(rcd['score'][:-1]))
            rcd['score'] = f"{ideal_score:.4f}%"
            if score_icon:
                rcd['score_icon'] = score_icon
            if ideal_score == 101:
                rcd['combo_icon'] = "app"
            rcd['ra'] = get_single_ra(rcd['internalLevelValue'], ideal_score, (ideal_score == 101 and ver == "jp"))

        for rcd in down_songs_data:
            ideal_score, score_icon = get_ideal_score(float(rcd['score'][:-1]))
            rcd['score'] = f"{ideal_score:.4f}%"
            if score_icon:
                rcd['score_icon'] = score_icon
            if ideal_score == 101:
                rcd['combo_icon'] = "app"
            rcd['ra'] = get_single_ra(rcd['internalLevelValue'], ideal_score, (ideal_score == 101 and ver == "jp"))

        up_songs = sorted(up_songs_data, key=lambda x: -x["ra"])[:35]
        down_songs = sorted(down_songs_data, key=lambda x: -x["ra"])[:15]

    return up_songs, down_songs;

def generate_records(user_id, type="best50", command="", ver="jp"):
    if user_id not in USERS:
        return segaid_error(user_id)

    if "personal_info" not in USERS[user_id]:
        return info_error(user_id)

    recent = (type == "rct50")
    song_record = read_record(user_id, recent=recent)
    if not len(song_record):
        return record_error(user_id)

    up_songs, down_songs = select_records(song_record, type, command, ver)
    if not up_songs and not down_songs:
        return picture_error(user_id)

    img = generate_records_picture(up_songs, down_songs, type.upper())

    # 获取用户信息并创建用户信息图片
    user_info = USERS[user_id]['personal_info']
    img = compose_images([create_user_info_img(user_info), img])

    original_url, preview_url = smart_upload(img)
    message = ImageMessage(original_content_url=original_url, preview_image_url=preview_url)
    return message

def generate_friend_b50(user_id, friend_code, ver="jp"):
    if user_id not in USERS:
        return segaid_error(user_id)

    elif 'sega_id' not in USERS[user_id] or 'sega_pwd' not in USERS[user_id]:
        return segaid_error(user_id)

    sega_id = USERS[user_id]['sega_id']
    sega_pwd = USERS[user_id]['sega_pwd']

    # 使用异步登录和获取好友成绩
    async def fetch_friend_data():
        cookies = await login_to_maimai(sega_id, sega_pwd, ver)
        if cookies is None or cookies == "MAINTENANCE":
            return cookies, None, None
        tasks = [
            get_friend_info(cookies, friend_code, ver),
            get_friend_records(cookies, friend_code, ver)
        ]
        friend_info, friend_records = await asyncio.gather(*tasks)
        return None, friend_info, friend_records

    error, friend_info, friend_records = asyncio.run(fetch_friend_data())

    if error == "MAINTENANCE":
        return maintenance_error(user_id)
    if error is None and friend_records is None:
        return segaid_error(user_id)

    # 检查 friend_info 是否包含维护错误
    if isinstance(friend_info, dict) and friend_info.get("error") == "MAINTENANCE":
        return maintenance_error(user_id)

    # 检查 friend_records 是否为维护模式字符串
    if friend_records == "MAINTENANCE":
        return maintenance_error(user_id)

    if not friend_records:
        return friend_rcd_error(user_id)

    friend_records = get_detailed_info(friend_records, ver)

    up_songs, down_songs = select_records(friend_records, "best50", "", ver)

    user_info_img = create_user_info_img(friend_info)
    rcd_img = generate_records_picture(up_songs, down_songs, "BEST50")
    img = compose_images([user_info_img, rcd_img])
    original_url, preview_url = smart_upload(img)

    message = ImageMessage(original_content_url=original_url, preview_image_url=preview_url)
    return message

def generate_level_records(user_id, level, ver="jp", page=1):
    if "personal_info" not in USERS[user_id]:
        return info_error(user_id)

    song_record = read_record(user_id)

    if not len(song_record):
        return record_error(user_id)

    level_value = parse_level_value(level)

    up_songs_data = list(filter(lambda x: x['new_song'] == False, song_record))
    down_songs_data = list(filter(lambda x: x['new_song'] == True, song_record))

    up_level_list_data = list(filter(lambda x: x['internalLevelValue'] in level_value, up_songs_data))
    down_level_list_data = list(filter(lambda x: x['internalLevelValue'] in level_value, down_songs_data))

    up_level_list = sorted(up_level_list_data, key=lambda x: -x["ra"])
    down_level_list = sorted(down_level_list_data, key=lambda x: -x["ra"])

    page_size_up = 35
    page_size_down = 15

    start_up = (page - 1) * page_size_up
    end_up = start_up + page_size_up

    start_down = (page - 1) * page_size_down
    end_down = start_down + page_size_down

    up_level_list = up_level_list[start_up:end_up]
    down_level_list = down_level_list[start_down:end_down]

    if not up_level_list and not down_level_list:
        return level_record_not_found(level, page, user_id)

    title = f"Lv{level} #{page}"

    img = generate_records_picture(up_level_list, down_level_list, title)

    # 获取用户信息并创建用户信息图片
    user_info = USERS[user_id]['personal_info']
    img = compose_images([create_user_info_img(user_info), img])

    original_url, preview_url = smart_upload(img)
    message = [
        ImageMessage(original_content_url=original_url, preview_image_url=preview_url),
        level_record_page_hint(page, user_id) if page == 1 else None
    ]
    message = [m for m in message if m]
    return message

def generate_version_songs(user_id, version_title, ver="jp"):
    read_dxdata(ver)

    target_version = []
    target_icon = []
    target_type = ""

    version_title = version_title.lower().replace("dx", "maimaiでらっくす").replace("deluxe", "maimaiでらっくす")

    for version in VERSIONS:
        if version_title == version['version'].lower():
            target_version.append(version['version'])

    if not len(target_version):
        return version_error(user_id)

    version_img = None
    version_img_path = os.path.join(VERSIONS_DIR, f"{version_title.replace(' ', '_')}.png")
    try:
        version_img = Image.open(version_img_path)
        version_img = resize_by_width(version_img, 1340)
    except Exception as e:
        logger.error(f"[VersionImage] ✗ Failed to load image: file={version_img_path}, error={e}")

    songs_data = list(filter(lambda x: x['version'] in target_version and x['type'] not in ['utage'], SONGS))
    version_list_img = generate_version_list(songs_data)

    if version_img is None:
        img = compose_images([version_list_img])
    else:
        img = compose_images([version_img, version_list_img], border_width=0)

    original_url, preview_url = smart_upload(img)
    message = ImageMessage(original_content_url=original_url, preview_image_url=preview_url)
    return message

# ==================== 消息处理 ====================

# Web任务路由规则 (需要网络请求的耗时任务)
WEB_TASK_ROUTES = {
    # 精确匹配规则
    'exact': {
        "マイマイアップデート": async_maimai_update_task,
        "maimai update": async_maimai_update_task,
        "レコードアップデート": async_maimai_update_task,
        "record update": async_maimai_update_task,
        "update": async_maimai_update_task,
        "アップデート": async_maimai_update_task
    },
    # 前缀匹配规则
    'prefix': {
        "friend-b50 ": async_generate_friend_b50_task,
        "friend b50 ": async_generate_friend_b50_task,
        "フレンドb50 ": async_generate_friend_b50_task,
    }
}

def route_to_web_queue(event):
    """
    路由消息到Web任务队列

    Args:
        event: LINE消息事件

    Returns:
        bool: True表示已路由到web队列, False表示不是web任务
    """
    user_message = event.message.text.strip()
    user_id = event.source.user_id

    # 检查精确匹配的web任务
    if user_message in WEB_TASK_ROUTES['exact']:
        task_func = WEB_TASK_ROUTES['exact'][user_message]

        # 频率限制检查
        if check_rate_limit(user_id, task_func.__name__):
            smart_reply(user_id, event.reply_token, rate_limit_msg(user_id), configuration, DIVIDER)
            return True

        try:
            # 生成任务ID
            task_id = f"user_{user_id}_{datetime.now().timestamp()}"

            # 获取用户昵称
            nickname = get_user_nickname_wrapper(user_id, use_cache=True)

            # 添加到任务追踪
            with task_tracking_lock:
                task_tracking['queued'].append({
                    'id': task_id,
                    'function': task_func.__name__,
                    'queue_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'user_id': user_id,
                    'nickname': nickname
                })

            webtask_queue.put_nowait((task_func, (event,), task_id))
            return True
        except queue.Full:
            smart_reply(user_id, event.reply_token, access_error(user_id), configuration, DIVIDER)
            return True

    # 检查前缀匹配的web任务
    for prefix, task_func in WEB_TASK_ROUTES['prefix'].items():
        if user_message.startswith(prefix):
            # 频率限制检查
            if check_rate_limit(user_id, task_func.__name__):
                smart_reply(user_id, event.reply_token, rate_limit_msg(user_id), configuration, DIVIDER)
                return True

            try:
                # 生成任务ID
                task_id = f"user_{user_id}_{datetime.now().timestamp()}"

                # 获取用户昵称
                nickname = get_user_nickname_wrapper(user_id, use_cache=True)

                # 添加到任务追踪
                with task_tracking_lock:
                    task_tracking['queued'].append({
                        'id': task_id,
                        'function': task_func.__name__,
                        'queue_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'user_id': user_id,
                        'nickname': nickname
                    })

                webtask_queue.put_nowait((task_func, (event,), task_id))
                return True
            except queue.Full:
                smart_reply(user_id, event.reply_token, access_error(user_id), configuration, DIVIDER)
                return True

    # 不是web任务,返回False
    return False

# 图片生成任务路由规则
IMAGE_TASK_ROUTES = {
    # 精确匹配规则 - 这些命令会生成图片
    'exact': {},
    # 前缀匹配规则
    'prefix': [],
    # 后缀匹配规则
    'suffix': [
        ("ってどんな曲", "info", "song-info"),
        ("の達成状況", "の達成情報", "の達成表", "achievement-list", "achievement"),
        ("のレコード", "song-record", "record"),
        ("のバージョンリスト", "version-list", "version"),
        ("の定数リスト", "のレベルリスト", "level-list")
    ],
    # B系列命令 (生成图片)
    'b_commands': {
        "b50", "best50", "best 50", "ベスト50",
        "b100", "best100", "best 100", "ベスト100",
        "b35", "best35", "best 35", "ベスト35",
        "b15", "best15", "best 15", "ベスト15",
        "ab35", "allb35", "all best 35", "オールベスト35",
        "ab50", "allb50", "all best 50", "オールベスト50",
        "ab100", "allb100", "all best 100", "オールベスト100",
        "apb50", "ap50", "all perfect 50", "オールパーフェクト50",
        "fdxb50", "fdx50", "Full DX 50", "フールでらっくす50",
        "rct50", "r50", "recent50", "recent 50",
        "idealb50", "idlb50", "ideal best 50", "理想的ベスト50",
        "unknown", "unknown songs", "unknown data", "未発見"
    }
}

def route_to_image_queue(event):
    """
    路由消息到图片生成任务队列

    Args:
        event: LINE消息事件

    Returns:
        bool: True表示已路由到image队列, False表示不是图片生成任务
    """
    user_message = event.message.text.strip()
    user_id = event.source.user_id

    # 检查精确匹配的图片生成任务
    if user_message in IMAGE_TASK_ROUTES['exact']:
        # 频率限制检查 - 使用消息类型作为任务类型
        if check_rate_limit(user_id, f"image:{user_message}"):
            smart_reply(user_id, event.reply_token, rate_limit_msg(user_id), configuration, DIVIDER)
            return True

        try:
            task_id = f"image_{user_id}_{datetime.now().timestamp()}"
            nickname = get_user_nickname_wrapper(user_id, use_cache=True)

            with task_tracking_lock:
                task_tracking['queued'].append({
                    'id': task_id,
                    'function': 'async_generate_image_task',
                    'queue_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'user_id': user_id,
                    'nickname': nickname
                })

            image_queue.put_nowait((async_generate_image_task, (event,), task_id))
            return True
        except queue.Full:
            smart_reply(user_id, event.reply_token, access_error(user_id), configuration, DIVIDER)
            return True

    # 检查后缀匹配的图片生成任务
    for suffixes in IMAGE_TASK_ROUTES['suffix']:
        for suffix in suffixes:
            if user_message.endswith(suffix):
                try:
                    task_id = f"image_{user_id}_{datetime.now().timestamp()}"
                    nickname = get_user_nickname_wrapper(user_id, use_cache=True)

                    with task_tracking_lock:
                        task_tracking['queued'].append({
                            'id': task_id,
                            'function': 'async_generate_image_task',
                            'queue_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'user_id': user_id,
                            'nickname': nickname
                        })

                    image_queue.put_nowait((async_generate_image_task, (event,), task_id))
                    return True
                except queue.Full:
                    smart_reply(user_id, event.reply_token, access_error(user_id), configuration, DIVIDER)
                    return True

    # 检查レコードリスト (带数字的)
    if re.match(r".+(のレコードリスト|record-list)[ 　]*\d*$", user_message):
        try:
            task_id = f"image_{user_id}_{datetime.now().timestamp()}"
            nickname = get_user_nickname_wrapper(user_id, use_cache=True)

            with task_tracking_lock:
                task_tracking['queued'].append({
                    'id': task_id,
                    'function': 'async_generate_image_task',
                    'queue_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'user_id': user_id,
                    'nickname': nickname
                })

            image_queue.put_nowait((async_generate_image_task, (event,), task_id))
            return True
        except queue.Full:
            smart_reply(user_id, event.reply_token, access_error(user_id), configuration, DIVIDER)
            return True

    # 检查 B 系列命令
    first_word = re.split(r"[ \n]", user_message.lower(), 1)[0]
    if first_word in IMAGE_TASK_ROUTES['b_commands']:
        # 频率限制检查 - B系列命令使用统一的限制
        if check_rate_limit(user_id, "image:b_series"):
            smart_reply(user_id, event.reply_token, rate_limit_msg(user_id), configuration, DIVIDER)
            return True

        try:
            task_id = f"image_{user_id}_{datetime.now().timestamp()}"
            nickname = get_user_nickname_wrapper(user_id, use_cache=True)

            with task_tracking_lock:
                task_tracking['queued'].append({
                    'id': task_id,
                    'function': 'async_generate_image_task',
                    'queue_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'user_id': user_id,
                    'nickname': nickname
                })

            image_queue.put_nowait((async_generate_image_task, (event,), task_id))
            return True
        except queue.Full:
            smart_reply(user_id, event.reply_token, access_error(user_id), configuration, DIVIDER)
            return True

    # 检查 ランダム曲 / random-song
    if user_message.startswith(("ランダム曲", "ランダム", "random-song", "random")):
        try:
            task_id = f"image_{user_id}_{datetime.now().timestamp()}"
            nickname = get_user_nickname_wrapper(user_id, use_cache=True)

            with task_tracking_lock:
                task_tracking['queued'].append({
                    'id': task_id,
                    'function': 'async_generate_image_task',
                    'queue_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'user_id': user_id,
                    'nickname': nickname
                })

            image_queue.put_nowait((async_generate_image_task, (event,), task_id))
            return True
        except queue.Full:
            smart_reply(user_id, event.reply_token, access_error(user_id), configuration, DIVIDER)
            return True

    # 不是图片生成任务
    return False


def handle_accept_perm_request(user_id: str, request_id: str) -> TextMessage:
    """
    处理接受权限请求的命令

    Args:
        user_id: 用户ID
        request_id: 请求ID

    Returns:
        TextMessage对象
    """

    result = accept_perm_request(user_id, request_id)

    if result['success']:
        text = get_multilingual_text(perm_request_accept_success_text, user_id).format(
            token_id=result['token_id'],
            requester_name=result.get('requester_name', result['token_id'])
        )
    else:
        # 不直接暴露错误详情给用户，使用通用错误消息
        notify_admins_error(
            error_title="Permission Request Accept Error",
            error_details=f"Error: {result['error']}\nMessage: {result['message']}\nRequest ID: {request_id}",
            context={
                "User ID": user_id,
                "Request ID": request_id,
                "Error Type": result['error']
            },
            admin_id=ADMIN_ID,
            configuration=configuration,
            error_notification_enabled=ERROR_NOTIFICATION_ENABLED
        )
        text = get_multilingual_text(system_error_text, user_id)

    return TextMessage(text=text)


def handle_reject_perm_request(user_id: str, request_id: str) -> TextMessage:
    """
    处理拒绝权限请求的命令

    Args:
        user_id: 用户ID
        request_id: 请求ID

    Returns:
        TextMessage对象
    """

    result = reject_perm_request(user_id, request_id)

    if result['success']:
        text = get_multilingual_text(perm_request_reject_success_text, user_id).format(
            token_id=result['token_id'],
            requester_name=result.get('requester_name', result['token_id'])
        )
    else:
        # 不直接暴露错误详情给用户，使用通用错误消息
        notify_admins_error(
            error_title="Permission Request Reject Error",
            error_details=f"Error: {result['error']}\nMessage: {result['message']}\nRequest ID: {request_id}",
            context={
                "User ID": user_id,
                "Request ID": request_id,
                "Error Type": result['error']
            },
            admin_id=ADMIN_ID,
            configuration=configuration,
            error_notification_enabled=ERROR_NOTIFICATION_ENABLED
        )
        text = get_multilingual_text(system_error_text, user_id)

    return TextMessage(text=text)


@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event):
    """
    文本消息处理入口

    根据消息类型智能路由:
    - Web任务 → webtask_queue (网络请求，如 maimai_update)
    - 图片生成任务 → image_queue (图片生成，如 b50 等)
    - 其他任务 → 同步处理 (快速文本响应)
    """
    # 清理消息文本中的 mention 特殊字符（LINE 的 mention 格式是 \ufffd@显示名\ufffd）
    # 移除所有不可见的 Unicode 字符和 @ 后的用户名
    original_text = event.message.text
    cleaned_text = re.sub(r'[\ufffd]', '', original_text)  # 移除替换字符
    cleaned_text = re.sub(r'@\S+\s*', '', cleaned_text)     # 移除 @用户名
    cleaned_text = cleaned_text.strip()

    # 替换 event.message.text 用于命令匹配
    event.message.text = cleaned_text

    if original_text != cleaned_text:
        logger.debug(f"[TextCleaning] Cleaned mention: original='{original_text}', cleaned='{cleaned_text}'")

    # 检查是否是web任务
    if route_to_web_queue(event):
        return

    # 检查是否是图片生成任务
    if route_to_image_queue(event):
        return

    # 同步处理其他文本命令
    handle_sync_text_command(event)


# ==================== 任务处理函数 ====================

def handle_sync_text_command(event):
    """
    同步处理文本命令 - 直接在主线程执行

    命令分类：
    1. 基础命令 - donate, unbind, get me, friend list
    2. 模糊匹配命令 - 歌曲查询、Rating 对照、达成情况等
    3. B 系列命令 - b50, b100, rct50, apb50 等
    4. 特殊命令 - bind, language, calc
    5. 管理员命令 - dxdata update, devtoken
    """
    # 记录开始时间以统计响应时间
    start_time = time.time()

    def tracked_reply(user_id, reply_token, reply_message):
        """包装 smart_reply 并更新统计"""
        # 计算响应时间
        response_time = (time.time() - start_time) * 1000  # 转换为毫秒

        # 更新统计
        with stats_lock:
            STATS['tasks_processed'] += 1
            STATS['response_time'] += response_time
            logger.debug(f"[Sync] ✓ Command processed: total={STATS['tasks_processed']}, avg_time={STATS['response_time']/STATS['tasks_processed']:.1f}ms")

        return smart_reply(user_id, reply_token, reply_message, configuration, DIVIDER)

    user_message = event.message.text.strip().lower()
    user_id = event.source.user_id

    # ========================================
    # 用户上下文初始化
    # ========================================

    # 检查 @ mention（仅提取信息，不阻断非命令消息）
    mentioned_user_id = None
    if hasattr(event.message, 'mention') and event.message.mention:
        mentionees = event.message.mention.mentionees
        if mentionees:
            # 多个 mention 时只取第一个用户
            if len(mentionees) >= 2:
                logger.debug(f"[Mention] Multiple mentions detected, using first one: user_id={user_id}")
            first_mention = mentionees[0]
            if hasattr(first_mention, 'user_id') and first_mention.user_id:
                mentioned_user_id = first_mention.user_id
                if mentioned_user_id in USERS:
                    logger.info(f"[Mention] User mentioned: user_id={user_id}, mentioned_user_id={mentioned_user_id}")
                else:
                    logger.debug(f"[Mention] Mentioned user not registered: mentioned_user_id={mentioned_user_id}")

    # 初始化用户版本和目标用户
    if user_id in USERS:
        mai_ver = USERS[user_id].get("version", "jp")
        # 只有当 mentioned_user_id 存在且已注册时才使用
        if mentioned_user_id and mentioned_user_id in USERS:
            id_use = mentioned_user_id
        else:
            id_use = user_id
        mai_ver_use = USERS[id_use].get("version", "jp") if id_use in USERS else mai_ver

        # 重置 id_use（非 mention 情况）
        if not mentioned_user_id:
            edit_user_value(user_id, "id_use", user_id)
    else:
        id_use = user_id
        mai_ver = "jp"
        mai_ver_use = "jp"

    # ========================================
    # 1. 基础命令 - 精确匹配
    # ========================================
    COMMAND_MAP = {
        # 捐赠
        "donate": lambda: donate_message,
        "ドネーション": lambda: donate_message,

        # 账户管理
        "unbind": lambda: user_unbind(user_id),
        "アンバインド": lambda: user_unbind(user_id),
        "get me": lambda: generate_user_info_flex(user_id),
        "getme": lambda: generate_user_info_flex(user_id),
        "ゲットミー": lambda: generate_user_info_flex(user_id),

        # 好友列表
        "friend list": lambda: get_friend_list(user_id),
        "フレンドリスト": lambda: get_friend_list(user_id),
        "friendlist": lambda: get_friend_list(user_id),

        # 系统状态
        "status": lambda: get_bot_status(user_id)
    }

    if user_message in COMMAND_MAP:
        reply_message = COMMAND_MAP[user_message]()
        return tracked_reply(user_id, event.reply_token, reply_message)

    # ========================================
    # 2. 模糊匹配命令 - 规则匹配
    # ========================================
    SPECIAL_RULES = [
        # 歌曲搜索（通过ID）
        (lambda msg: msg.startswith("search ") and len(msg.split()) == 2 and len(msg.split()[1]) == 6,
         lambda msg: search_song_by_id(user_id, msg.split()[1], mai_ver)),

        # Calc （通过ID）
        (lambda msg: msg.startswith("calc-song ") and len(msg.split()) == 2 and len(msg.split()[1]) == 6,
         lambda msg: calc_by_id(user_id, msg.split()[1], mai_ver)),

        # 成绩搜索（通过ID）
        (lambda msg: msg.startswith("search-record ") and len(msg.split()) == 2 and len(msg.split()[1]) == 6,
         lambda msg: get_song_record_by_id(id_use, msg.split()[1], mai_ver_use)),

        # 歌曲信息查询
        (lambda msg: msg.endswith(("ってどんな曲", "info", "song-info")),
         lambda msg: search_song(user_id, re.sub(r"\s*(ってどんな曲|info|song-info)$", "", msg).strip(), mai_ver)),

        # 随机歌曲
        (lambda msg: msg.startswith(("ランダム曲", "ランダム", "random-song", "random")),
         lambda msg: random_song(user_id, re.sub(r"^(ランダム曲|ランダム|random-song|random)", "", msg).strip(), mai_ver)),

        # Rating 对照表
        (lambda msg: msg.startswith(("rc ", "RC ", "Rc ")),
         lambda msg: handle_rc_command(msg, user_id)),

        # 版本达成情况
        (lambda msg: msg.endswith(("の達成状況", "の達成情報", "の達成表", "achievement-list", "achievement")),
         lambda msg: generate_plate_rcd(id_use, re.sub(r"\s*(の達成状況|の達成情報|の達成表|achievement-list|achievement)$", "", msg).strip(), mai_ver_use)),

        # 歌曲成绩记录
        (lambda msg: msg.endswith(("のレコード", "song-record", "record")),
         lambda msg: get_song_record(id_use, re.sub(r"\s*(のレコード|song-record|record)$", "", msg).strip(), mai_ver_use)),

        # 等级成绩列表
        (lambda msg: re.match(r".+(のレコードリスト|record-list|records)[ 　]*\d*$", msg),
         lambda msg: generate_level_records(
             id_use,
             re.sub(r"\s*(のレコードリスト|record-list|records)[ 　]*\d*$", "", msg).strip(),
             mai_ver_use,
             int(re.search(r"(\d+)$", msg).group(1)) if re.search(r"(\d+)$", msg) else 1)),

        # 版本歌曲列表
        (lambda msg: msg.endswith(("のバージョンリスト", "version-list", "version")),
         lambda msg: generate_version_songs(user_id, re.sub(r"\s*\+\s*", " PLUS", re.sub(r"(のバージョンリスト|version-list|version)$", "", msg)).strip(), mai_ver)),

        # 定数查询
        (lambda msg: msg.endswith(("の定数リスト", "のレベルリスト", "level-list")),
         lambda msg: generate_internallevel_songs(user_id, re.sub(r"\s*(の定数リスト|のレベルリスト|level-list)$", "", msg), mai_ver)),

        # 权限请求管理
        (lambda msg: msg.startswith("accept-perm-request "),
         lambda msg: handle_accept_perm_request(user_id, re.sub(r"^accept-perm-request ", "", msg).strip())),

        (lambda msg: msg.startswith("reject-perm-request "),
         lambda msg: handle_reject_perm_request(user_id, re.sub(r"^reject-perm-request ", "", msg).strip()))
    ]

    for cond, func in SPECIAL_RULES:
        if cond(user_message):
            reply_message = func(user_message)
            return tracked_reply(user_id, event.reply_token, reply_message)

    # ========================================
    # 3. B 系列命令 - 成绩排行
    # ========================================
    first_word = re.split(r"[ \n]", user_message.lower(), 1)[0]
    rest_text = re.split(r"[ \n]", user_message.lower(), 1)[1] if re.search(r"[ \n]", user_message) else ""

    RANK_COMMANDS = {
        # Best 系列
        ("b50", "best50", "best 50", "ベスト50"): "best50",
        ("b100", "best100", "best 100", "ベスト100"): "best100",
        ("b35", "best35", "best 35", "ベスト35"): "best35",
        ("b15", "best15", "best 15", "ベスト15"): "best15",

        # All Best 系列
        ("ab35", "allb35", "all best 35", "オールベスト35"): "allb35",
        ("ab50", "allb50", "all best 50", "オールベスト50"): "allb50",
        ("ab100", "allb100", "all best 100", "オールベスト100"): "allb100",

        # 特殊系列
        ("apb50", "ap50", "all perfect 50", "オールパーフェクト50"): "apb50",
        ("fdxb50", "fdx50", "Full DX 50", "フールでらっくす50"): "fdxb50",
        ("rct50", "r50", "recent50", "recent 50"): "rct50",
        ("idealb50", "idlb50", "ideal best 50", "理想的ベスト50"): "idealb50",
        ("unknown", "unknown songs", "unknown data", "未発見"): "UNKNOWN",
    }

    for aliases, mode in RANK_COMMANDS.items():
        if first_word in aliases:
            reply_message = generate_records(id_use, mode, rest_text, mai_ver_use)
            return tracked_reply(user_id, event.reply_token, reply_message)

    # ========================================
    # 4. SEGA ID 绑定
    # ========================================
    BIND_COMMANDS = ["bind", "segaid bind", "バインド"]
    if user_message.lower() in BIND_COMMANDS:
        # 检查用户是否已设置语言
        user_data = USERS.get(user_id, {})
        has_language = 'language' in user_data

        # 如果用户还没有设置语言，先让用户选择语言
        if not has_language:
            buttons_template = ButtonsTemplate(
                title=language_select_title,
                text=language_select_description,
                actions=[
                    MessageAction(label=language_button_ja, text="language jp"),
                    MessageAction(label=language_button_en, text="language en"),
                    MessageAction(label=language_button_zh, text="language zh")
                ]
            )
            reply_message = TemplateMessage(
                alt_text=language_select_alt,
                template=buttons_template
            )

            return tracked_reply(user_id, event.reply_token, reply_message)

        # 用户已设置语言，检查是否已经绑定账号
        has_account = all(key in user_data for key in ['sega_id', 'sega_pwd', 'version'])

        if has_account:
            # 已经绑定过账号，提示先解绑
            reply_message = TextMessage(text=get_multilingual_text(already_bound_text, user_id))
            return tracked_reply(user_id, event.reply_token, reply_message)

        # 用户已设置语言且未绑定账号，显示绑定按钮
        bind_url = f"https://{DOMAIN}/linebot/sega_bind?token={generate_bind_token(user_id)}"

        # 使用多语言文本
        buttons_template = ButtonsTemplate(
            title=get_multilingual_text(sega_bind_title_text, user_id),
            text=get_multilingual_text(sega_bind_description_text, user_id),
            actions=[URIAction(
                label=get_multilingual_text(sega_bind_button_text, user_id),
                uri=bind_url
            )]
        )
        reply_message = TemplateMessage(
            alt_text=get_multilingual_text(sega_bind_alt_text, user_id),
            template=buttons_template
        )

        return tracked_reply(user_id, event.reply_token, reply_message)

    # ========================================
    # 5. 语言设置
    # ========================================
    if user_message.startswith("language "):
        lang_code = user_message[9:].strip().lower()

        # 验证语言代码
        if lang_code not in ["ja", "en", "zh"]:
            reply_message = TextMessage(text="Invalid language code. Please use: ja, en, or zh")
            return tracked_reply(user_id, event.reply_token, reply_message)

        # 设置用户语言
        user_set_language(user_id, lang_code)

        # 使用多语言成功消息
        success_text = get_multilingual_text(language_set_success_text, user_id)

        # 添加快捷回复按钮
        quick_reply = get_bind_quick_reply(user_id)

        reply_message = TextMessage(text=success_text, quick_reply=quick_reply)
        return tracked_reply(user_id, event.reply_token, reply_message)

    # ========================================
    # 6. Calc 计算器
    # ========================================
    if user_message.startswith("calc "):
        try:
            num = list(map(int, user_message[5:].split()))
            if len(num) == 4:
                num = [num[0], num[1], num[2], 0, num[3]]
            if len(num) != 5:
                raise ValueError
            notes = dict(zip(['tap', 'hold', 'slide', 'touch', 'break'], num))
            scores = get_note_score(notes)
            reply_message = generate_calc_result_flex(notes, scores)
        except Exception:
            reply_message = input_error(user_id)
        return tracked_reply(user_id, event.reply_token, reply_message)

    # ========================================
    # 7. 管理员命令
    # ========================================
    if user_id in ADMIN_ID:
        if user_message == "dxdata update":
            # 使用新的对比更新函数
            result = update_dxdata_with_comparison(DXDATA_URL, DXDATA_LIST)
            read_dxdata()  # 重新加载到内存

            # 使用多语言函数构建消息
            message_text = build_dxdata_update_message(result, user_id)
            reply_message = TextMessage(text=message_text)

            # 回复执行命令的管理员
            smart_reply(user_id, event.reply_token, reply_message, configuration, DIVIDER)

            # 推送通知给所有其他管理员
            for admin_user_id in ADMIN_ID:
                if admin_user_id != user_id:  # 不重复发送给执行命令的管理员
                    try:
                        # 为每个管理员构建对应语言的消息
                        admin_message_text = build_dxdata_update_message(result, admin_user_id)
                        notification_message = dxdata_update_notification(admin_message_text, admin_user_id)
                        smart_push(admin_user_id, notification_message, configuration)
                    except Exception as e:
                        logger.error(f"[Notification] ✗ Failed to notify admin: admin_id={admin_user_id}, context=dxdata_update, error={e}")

            return

        if user_message.startswith("devtoken "):
            # Parse command
            parts = user_message.split(maxsplit=2)

            if len(parts) < 2:
                # Show usage
                reply_message = TextMessage(text=get_multilingual_text(devtoken_usage_text, user_id))
                return tracked_reply(user_id, event.reply_token, reply_message)

            subcommand = parts[1]

            if subcommand == "create" and len(parts) >= 3:
                note = parts[2]
                result = create_dev_token(note, user_id)
                if result:
                    text = get_multilingual_text(devtoken_create_success_text, user_id)
                    text = text.format(
                        token_id=result["token_id"],
                        note=result["note"],
                        token=result["token"],
                        created_at=result["created_at"]
                    )
                    reply_message = TextMessage(text=text)
                else:
                    reply_message = TextMessage(text=get_multilingual_text(devtoken_create_failed_text, user_id))
                return tracked_reply(user_id, event.reply_token, reply_message)

            elif subcommand == "list":
                tokens = list_dev_tokens()
                if not tokens:
                    text = get_multilingual_text(devtoken_list_empty_text, user_id)
                else:
                    header = get_multilingual_text(devtoken_list_header_text, user_id)
                    token_lines = []
                    for t in tokens:
                        status = "❌ Revoked" if t["revoked"] else "✅ Active"
                        token_lines.append(
                            f"• {t['token_id']}\n"
                            f"  Note: {t['note']}\n"
                            f"  Status: {status}\n"
                            f"  Created: {t['created_at']}\n"
                            f"  Last used: {t['last_used']}"
                        )
                    text = header + "\n\n" + "\n\n".join(token_lines)
                reply_message = TextMessage(text=text)
                return tracked_reply(user_id, event.reply_token, reply_message)

            elif subcommand == "revoke" and len(parts) >= 3:
                token_id = parts[2]
                success = revoke_dev_token(token_id)
                if success:
                    text = get_multilingual_text(devtoken_revoke_success_text, user_id)
                    text = text.format(token_id=token_id)
                    reply_message = TextMessage(text=text)
                else:
                    reply_message = TextMessage(text=get_multilingual_text(devtoken_revoke_failed_text, user_id))
                return tracked_reply(user_id, event.reply_token, reply_message)

            elif subcommand == "info" and len(parts) >= 3:
                token_id = parts[2]
                info = get_token_info(token_id=token_id)
                if info:
                    text = get_multilingual_text(devtoken_info_text, user_id)
                    status = "❌ Revoked" if info["revoked"] else "✅ Active"
                    text = text.format(
                        token_id=info["token_id"],
                        note=info["note"],
                        status=status,
                        created_at=info["created_at"],
                        created_by=info["created_by"],
                        last_used=info["last_used"],
                        token=info["token"]
                    )
                    reply_message = TextMessage(text=text)
                else:
                    reply_message = TextMessage(text=get_multilingual_text(devtoken_info_not_found_text, user_id))
                return tracked_reply(user_id, event.reply_token, reply_message)

            else:
                # Invalid subcommand or missing arguments
                reply_message = TextMessage(text=get_multilingual_text(devtoken_usage_text, user_id))
                return tracked_reply(user_id, event.reply_token, reply_message)

        if user_message == "backup":
            # 创建系统备份
            try:
                # 准备数据库配置
                db_config = {
                    'host': DB_HOST,
                    'user': DB_USER,
                    'password': DB_PASSWORD,
                    'database': DB_NAME
                }

                # 读取当前配置
                with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)

                # 创建备份
                success, message, backup_path = create_backup(
                    users_data=USERS,  # 未加密的用户数据
                    config_data=config_data,
                    db_config=db_config,
                    backup_password=ADMIN_PASSWORD,
                    output_dir=BACKUP_DIR
                )

                # 发送结果消息
                result_message = TextMessage(text=message)
                smart_reply(user_id, event.reply_token, result_message, configuration, DIVIDER)

                return

            except Exception as e:
                logger.error(f"[Backup] ✗ Backup command error: user_id={user_id}, error={e}", exc_info=True)
                error_message = TextMessage(text=f"❌ Backup failed\nError: {str(e)}")
                smart_reply(user_id, event.reply_token, error_message, configuration, DIVIDER)
                return

    # ========================================
    # 默认：未匹配任何命令
    # ========================================
    return

#图片信息处理
@handler.add(MessageEvent, message=ImageMessageContent)
def handle_image_message(event):
    message_id = event.message.id
    with ApiClient(configuration) as api_client:
        line_bot_blob_api = MessagingApiBlob(api_client)
        message_content = line_bot_blob_api.get_message_content(message_id)

    image = Image.open(BytesIO(message_content))
    image.load()  # 强制加载像素数据到内存，避免 BytesIO 作用域问题

    qr_results = decode(image)

    reply_msg = []

    if qr_results:
        # 发现 QR 码，解析并处理（同步，速度快）
        for qr in qr_results:
            data = qr.data.decode("utf-8")
            new_reply_msg = handle_image_message_task(event.source.user_id, event.reply_token, data, image)
            if new_reply_msg:
                reply_msg.append(new_reply_msg)
        if reply_msg:
            smart_reply(
                event.source.user_id,
                event.reply_token,
                reply_msg,
                configuration,
                DIVIDER
            )

def handle_image_message_task(user_id, reply_token, data, image=None):
    """
    处理图片消息中的数据

    Args:
        user_id: 用户ID
        reply_token: 回复令牌
        data: QR码解析出的数据
        image: PIL Image 对象（用于封面匹配）

    Returns:
        消息对象或消息列表
    """
    if DOMAIN in data:
        return handle_internal_link(user_id, reply_token, data)
    else:
        return TextMessage(text=data)

def handle_internal_link(user_id, reply_token, data):
    mai_ver = "jp"
    if user_id in USERS:
        if 'version' in USERS[user_id]:
            mai_ver = USERS[user_id]['version']

    URL_MAP = []

    for condition, action in URL_MAP:
        if condition(data, DOMAIN):
            return action(data, user_id, reply_token, DOMAIN, mai_ver)
        else:
            return TextMessage(text=data)


#位置信息处理
@handler.add(MessageEvent, message=LocationMessageContent)
def handle_location_message(event):
    """
    位置消息处理 - 异步获取附近机厅
    """

    lat = event.message.latitude
    lng = event.message.longitude
    user_id = event.source.user_id

    stores = asyncio.run(get_nearby_maimai_stores(lat, lng, USERS[user_id]['version']))

    # 检查维护状态
    if stores == "MAINTENANCE":
        reply_message = maintenance_error(user_id)
    elif not stores:
        reply_message = store_error(user_id)
    else:
        # 使用 LINE SDK v3 对象构建的 Flex Message（已修复结构问题）
        user_id = event.source.user_id
        reply_message = generate_store_buttons(
            user_id,
            get_nearby_stores_alt_text(user_id),
            stores[:35]
        )

    smart_reply(
        event.source.user_id,
        event.reply_token,
        reply_message,
        configuration,
        DIVIDER
    )

# Postback 事件处理
@handler.add(PostbackEvent)
def handle_postback(event):
    """
    处理 Postback 事件（来自 PostbackAction 的按钮点击）

    支持：
    - 公告投票 (action=vote_notice)
    - 其他 Postback 事件（作为文本消息处理）
    """
    user_id = event.source.user_id
    postback_data = event.postback.data

    logger.info(f"[Postback] user_id={user_id}, data={postback_data}")

    try:
        # 处理公告投票
        if 'action=vote_notice' in postback_data:
            # 解析postback data
            params = dict(param.split('=') for param in postback_data.split('&'))
            action = params.get('action')
            notice_id = params.get('notice_id')
            vote_type = params.get('vote')  # 'support' | 'oppose'

            if action == 'vote_notice' and notice_id and vote_type in ['support', 'oppose']:
                # 验证公告存在且启用投票
                notice = get_notice_by_id(notice_id)
                if not notice:
                    logger.warning(f"[Notice] ⚠ Notice not found: notice_id={notice_id}")
                    return

                if not notice.get('voting_enabled'):
                    logger.warning(f"[Notice] ⚠ Voting not enabled: notice_id={notice_id}")
                    return

                # 记录投票
                success = record_notice_vote(user_id, notice_id, vote_type)

                if success:
                    # 获取统计数据
                    stats = calculate_notice_stats(notice_id)

                    # 获取用户语言
                    lang = get_user_language(user_id) or 'ja'

                    # 构建反馈消息（多语言）
                    vote_success_text = {
                        'ja': f"投票ありがとうございます！\n\n支持: {stats['support_count']}人 ({stats['support_count']/(stats['support_count']+stats['oppose_count'])*100 if stats['support_count']+stats['oppose_count'] > 0 else 0:.1f}%)\n反対: {stats['oppose_count']}人 ({stats['oppose_count']/(stats['support_count']+stats['oppose_count'])*100 if stats['support_count']+stats['oppose_count'] > 0 else 0:.1f}%)",
                        'en': f"Thank you for voting!\n\nSupport: {stats['support_count']} ({stats['support_count']/(stats['support_count']+stats['oppose_count'])*100 if stats['support_count']+stats['oppose_count'] > 0 else 0:.1f}%)\nOppose: {stats['oppose_count']} ({stats['oppose_count']/(stats['support_count']+stats['oppose_count'])*100 if stats['support_count']+stats['oppose_count'] > 0 else 0:.1f}%)",
                        'zh': f"感谢您的投票！\n\n支持: {stats['support_count']}人 ({stats['support_count']/(stats['support_count']+stats['oppose_count'])*100 if stats['support_count']+stats['oppose_count'] > 0 else 0:.1f}%)\n反对: {stats['oppose_count']}人 ({stats['oppose_count']/(stats['support_count']+stats['oppose_count'])*100 if stats['support_count']+stats['oppose_count'] > 0 else 0:.1f}%)"
                    }

                    reply_message = TextMessage(text=vote_success_text.get(lang, vote_success_text['ja']))

                    # 发送回复
                    smart_reply(user_id, event.reply_token, reply_message, configuration, DIVIDER)

                    logger.info(f"[Notice] ✓ Vote processed: user_id={user_id}, notice_id={notice_id}, vote={vote_type}")
                    return
                else:
                    logger.error(f"[Notice] ✗ Vote failed: user_id={user_id}, notice_id={notice_id}")
                    return

        # 其他Postback事件：走原有的文本命令逻辑
        # 创建一个模拟的 TextMessageContent 对象
        class MockTextMessage:
            def __init__(self, text):
                self.text = text
                self.type = 'text'

        # 创建一个模拟的 MessageEvent 对象
        class MockMessageEvent:
            def __init__(self, original_event, text):
                self.source = original_event.source
                self.reply_token = original_event.reply_token
                self.message = MockTextMessage(text)

        # 创建模拟事件，使用 postback data 作为消息文本
        mock_event = MockMessageEvent(event, postback_data)

        # 检查是否是web任务
        if route_to_web_queue(mock_event):
            return

        # 检查是否是图片生成任务
        if route_to_image_queue(mock_event):
            return

        # 同步处理文本命令（走和 MessageEvent 相同的逻辑）
        handle_sync_text_command(mock_event)

    except Exception as e:
        logger.error(f"[Postback] ✗ Error processing postback: user_id={user_id}, data={postback_data}, error={e}")
        logger.error(traceback.format_exc())

# ==================== 管理后台路由 ====================

# 任务队列追踪
task_tracking = {
    'running': [],
    'queued': [],
    'cancelled': set(),  # 存储已取消的任务ID
    'completed': []  # 存储已完成的任务 (最多保留20个)
}
task_tracking_lock = threading.Lock()
MAX_COMPLETED_TASKS = 20  # 最多保留20个已完成任务

# ==================== 辅助函数 ====================

def check_admin_auth():
    """检查管理员是否已登录"""
    return session.get('admin_authenticated', False)

def get_user_nickname_wrapper(user_id, use_cache=True):
    """
    获取用户昵称的wrapper函数
    在main.py中使用,自动传递line_bot_api
    若无法通过LINE API获取昵称,则从用户数据中获取nickname字段
    """
    nickname = None

    # 尝试从LINE API获取昵称
    try:
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            nickname = get_user_nickname(user_id, line_bot_api, use_cache)

            # 检查是否为错误消息
            if nickname and ("Unknown" in nickname or "API Error" in nickname or "Blocked" in nickname):
                nickname = None
    except Exception as e:
        logger.debug(f"[User] Failed to get LINE nickname: user_id={user_id}, error={e}")
        nickname = None

    # 如果LINE API失败,尝试从用户数据获取
    if not nickname:
        if user_id in USERS and USERS[user_id].get('nickname'):
            nickname = USERS[user_id].get('nickname')

    return nickname if nickname else f"User {user_id[:8]}..."

@app.route("/linebot/admin", methods=["GET", "POST"])
def admin_panel():
    """管理后台主页面"""
    if request.method == "POST":
        # 处理登录
        password = request.form.get("password", "")

        # 验证密码
        if password and password == ADMIN_PASSWORD:
            session['admin_authenticated'] = True
            session.permanent = True
            return redirect("/linebot/admin")
        else:
            return render_template("admin_login.html", error="Invalid password")

    # GET请求
    if not check_admin_auth():
        return render_template("admin_login.html")

    # 准备用户数据 - 不获取昵称,使用懒加载
    users_data = {}
    for user_id, user_info in USERS.items():
        users_data[user_id] = {
            'nickname': 'Loading...',  # 初始占位符
            'json_str': json.dumps(user_info, indent=2, ensure_ascii=False)
        }

    # 获取任务队列信息
    with task_tracking_lock:
        running_tasks = list(task_tracking['running'])
        queued_tasks = list(task_tracking['queued'])
        completed_tasks = list(task_tracking['completed'])

    # 为任务添加用户昵称 - 也使用懒加载
    for task in running_tasks + queued_tasks + completed_tasks:
        if 'user_id' in task:
            task['nickname'] = 'Loading...'

    # 获取统计信息
    total_users = len(USERS)
    jp_users = sum(1 for user in USERS.values() if user.get("version") == "jp")
    intl_users = sum(1 for user in USERS.values() if user.get("version") == "intl")

    # 计算运行时长
    uptime = datetime.now() - SERVICE_START_TIME
    days = uptime.days
    hours, remainder = divmod(uptime.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str = f"{days}d {hours}h {minutes}m"

    # 计算百分比
    jp_percent = round((jp_users / total_users * 100) if total_users > 0 else 0, 1)
    intl_percent = round((intl_users / total_users * 100) if total_users > 0 else 0, 1)

    # 获取系统信息
    cpu_percent = round(psutil.cpu_percent(interval=0.1), 1)
    cpu_count = psutil.cpu_count()
    cpu_count_used = round(cpu_percent / 100 * cpu_count, 1)

    memory = psutil.virtual_memory()
    memory_percent = round(memory.percent, 1)
    total_memory = round(memory.total / (1024**3), 1)  # GB
    memory_used_gb = round(memory.used / (1024**3), 1)  # GB

    # 获取线程信息
    thread_count = threading.active_count()

    # 线程安全地读取统计数据
    with stats_lock:
        total_tasks = STATS['tasks_processed']
        total_time = STATS['response_time']

    # 计算平均响应时间
    avg_response = round(total_time / total_tasks if total_tasks > 0 else 0, 1)

    stats = {
        'total_users': total_users,
        'jp_users': jp_users,
        'intl_users': intl_users,
        'jp_percent': jp_percent,
        'intl_percent': intl_percent,
        'cpu_percent': cpu_percent,
        'cpu_count_total': cpu_count,
        'cpu_count_used': cpu_count_used,
        'memory_percent': memory_percent,
        'memory_used_gb': memory_used_gb,
        'total_memory': total_memory,
        'uptime': uptime_str,
        'python_version': platform.python_version(),
        'platform': f"{platform.system()} {platform.release()}",
        'platform_short': platform.system(),
        'hostname': socket.gethostname(),
        'port': PORT,
        'image_queue_size': image_queue.qsize(),
        'web_queue_size': webtask_queue.qsize(),
        'max_queue_size': MAX_QUEUE_SIZE,
        'thread_count': thread_count,
        'total_tasks_processed': total_tasks,
        'avg_response_time': avg_response,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    # 读取日志
    logs = ""
    try:
        with open('jietng.log', 'r', encoding='utf-8') as f:
            logs = ''.join(f.readlines()[-100:])
    except Exception as e:
        logs = f"Error reading logs: {e}"

    return render_template(
        "admin_panel.html",
        users_data=users_data,
        total_users=total_users,
        running_tasks=running_tasks,
        queued_tasks=queued_tasks,
        completed_tasks=completed_tasks,
        stats=stats,
        logs=logs
    )

@app.route("/linebot/admin/logout", methods=["GET"])
def admin_logout():
    """管理员登出"""
    session.pop('admin_authenticated', None)
    return redirect("/linebot/admin")

@app.route("/linebot/admin/trigger_update", methods=["POST"])
@csrf.exempt
def admin_trigger_update():
    """触发指定用户的maimai_update"""
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    user_id = data.get('user_id')

    if not user_id:
        return jsonify({'error': 'User ID required'}), 400

    try:
        # 创建一个模拟的event对象用于异步任务
        class MockEvent:
            def __init__(self, user_id):
                self.source = type('obj', (object,), {'user_id': user_id})()
                self.reply_token = None

        mock_event = MockEvent(user_id)

        # 生成任务ID
        task_id = f"admin_update_{user_id}_{datetime.now().timestamp()}"

        # 获取用户昵称用于显示
        nickname = get_user_nickname_wrapper(user_id, use_cache=True)

        # 添加到任务追踪（在入队之前）
        with task_tracking_lock:
            task_tracking['queued'].append({
                'id': task_id,
                'function': 'async_admin_maimai_update_task',
                'queue_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'user_id': user_id,
                'nickname': nickname
            })

        # 添加到webtask队列（使用3元组格式）
        webtask_queue.put_nowait((async_admin_maimai_update_task, (mock_event,), task_id))

        return jsonify({
            'success': True,
            'message': f'Update task queued for user {user_id}'
        })
    except queue.Full:
        return jsonify({
            'success': False,
            'message': 'Task queue is full'
        }), 503
    except Exception as e:
        logger.error(f"[Admin] ✗ Trigger update error: user_id={user_id}, error={e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route("/linebot/admin/cancel_task", methods=["POST"])
@csrf.exempt
def admin_cancel_task():
    """取消排队中的任务"""
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    task_id = data.get('task_id')

    if not task_id:
        return jsonify({'error': 'Task ID required'}), 400

    # 检查任务是否在排队中
    with task_tracking_lock:
        queued_task = None
        for task in task_tracking['queued']:
            if task.get('id') == task_id:
                queued_task = task
                break

        if not queued_task:
            return jsonify({
                'success': False,
                'message': 'Task not found in queue (already running or completed)'
            }), 404

        # 将任务添加到已取消集合
        task_tracking['cancelled'].add(task_id)

        # 标记任务为已取消
        queued_task['status'] = 'cancelled'

        logger.info(f"[Admin] ✓ Task cancelled: task_id={task_id}")

    return jsonify({
        'success': True,
        'message': f'Task {task_id} marked for cancellation'
    })

@app.route("/linebot/admin/get_logs", methods=["GET"])
def admin_get_logs():
    """获取最新日志"""
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        with open('jietng.log', 'r', encoding='utf-8') as f:
            logs = ''.join(f.readlines()[-100:])
        return jsonify({'logs': logs})
    except Exception as e:
        return jsonify({'logs': f'Error reading logs: {e}'})

@app.route("/linebot/admin/memory_stats", methods=["GET"])
def admin_memory_stats():
    """获取内存管理器状态"""
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        stats = memory_manager.get_stats()
        return jsonify({'success': True, 'stats': stats})
    except Exception as e:
        logger.error(f"[Admin] ✗ Memory stats error: error={e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/linebot/admin/trigger_cleanup", methods=["POST"])
@csrf.exempt
def admin_trigger_cleanup():
    """手动触发内存清理"""
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        stats = memory_manager.cleanup()
        return jsonify({'success': True, 'message': 'Memory cleanup completed', 'stats': stats})
    except Exception as e:
        logger.error(f"[Admin] ✗ Cleanup trigger error: error={e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/linebot/admin/get_notices", methods=["GET"])
def admin_get_notices():
    """获取所有公告(包括草稿)"""
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        notices = get_all_notices(include_drafts=True)
        return jsonify({'success': True, 'notices': notices})
    except Exception as e:
        logger.error(f"[Admin] ✗ Get notices error: error={e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route("/linebot/admin/create_notice", methods=["POST"])
@csrf.exempt
def admin_create_notice():
    """创建新公告 - 支持多语言、草稿、投票"""
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()

    # 多语言内容
    content_zh = data.get('content_zh', '').strip()
    content_ja = data.get('content_ja', '').strip()
    content_en = data.get('content_en', '').strip()

    # 验证至少填写一种语言
    if not any([content_ja, content_en, content_zh]):
        return jsonify({'success': False, 'message': 'At least one language content is required'}), 400

    # 构建多语言内容对象
    content_dict = {
        'zh': content_zh,
        'ja': content_ja,
        'en': content_en,
    }

    # 获取其他参数
    status = data.get('status', 'published')  # 'draft' | 'published'
    voting_enabled = data.get('voting_enabled', False)
    created_by = session.get('user_id', 'admin')

    # 按钮参数
    button_type = data.get('button_type')
    button_label_zh = data.get('button_label_zh', '').strip()
    button_label_ja = data.get('button_label_ja', '').strip()
    button_label_en = data.get('button_label_en', '').strip()
    button_value = data.get('button_value', '').strip()

    # 构建按钮标签字典
    button_label = None
    if button_type and button_value:
        button_label = {
            'zh': button_label_zh,
            'ja': button_label_ja,
            'en': button_label_en
        }

    try:
        notice_id = upload_notice(
            content=content_dict,
            status=status,
            voting_enabled=voting_enabled,
            created_by=created_by,
            button_type=button_type,
            button_label=button_label,
            button_value=button_value
        )

        # 仅发布状态的公告才清除阅读状态
        if status == 'published':
            clear_notice_read_status(notice_id)
            logger.info(f"[Admin] ✓ Notice published: notice_id={notice_id}")
        else:
            logger.info(f"[Admin] ✓ Notice saved as draft: notice_id={notice_id}")

        return jsonify({
            'success': True,
            'message': f'Notice {"published" if status == "published" else "saved as draft"} successfully',
            'notice_id': notice_id
        })
    except Exception as e:
        logger.error(f"[Admin] ✗ Create notice error: error={e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route("/linebot/admin/update_notice", methods=["POST"])
@csrf.exempt
def admin_update_notice():
    """更新公告 - 支持多语言"""
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    notice_id = data.get('notice_id')

    # 多语言内容
    content_zh = data.get('content_zh', '').strip()
    content_ja = data.get('content_ja', '').strip()
    content_en = data.get('content_en', '').strip()

    if not notice_id or not any([content_ja, content_en, content_zh]):
        return jsonify({'success': False, 'message': 'Notice ID and at least one language content are required'}), 400

    content_dict = {
        'zh': content_zh,
        'ja': content_ja,
        'en': content_en,
    }

    # 按钮参数
    button_type = data.get('button_type')
    button_label_zh = data.get('button_label_zh', '').strip()
    button_label_ja = data.get('button_label_ja', '').strip()
    button_label_en = data.get('button_label_en', '').strip()
    button_value = data.get('button_value', '').strip()
    remove_button = data.get('remove_button', False)

    # 构建按钮标签字典
    button_label = None
    if button_type and button_value:
        button_label = {
            'zh': button_label_zh,
            'ja': button_label_ja,
            'en': button_label_en
        }

    try:
        # 检查是否为最新已发布公告
        latest_notice = get_latest_published_notice()
        is_latest = latest_notice and latest_notice.get('id') == notice_id

        success = update_notice(
            notice_id,
            content_dict,
            button_type=button_type,
            button_label=button_label,
            button_value=button_value,
            remove_button=remove_button
        )

        if success:
            notice = get_notice_by_id(notice_id)
            # 如果修改的是已发布的公告,清除阅读状态
            if notice.get('status') == 'published' and is_latest:
                clear_notice_read_status(notice_id)
                logger.info(f"[Admin] ✓ Updated latest published notice: notice_id={notice_id}")
            else:
                logger.info(f"[Admin] ✓ Updated notice: notice_id={notice_id}")

            return jsonify({'success': True, 'message': 'Notice updated successfully'})
        else:
            return jsonify({'success': False, 'message': 'Notice not found'}), 404

    except Exception as e:
        logger.error(f"[Admin] ✗ Update notice error: error={e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route("/linebot/admin/delete_notice", methods=["POST"])
@csrf.exempt
def admin_delete_notice():
    """删除公告"""
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    notice_id = data.get('notice_id')

    if not notice_id:
        return jsonify({'success': False, 'message': 'Notice ID is required'}), 400

    try:
        clear_notice_record(notice_id)
        success = delete_notice(notice_id)

        if success:
            logger.info(f"[Admin] ✓ Notice deleted: notice_id={notice_id}")
            return jsonify({'success': True, 'message': 'Notice deleted successfully'})
        else:
            return jsonify({'success': False, 'message': 'Notice not found'}), 404

    except Exception as e:
        logger.error(f"[Admin] ✗ Delete notice error: error={e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route("/linebot/admin/publish_notice", methods=["POST"])
@csrf.exempt
def admin_publish_notice():
    """发布草稿公告"""
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    notice_id = data.get('notice_id')

    if not notice_id:
        return jsonify({'success': False, 'message': 'Notice ID is required'}), 400

    try:
        success = publish_notice(notice_id)

        if success:
            # 清除所有用户的阅读状态
            clear_notice_read_status(notice_id)
            logger.info(f"[Admin] ✓ Published draft notice: notice_id={notice_id}")
            return jsonify({'success': True, 'message': 'Notice published successfully'})
        else:
            return jsonify({'success': False, 'message': 'Notice not found or already published'}), 404

    except Exception as e:
        logger.error(f"[Admin] ✗ Publish notice error: error={e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route("/linebot/admin/get_notice_stats", methods=["GET"])
def admin_get_notice_stats():
    """获取公告统计数据"""
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    notice_id = request.args.get('notice_id')

    try:
        if notice_id:
            # 获取单个公告的统计
            stats = calculate_notice_stats(notice_id)
            if stats is None:
                return jsonify({'success': False, 'message': 'Notice not found'}), 404
            return jsonify({'success': True, 'stats': stats})
        else:
            # 获取所有公告的统计
            stats = get_all_notices_stats()
            return jsonify({'success': True, 'stats': stats})

    except Exception as e:
        logger.error(f"[Admin] ✗ Get notice stats error: error={e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route("/linebot/notice_vote", methods=["POST"])
@csrf.exempt
def notice_vote():
    """
    用户投票端点
    通过 LINE LIFF 或 Postback 调用
    """
    data = request.get_json()
    user_id = data.get('user_id')
    notice_id = data.get('notice_id')
    vote_type = data.get('vote_type')  # 'support' | 'oppose'

    if not all([user_id, notice_id, vote_type]):
        return jsonify({'success': False, 'message': 'Missing required parameters'}), 400

    if vote_type not in ['support', 'oppose']:
        return jsonify({'success': False, 'message': 'Invalid vote type'}), 400

    try:
        # 验证公告存在且启用投票
        notice = get_notice_by_id(notice_id)
        if not notice:
            return jsonify({'success': False, 'message': 'Notice not found'}), 404

        if not notice.get('voting_enabled'):
            return jsonify({'success': False, 'message': 'Voting is not enabled for this notice'}), 400

        # 记录投票
        success = record_notice_vote(user_id, notice_id, vote_type)

        if success:
            # 返回最新统计
            stats = calculate_notice_stats(notice_id)
            logger.info(f"[Notice] ✓ User voted: user_id={user_id}, notice_id={notice_id}, vote={vote_type}")
            return jsonify({
                'success': True,
                'message': 'Vote recorded successfully',
                'stats': stats
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to record vote'}), 500

    except Exception as e:
        logger.error(f"[Notice] ✗ Vote error: error={e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== Tip/Ad 管理 API ====================

@app.route("/linebot/admin/get_tip_ads", methods=["GET"])
def admin_get_tip_ads():
    """获取所有 tip/ad"""
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        tip_ads = get_all_tip_ads()
        return jsonify({'success': True, 'tip_ads': tip_ads})
    except Exception as e:
        logger.error(f"[Admin] ✗ Get tip/ads error: error={e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route("/linebot/admin/create_tip_ad", methods=["POST"])
@csrf.exempt
def admin_create_tip_ad():
    """创建新的 tip/ad"""
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    tip_type = data.get('type')
    text_zh = data.get('text_zh')
    text_en = data.get('text_en')
    text_ja = data.get('text_ja')
    button_type = data.get('button_type')
    button_label_zh = data.get('button_label_zh')
    button_label_en = data.get('button_label_en')
    button_label_ja = data.get('button_label_ja')
    button_value = data.get('button_value')
    enabled = data.get('enabled', True)

    if not all([tip_type, text_zh, text_en, text_ja]):
        return jsonify({'success': False, 'message': 'Missing required fields'}), 400

    if tip_type not in ['tip', 'ad']:
        return jsonify({'success': False, 'message': 'Invalid type'}), 400

    try:
        tip_ad = create_tip_ad(
            tip_type=tip_type,
            text_zh=text_zh,
            text_en=text_en,
            text_ja=text_ja,
            button_type=button_type,
            button_label_zh=button_label_zh,
            button_label_en=button_label_en,
            button_label_ja=button_label_ja,
            button_value=button_value,
            enabled=enabled
        )
        logger.info(f"[Admin] ✓ Created tip/ad: id={tip_ad['id']}, type={tip_type}")
        return jsonify({'success': True, 'tip_ad': tip_ad})
    except Exception as e:
        logger.error(f"[Admin] ✗ Create tip/ad error: error={e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route("/linebot/admin/update_tip_ad", methods=["POST"])
@csrf.exempt
def admin_update_tip_ad():
    """更新 tip/ad"""
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    tip_id = data.get('id')

    if not tip_id:
        return jsonify({'success': False, 'message': 'Missing id'}), 400

    tip_type = data.get('type')
    text_zh = data.get('text_zh')
    text_en = data.get('text_en')
    text_ja = data.get('text_ja')
    button_type = data.get('button_type')
    button_label_zh = data.get('button_label_zh')
    button_label_en = data.get('button_label_en')
    button_label_ja = data.get('button_label_ja')
    button_value = data.get('button_value')
    enabled = data.get('enabled')
    remove_button = data.get('remove_button', False)

    try:
        tip_ad = update_tip_ad(
            tip_id=tip_id,
            tip_type=tip_type,
            text_zh=text_zh,
            text_en=text_en,
            text_ja=text_ja,
            button_type=button_type,
            button_label_zh=button_label_zh,
            button_label_en=button_label_en,
            button_label_ja=button_label_ja,
            button_value=button_value,
            enabled=enabled,
            remove_button=remove_button
        )

        if tip_ad:
            logger.info(f"[Admin] ✓ Updated tip/ad: id={tip_id}")
            return jsonify({'success': True, 'tip_ad': tip_ad})
        else:
            return jsonify({'success': False, 'message': 'Tip/ad not found'}), 404
    except Exception as e:
        logger.error(f"[Admin] ✗ Update tip/ad error: error={e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route("/linebot/admin/delete_tip_ad", methods=["POST"])
@csrf.exempt
def admin_delete_tip_ad():
    """删除 tip/ad"""
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    tip_id = data.get('id')

    if not tip_id:
        return jsonify({'success': False, 'message': 'Missing id'}), 400

    try:
        success = delete_tip_ad(tip_id)
        if success:
            logger.info(f"[Admin] ✓ Deleted tip/ad: id={tip_id}")
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': 'Tip/ad not found'}), 404
    except Exception as e:
        logger.error(f"[Admin] ✗ Delete tip/ad error: error={e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== 用户管理 API ====================

@app.route("/linebot/admin/edit_user", methods=["POST"])
@csrf.exempt
def admin_edit_user():
    """编辑用户数据"""
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    user_id = data.get('user_id')
    user_data = data.get('user_data')

    if not user_id or user_data is None:
        return jsonify({
            'success': False,
            'message': 'User ID and user data required'
        }), 400

    try:
        if user_id not in USERS:
            return jsonify({
                'success': False,
                'message': f'User {user_id} not found'
            }), 404

        # 更新用户数据
        USERS[user_id] = user_data
        mark_user_dirty()
        write_user()

        logger.info(f"[Admin] ✓ User data edited: user_id={user_id}")

        # 不再发送通知给管理员

        return jsonify({
            'success': True,
            'message': 'User data updated successfully'
        })

    except Exception as e:
        logger.error(f"[Admin] ✗ Edit user error: user_id={user_id}, error={e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route("/linebot/admin/delete_user", methods=["POST"])
@csrf.exempt
def admin_delete_user():
    """删除用户"""
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    user_id = data.get('user_id')

    if not user_id:
        return jsonify({
            'success': False,
            'message': 'User ID required'
        }), 400

    try:
        if user_id not in USERS:
            return jsonify({
                'success': False,
                'message': f'User {user_id} not found'
            }), 404

        # 使用 delete_user 函数删除用户
        delete_user(user_id)

        logger.info(f"[Admin] ✓ User deleted: user_id={user_id}")

        return jsonify({
            'success': True,
            'message': f'User {user_id} deleted successfully'
        })

    except Exception as e:
        logger.error(f"[Admin] ✗ Delete user error: user_id={user_id}, error={e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route("/linebot/admin/clear_cache", methods=["POST"])
@csrf.exempt
def admin_clear_cache():
    """清除昵称缓存"""
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        with nickname_cache_lock:
            cache_size = len(nickname_cache)
            nickname_cache.clear()

        logger.info(f"[Admin] ✓ Nickname cache cleared: entries={cache_size}")

        return jsonify({
            'success': True,
            'message': f'Cache cleared ({cache_size} entries)'
        })

    except Exception as e:
        logger.error(f"[Admin] ✗ Clear cache error: error={e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route("/linebot/admin/get_user_data", methods=["POST"])
@csrf.exempt
def admin_get_user_data():
    """获取单个用户的最新数据"""
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    user_id = data.get('user_id')

    if not user_id:
        return jsonify({
            'success': False,
            'message': 'User ID required'
        }), 400

    try:
        if user_id not in USERS:
            return jsonify({
                'success': False,
                'message': f'User {user_id} not found'
            }), 404

        # 获取用户数据
        user_info = USERS[user_id]

        # 获取昵称(不使用缓存,强制刷新)
        nickname = get_user_nickname_wrapper(user_id, use_cache=False)

        # 格式化 JSON
        json_str = json.dumps(user_info, indent=2, ensure_ascii=False)

        return jsonify({
            'success': True,
            'nickname': nickname,
            'json_str': json_str,
            'user_data': user_info
        })

    except Exception as e:
        logger.error(f"[Admin] ✗ Get user data error: user_id={user_id}, error={e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route("/linebot/admin/load_nicknames", methods=["POST"])
@csrf.exempt
def admin_load_nicknames():
    """批量加载用户昵称"""
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        # 获取所有用户的昵称
        nicknames = {}
        for user_id in USERS.keys():
            nickname = get_user_nickname_wrapper(user_id, use_cache=True)
            nicknames[user_id] = nickname

        return jsonify({
            'success': True,
            'nicknames': nicknames,
            'count': len(nicknames)
        })

    except Exception as e:
        logger.error(f"[Admin] ✗ Load nicknames error: error={e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route("/linebot/admin/get_backups", methods=["GET"])
def admin_get_backups():
    """获取所有备份文件列表"""
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        backup_files = []

        # 扫描备份目录
        if os.path.exists(BACKUP_DIR):
            for filename in os.listdir(BACKUP_DIR):
                if filename.startswith("backup_") and filename.endswith(".zip"):
                    filepath = os.path.join(BACKUP_DIR, filename)
                    stat = os.stat(filepath)

                    backup_files.append({
                        'filename': filename,
                        'size': stat.st_size,
                        'size_mb': round(stat.st_size / (1024 * 1024), 2),
                        'created_at': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                        'timestamp': stat.st_mtime
                    })

        # 按时间倒序排序（最新的在前）
        backup_files.sort(key=lambda x: x['timestamp'], reverse=True)

        return jsonify({
            'success': True,
            'backups': backup_files,
            'count': len(backup_files)
        })

    except Exception as e:
        logger.error(f"[Admin] ✗ Get backups error: error={e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route("/linebot/admin/download_backup", methods=["GET"])
def admin_download_backup():
    """下载指定的备份文件"""
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        filename = request.args.get('file')
        if not filename:
            return jsonify({
                'success': False,
                'message': 'Missing file parameter'
            }), 400

        # 安全检查：只允许备份文件
        if not filename.startswith("backup_") or not filename.endswith(".zip"):
            return jsonify({
                'success': False,
                'message': 'Invalid backup filename'
            }), 400

        # 防止路径遍历攻击
        if ".." in filename or "/" in filename or "\\" in filename:
            return jsonify({
                'success': False,
                'message': 'Invalid filename'
            }), 400

        backup_path = os.path.join(BACKUP_DIR, filename)

        # 检查文件是否存在
        if not os.path.exists(backup_path):
            return jsonify({
                'success': False,
                'message': 'Backup file not found'
            }), 404

        # 发送文件
        return send_file(
            backup_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/zip'
        )

    except Exception as e:
        logger.error(f"[Admin] ✗ Download backup error: file={filename}, error={e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route("/linebot/admin/delete_backup", methods=["POST"])
@csrf.exempt
def admin_delete_backup():
    """删除指定的备份文件"""
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        data = request.get_json()
        filename = data.get('filename')

        if not filename:
            return jsonify({
                'success': False,
                'message': 'Missing filename parameter'
            }), 400

        # 安全检查：只允许备份文件
        if not filename.startswith("backup_") or not filename.endswith(".zip"):
            return jsonify({
                'success': False,
                'message': 'Invalid backup filename'
            }), 400

        # 防止路径遍历攻击
        if ".." in filename or "/" in filename or "\\" in filename:
            return jsonify({
                'success': False,
                'message': 'Invalid filename'
            }), 400

        backup_path = os.path.join(BACKUP_DIR, filename)

        # 检查文件是否存在
        if not os.path.exists(backup_path):
            return jsonify({
                'success': False,
                'message': 'Backup file not found'
            }), 404

        # 删除文件
        os.remove(backup_path)
        logger.info(f"[Admin] ✓ Backup deleted: file={filename}")

        return jsonify({
            'success': True,
            'message': f'Backup {filename} deleted successfully'
        })

    except Exception as e:
        logger.error(f"[Admin] ✗ Delete backup error: error={e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route("/linebot/admin/dxdata_status", methods=["GET"])
def admin_dxdata_status():
    """获取 DXData 状态（歌曲数、谱面数、版本数）"""
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        read_dxdata()
        # 统计歌曲数
        total_songs = len(SONGS)
        std_songs = len([s for s in SONGS if s['type'] == 'std'])
        dx_songs = len([s for s in SONGS if s['type'] == 'dx'])
        utage_songs = len([s for s in SONGS if s['type'] == 'utage'])

        # 统计谱面数（不包括宴会曲）
        total_sheets = 0
        jp_sheets = 0
        intl_sheets = 0

        for song in SONGS:
            if song['type'] == 'utage':
                continue
            for sheet in song['sheets']:
                total_sheets += 1
                if sheet['regions'].get('jp', False):
                    jp_sheets += 1
                if sheet['regions'].get('intl', False):
                    intl_sheets += 1

        # 使用 VERSIONS 全局变量
        total_versions = len(VERSIONS)

        return jsonify({
            'songs': {
                'total': total_songs,
                'std': std_songs,
                'dx': dx_songs,
                'utage': utage_songs
            },
            'sheets': {
                'total': total_sheets,
                'jp': jp_sheets,
                'intl': intl_sheets
            },
            'versions': total_versions
        })

    except Exception as e:
        logger.error(f"[Admin] ✗ DXData status error: error={e}", exc_info=True)
        return jsonify({
            'error': str(e)
        }), 500

# ==================== 开发者 API ====================

@app.route("/api/v1/users", methods=["GET"])
@csrf.exempt
@require_dev_token
def api_list_users():
    """
    获取所有用户列表 API

    需要 Bearer Token 认证

    返回该 token 有权限访问的所有用户（包括创建的用户和授权访问的用户）
    """
    try:
        token_info = request.token_info
        token_id = token_info['token_id']

        # 获取 token 的 allowed_users 列表
        dev_tokens = load_dev_tokens()
        allowed_users = dev_tokens.get(token_id, {}).get('allowed_users', [])

        users_list = []
        for user_id in USERS.keys():
            # 检查是否有访问权限（创建的用户或授权访问的用户）
            has_access = False
            access_type = None

            if 'registered_via_token' in USERS[user_id] and USERS[user_id]['registered_via_token'] == token_id:
                has_access = True
                access_type = "owner"
            elif user_id in allowed_users:
                has_access = True
                access_type = "granted"

            if has_access:
                nickname = get_user_nickname_wrapper(user_id, use_cache=True)
                users_list.append({
                    "user_id": user_id,
                    "nickname": nickname,
                    "access_type": access_type
                })

        # 记录 API 访问日志
        logger.info(f"[API] List users: token_id={token_id}, note={token_info['note']}, count={len(users_list)}")

        return jsonify({
            "success": True,
            "count": len(users_list),
            "users": users_list
        })

    except Exception as e:
        logger.error(f"[API] ✗ List users error: error={e}", exc_info=True)
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500


@app.route("/api/v1/register/<user_id>", methods=["POST"])
@csrf.exempt
@require_dev_token
def api_register_user(user_id):
    """
    用户注册 API - 生成绑定链接

    需要 Bearer Token 认证

    请求体 (JSON):
    - nickname: 必需，用户昵称（如果是LINE用户会自动从LINE API获取，非LINE用户则使用此参数）
    - language: 可选，语言设置 (ja/en/zh)，默认为 en

    返回:
    - bind_url: 绑定页面链接
    - token: 绑定 token（2分钟有效）
    - expires_in: token 过期时间（秒）
    - nickname: 实际使用的昵称
    """
    try:
        # 获取 JSON 数据
        data = request.get_json() or {}
        nickname = data.get('nickname', '')
        language = data.get('language', 'en')

        # nickname 是必需参数
        if not nickname:
            return jsonify({
                "error": "Missing parameter",
                "message": "Parameter 'nickname' is required"
            }), 400

        # 验证 language 参数
        if language not in ['ja', 'en', 'zh']:
            return jsonify({
                "error": "Invalid parameter",
                "message": "Parameter 'language' must be 'ja', 'en', or 'zh'"
            }), 400

        # 记录 API 访问日志
        token_info = request.token_info
        logger.info(f"[API] Register user: user_id={user_id}, nickname={nickname}, language={language}, token_id={token_info['token_id']}, note={token_info['note']}")

        # 读取用户数据
        if user_id in USERS:
            return jsonify({
                "error": "User already exists",
                "message": f"User {user_id} was created already."
            }), 409  # 409 Conflict 更合适

        # 生成绑定 token
        bind_token = generate_bind_token(user_id)

        # 构建绑定 URL
        bind_url = f"https://{DOMAIN}/linebot/sega_bind?token={bind_token}"

        # 初始化用户数据
        add_user(user_id)
        user_set_language(user_id, language)
        edit_user_value(user_id, "nickname", nickname)
        edit_user_value(user_id, "registered_via_token", token_info['token_id'])
        edit_user_value(user_id, "registered_at", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        logger.info(f"[API] ✓ User created: user_id={user_id}, token_id={token_info['token_id']}")

        return jsonify({
            "success": True,
            "user_id": user_id,
            "nickname": nickname,
            "bind_url": bind_url,
            "token": bind_token,
            "expires_in": 120,
            "message": "Bind URL generated successfully. Token expires in 2 minutes."
        })

    except Exception as e:
        logger.error(f"[API] ✗ Register user error: user_id={user_id}, error={e}", exc_info=True)
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500


@app.route("/api/v1/user/<user_id>", methods=["GET"])
@csrf.exempt
@require_dev_token
@require_user_permission
def api_get_user(user_id):
    """
    获取用户信息 API

    需要 Bearer Token 认证并拥有该用户的访问权限
    """
    try:
        user_data = USERS[user_id]
        nickname = get_user_nickname_wrapper(user_id, use_cache=True)

        # 记录 API 访问日志
        token_info = request.token_info
        logger.info(f"[API] Get user: user_id={user_id}, token_id={token_info['token_id']}, note={token_info['note']}")

        return jsonify({
            "success": True,
            "user_id": user_id,
            "nickname": nickname,
            "data": user_data
        })

    except Exception as e:
        logger.error(f"[API] ✗ Get user error: user_id={user_id}, error={e}", exc_info=True)
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500


@app.route("/api/v1/user/<user_id>", methods=["DELETE"])
@csrf.exempt
@require_dev_token
@require_owner_permission
def api_delete_user(user_id):
    """
    删除用户 API

    需要 Bearer Token 认证（该 token 必须是用户的创建者）
    """
    try:
        # 获取用户信息用于日志
        nickname = get_user_nickname_wrapper(user_id, use_cache=True)

        # 删除用户
        delete_user(user_id)

        # 记录 API 访问日志
        token_info = request.token_info
        logger.info(f"[API] Delete user: user_id={user_id}, nickname={nickname}, token_id={token_info['token_id']}, note={token_info['note']}")

        return jsonify({
            "success": True,
            "user_id": user_id,
            "message": f"User {user_id} has been deleted successfully"
        })

    except Exception as e:
        logger.error(f"[API] ✗ Delete user error: user_id={user_id}, error={e}", exc_info=True)
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500


@app.route("/api/v1/perm/<user_id>", methods=["POST"])
@csrf.exempt
@require_dev_token
def api_request_permission(user_id):
    """
    请求访问用户的权限 API

    需要 Bearer Token 认证

    类似好友请求机制，token 发送权限请求后，需要用户同意才能获取访问权限

    请求体 (JSON):
    - requester_name: 可选，请求者名称（用于在通知中显示）

    返回:
    - success: 是否成功发送请求
    - request_id: 请求ID（用于后续接受/拒绝操作）
    - message: 状态信息
    """
    try:
        # 获取 JSON 数据
        data = request.get_json() or {}
        requester_name = data.get('requester_name', '')

        # 获取 token 信息
        token_info = request.token_info
        token_id = token_info['token_id']

        # 如果没有提供 requester_name，使用 token 的 note
        if not requester_name:
            requester_name = token_info.get('note', token_id)

        # 记录 API 访问日志
        logger.info(f"[API] Request permission: target_user_id={user_id}, token_id={token_id}, note={token_info['note']}")

        # 发送权限请求
        result = send_perm_request(token_id, user_id, requester_name)

        if result['success']:
            return jsonify({
                "success": True,
                "request_id": result['request_id'],
                "user_id": user_id,
                "message": result['message']
            })
        else:
            # 根据错误类型返回不同的 HTTP 状态码
            status_code = 404 if result['error'] == "User not found" else 400
            return jsonify({
                "error": result['error'],
                "message": result['message']
            }), status_code

    except Exception as e:
        logger.error(f"[API] ✗ Request permission error: user_id={user_id}, error={e}", exc_info=True)
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500


@app.route("/api/v1/perm/<user_id>/requests", methods=["GET"])
@csrf.exempt
@require_dev_token
@require_owner_permission
def api_get_perm_requests(user_id):
    """
    获取用户的待处理权限请求列表 API

    需要 Bearer Token 认证（该 token 必须是用户的所有者）

    返回:
    - requests: 权限请求列表，包含 request_id, token_id, requester_name, timestamp
    """
    try:
        # 获取待处理的权限请求
        requests = get_pending_perm_requests(user_id)

        # 记录 API 访问日志
        token_info = request.token_info
        logger.info(f"[API] Get permission requests: user_id={user_id}, token_id={token_info['token_id']}, note={token_info['note']}")

        return jsonify({
            "success": True,
            "user_id": user_id,
            "count": len(requests),
            "requests": requests
        })

    except Exception as e:
        logger.error(f"[API] ✗ Get permission requests error: user_id={user_id}, error={e}", exc_info=True)
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500


@app.route("/api/v1/perm/<user_id>/accept", methods=["POST"])
@csrf.exempt
@require_dev_token
@require_owner_permission
def api_accept_perm_request(user_id):
    """
    接受权限请求 API

    需要 Bearer Token 认证（该 token 必须是用户的所有者 token）

    请求体 (JSON):
    - request_id: 必需，要接受的权限请求ID

    返回:
    - success: 是否成功接受
    - token_id: 被授权的 token ID
    - message: 状态信息
    """
    try:
        # 获取 JSON 数据
        data = request.get_json() or {}
        request_id = data.get('request_id', '')

        # request_id 是必需参数
        if not request_id:
            return jsonify({
                "error": "Missing parameter",
                "message": "Parameter 'request_id' is required"
            }), 400

        # 记录 API 访问日志
        token_info = request.token_info
        logger.info(f"[API] Accept permission request: request_id={request_id}, user_id={user_id}, token_id={token_info['token_id']}, note={token_info['note']}")

        # 接受权限请求
        result = accept_perm_request(user_id, request_id)

        if result['success']:
            return jsonify({
                "success": True,
                "user_id": user_id,
                "token_id": result['token_id'],
                "token_note": result['token_note'],
                "message": result['message']
            })
        else:
            # 根据错误类型返回不同的 HTTP 状态码
            status_code = 404 if result['error'] in ["User not found", "Request not found", "Invalid token"] else 400
            return jsonify({
                "error": result['error'],
                "message": result['message']
            }), status_code

    except Exception as e:
        logger.error(f"[API] ✗ Accept permission request error: user_id={user_id}, request_id={request_id}, error={e}", exc_info=True)
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500


@app.route("/api/v1/perm/<user_id>/reject", methods=["POST"])
@csrf.exempt
@require_dev_token
@require_owner_permission
def api_reject_perm_request(user_id):
    """
    拒绝权限请求 API

    需要 Bearer Token 认证（该 token 必须是用户的所有者 token）

    请求体 (JSON):
    - request_id: 必需，要拒绝的权限请求ID

    返回:
    - success: 是否成功拒绝
    - message: 状态信息
    """
    try:
        # 获取 JSON 数据
        data = request.get_json() or {}
        request_id = data.get('request_id', '')

        # request_id 是必需参数
        if not request_id:
            return jsonify({
                "error": "Missing parameter",
                "message": "Parameter 'request_id' is required"
            }), 400

        # 记录 API 访问日志
        token_info = request.token_info
        logger.info(f"[API] Reject permission request: request_id={request_id}, user_id={user_id}, token_id={token_info['token_id']}, note={token_info['note']}")

        # 拒绝权限请求
        result = reject_perm_request(user_id, request_id)

        if result['success']:
            return jsonify({
                "success": True,
                "user_id": user_id,
                "token_id": result['token_id'],
                "token_note": result['token_note'],
                "message": result['message']
            })
        else:
            # 根据错误类型返回不同的 HTTP 状态码
            status_code = 404 if result['error'] in ["User not found", "Request not found"] else 400
            return jsonify({
                "error": result['error'],
                "message": result['message']
            }), status_code

    except Exception as e:
        logger.error(f"[API] ✗ Reject permission request error: user_id={user_id}, request_id={request_id}, error={e}", exc_info=True)
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500


@app.route("/api/v1/perm/<user_id>/revoke", methods=["POST"])
@csrf.exempt
@require_dev_token
@require_owner_permission
def api_revoke_perm(user_id):
    """
    撤销已授予的权限 API

    需要 Bearer Token 认证（该 token 必须是用户的所有者）

    请求体 (JSON):
    - token_id: 必需，要撤销权限的 token ID

    返回:
    - success: 是否成功撤销
    - message: 状态信息
    """
    try:
        # 获取 JSON 数据
        data = request.get_json() or {}
        target_token_id = data.get('token_id', '')

        # token_id 是必需参数
        if not target_token_id:
            return jsonify({
                "error": "Missing parameter",
                "message": "Parameter 'token_id' is required"
            }), 400

        # 记录 API 访问日志
        token_info = request.token_info
        logger.info(f"[API] Revoke permission: target_token_id={target_token_id}, user_id={user_id}, token_id={token_info['token_id']}, note={token_info['note']}")

        # 加载 dev tokens
        dev_tokens = load_dev_tokens()

        if target_token_id not in dev_tokens:
            return jsonify({
                "error": "Token not found",
                "message": f"Token {target_token_id} does not exist"
            }), 404

        # 从 allowed_users 列表中移除该用户
        allowed_users = dev_tokens[target_token_id].get('allowed_users', [])
        if user_id in allowed_users:
            allowed_users.remove(user_id)
            dev_tokens[target_token_id]['allowed_users'] = allowed_users
            save_dev_tokens(dev_tokens)

            return jsonify({
                "success": True,
                "user_id": user_id,
                "token_id": target_token_id,
                "message": f"Permission revoked for token {target_token_id}"
            })
        else:
            return jsonify({
                "error": "Permission not found",
                "message": f"Token {target_token_id} does not have permission to access user {user_id}"
            }), 404

    except Exception as e:
        logger.error(f"[API] ✗ Revoke permission error: user_id={user_id}, target_token_id={target_token_id}, error={e}", exc_info=True)
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500


@app.route("/api/v1/task/<task_id>", methods=["GET"])
@csrf.exempt
@require_dev_token
def api_get_task_status(task_id):
    """
    查询任务状态 API

    需要 Bearer Token 认证

    返回指定任务的状态信息（running, queued, completed, 或 not_found）
    """
    try:
        with task_tracking_lock:
            # 检查任务是否在运行中
            for task in task_tracking['running']:
                if task.get('id') == task_id:
                    return jsonify({
                        "success": True,
                        "task_id": task_id,
                        "status": "running",
                        "start_time": task.get('start_time'),
                        "task_type": task.get('type', 'unknown')
                    })

            # 检查任务是否在队列中
            for task in task_tracking['queued']:
                if task.get('id') == task_id:
                    return jsonify({
                        "success": True,
                        "task_id": task_id,
                        "status": "queued",
                        "queued_time": task.get('queued_time'),
                        "task_type": task.get('type', 'unknown'),
                        "queue_position": task_tracking['queued'].index(task) + 1
                    })

            # 检查任务是否已完成
            for task in task_tracking['completed']:
                if task.get('id') == task_id:
                    return jsonify({
                        "success": True,
                        "task_id": task_id,
                        "status": "completed",
                        "start_time": task.get('start_time'),
                        "end_time": task.get('end_time'),
                        "duration": task.get('duration'),
                        "task_type": task.get('type', 'unknown'),
                        "result": task.get('result', 'success')
                    })

            # 检查任务是否已被取消
            if task_id in task_tracking['cancelled']:
                return jsonify({
                    "success": True,
                    "task_id": task_id,
                    "status": "cancelled"
                })

        # 任务不存在
        return jsonify({
            "success": False,
            "task_id": task_id,
            "status": "not_found",
            "message": "Task not found or expired"
        }), 404

    except Exception as e:
        logger.error(f"[API] ✗ Get task status error: task_id={task_id}, error={e}", exc_info=True)
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500

@app.route("/api/v1/update/<user_id>", methods=["POST"])
@csrf.exempt
@require_dev_token
@require_user_permission
def api_update_user(user_id):
    """
    触发用户数据更新 API

    需要 Bearer Token 认证并拥有该用户的访问权限

    将用户加入更新队列，异步执行数据更新
    """
    try:
        # 检查用户是否已绑定账号
        if 'sega_id' not in USERS[user_id] or 'sega_pwd' not in USERS[user_id]:
            return jsonify({
                "error": "Account not bound",
                "message": f"User {user_id} has not bound a SEGA account"
            }), 400

        # 创建模拟事件对象用于更新任务
        class MockEvent:
            def __init__(self, user_id):
                self.source = type('obj', (object,), {'user_id': user_id})()
                self.reply_token = None  # API 调用不需要回复

        mock_event = MockEvent(user_id)

        # 生成任务ID
        task_id = f"api_update_{secrets.token_hex(8)}"

        # 将更新任务加入队列
        try:
            webtask_queue.put_nowait((async_maimai_update_task, (mock_event,), task_id))

            # 记录 API 访问日志
            token_info = request.token_info
            logger.info(f"[API] ✓ Update triggered: user_id={user_id}, task_id={task_id}, token_id={token_info['token_id']}, note={token_info['note']}")

            return jsonify({
                "success": True,
                "message": "Update task queued successfully",
                "user_id": user_id,
                "task_id": task_id,
                "queue_size": webtask_queue.qsize()
            })

        except queue.Full:
            return jsonify({
                "error": "Queue full",
                "message": "Update queue is full, please try again later",
                "queue_size": webtask_queue.qsize()
            }), 503

    except Exception as e:
        logger.error(f"[API] ✗ Update user error: user_id={user_id}, error={e}", exc_info=True)
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500

@app.route("/api/v1/records/<user_id>", methods=["GET"])
@csrf.exempt
@require_dev_token
@require_user_permission
def api_get_records(user_id):
    """
    获取用户成绩记录 API

    需要 Bearer Token 认证并拥有该用户的访问权限

    参数:
    - type: 可选，记录类型，默认为 best50
      可选值: best50, best100, best35, best15, allb50, allb100, allb200, allb35, apb50, rct50, idealb50, UNKNOWN
    - command: 可选，过滤命令，如 "-lv 14 15 -ra 100 200"
    """
    try:
        # 获取查询参数
        record_type = request.args.get('type', 'best50')
        command = request.args.get('command', '')

        # 记录 API 访问日志
        token_info = request.token_info
        logger.info(f"[API] Get records: user_id={user_id}, type={record_type}, token_id={token_info['token_id']}, note={token_info['note']}")

        # 验证 record_type
        valid_types = ["best50", "best100", "best35", "best15", "allb50", "allb100", "allb200", "allb35", "apb50", "rct50", "idealb50", "UNKNOWN"]
        if record_type not in valid_types:
            return jsonify({
                "error": "Invalid type",
                "message": f"Invalid record type: {record_type}. Valid types: {', '.join(valid_types)}"
            }), 400

        # 检查是否有个人信息
        if "personal_info" not in USERS[user_id]:
            return jsonify({
                "error": "User info not found",
                "message": f"User {user_id} has no personal info, please update first"
            }), 400

        # 获取用户版本
        ver = USERS[user_id].get('version', 'jp')

        # 读取用户记录
        recent = (record_type == "rct50")
        song_record = read_record(user_id, recent=recent)
        if not len(song_record):
            return jsonify({
                "error": "No records found",
                "message": f"User {user_id} has no score records"
            }), 404

        # 调用 select_records 函数获取筛选后的记录
        up_songs, down_songs = select_records(song_record, record_type, command, ver)

        if not up_songs and not down_songs:
            return jsonify({
                "success": True,
                "count": 0,
                "old_songs": [],
                "new_songs": [],
                "message": "No records match the criteria"
            })

        return jsonify({
            "success": True,
            "user_id": user_id,
            "type": record_type,
            "count": len(up_songs) + len(down_songs),
            "old_songs": up_songs,
            "new_songs": down_songs
        })

    except Exception as e:
        logger.error(f"[API] ✗ Get records error: user_id={user_id}, error={e}", exc_info=True)
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500


@app.route("/api/v1/search", methods=["GET"])
@csrf.exempt
@require_dev_token
def api_search_songs():
    """
    搜索歌曲 API

    需要 Bearer Token 认证

    参数:
    - q: 可选，搜索关键词，如果不提供或使用 __empty__ 则搜索空字符串
    - ver: 可选，服务器版本 (jp/intl)，默认为 jp
    - max_results: 可选，最大结果数，默认为 6
    """
    try:
        # 获取查询参数，允许空字符串
        query = request.args.get('q', '')
        user_id = request.args.get('user_id')
        max_results = request.args.get('max_results', MAX_SEARCH_RESULTS, type=int)

        # 处理特殊占位符
        if query == '__empty__':
            query = ''
        
        token_info = request.token_info

        if not user_id:
            ver = request.args.get('ver', 'jp')
        else:
            # 使用辅助函数检查权限
            has_permission, error_response = check_user_permission(user_id, token_info['token_id'])
            if not has_permission:
                return error_response

            # 检查是否有个人信息
            if "personal_info" not in USERS[user_id]:
                return jsonify({
                    "error": "User info not found",
                    "message": f"User {user_id} has no personal info, please update first"
                }), 400

            ver = get_user_value(user_id, "version")

        if ver not in ['jp', 'intl']:
            return jsonify({
                "error": "Invalid parameter",
                "message": "Parameter 'ver' must be 'jp' or 'intl'"
            }), 400

        # 记录 API 访问日志
        logger.info(f"[API] Search songs: query='{query}', token_id={token_info['token_id']}, note={token_info['note']}")

        # 读取歌曲数据
        read_dxdata(ver)

        # 使用优化的歌曲匹配函数
        matching_songs = find_matching_songs(query, SONGS, max_results=max_results, threshold=0.85)

        # 检查结果
        if not matching_songs:
            return jsonify({
                "success": True,
                "count": 0,
                "songs": [],
                "message": "No songs found"
            })

        if len(matching_songs) > max_results:
            return jsonify({
                "error": "Too many results",
                "message": f"Found {len(matching_songs)} songs, please refine your search (max: {max_results})",
                "count": len(matching_songs)
            }), 400

        if not user_id:
            return jsonify({
                "success": True,
                "count": len(matching_songs),
                "query": query,
                "ver": ver,
                "songs": matching_songs
            })


        song_record = read_record(user_id)
        result = []
        
        # 对每首匹配的歌曲,查找用户的游玩记录
        for song in matching_songs:
            played_data = []

            # 使用优化的精确匹配函数
            for rcd in song_record:
                if is_exact_song_match(rcd['cover_name'], song['cover_name']) and rcd['type'] == song['type']:
                    rcd['rank'] = ""
                    played_data.append(rcd)

            if played_data:
                result.append(played_data)
                
        if not result:
            return jsonify({
                "success": True,
                "count": 0,
                "records": [],
                "message": "No records found"
            })

        if len(result) > max_results:
            return jsonify({
                "error": "Too many results",
                "message": f"Found {len(result)} songs, please refine your search (max: {max_results})",
                "count": len(result)
            }), 400

        return jsonify({
            "success": True,
            "count": len(result),
            "query": query,
            "ver": ver,
            "records": result
        })


    except Exception as e:
        logger.error(f"[API] ✗ Search songs error: query='{query}', error={e}", exc_info=True)
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500


@app.route("/api/v1/versions", methods=["GET"])
@csrf.exempt
@require_dev_token
def api_get_versions():
    """
    获取版本信息 API

    需要 Bearer Token 认证

    返回 maimai DX 的版本信息

    示例:
    curl -H "Authorization: Bearer <your_token>" https://your-domain.com/api/v1/versions
    """
    try:
        # 记录 API 访问日志
        token_info = request.token_info
        logger.info(f"[API] Get versions: token_id={token_info['token_id']}, note={token_info['note']}")

        read_dxdata()

        return jsonify({
            "success": True,
            "versions": VERSIONS
        })

    except Exception as e:
        logger.error(f"[API] ✗ Get versions error: error={e}", exc_info=True)
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500

if __name__ == "__main__":
    # ==================== 系统启动自检 ====================
    # 在启动 worker 线程之前执行系统自检
    logger.info("=" * 60)
    logger.info("[System] → Starting JiETNG Maimai DX LINE Bot...")
    logger.info("=" * 60)

    try:
        # 读取用户数据
        logger.info("[System] → Loading user list...")
        load_user()

        # 加载 tip/ad 数据
        logger.info("[System] → Loading tip/ad data...")
        load_tip_ad_data()

        system_check_results = run_system_check()

        # 如果有关键问题，显示警告
        if system_check_results["overall_status"] == "WARNING":
            logger.info("[System] ⚠ System check found some issues")
            logger.info("[System] → Check logs for details")
        else:
            logger.info("[System] ✓ System check passed")

    except Exception as e:
        logger.info(f"[System] ⚠ System check failed: error={e}")
        logger.info("[System] → Continuing startup anyway...")

    # 启动 worker 线程
    for i in range(MAX_CONCURRENT_IMAGE_TASKS):
        threading.Thread(target=image_worker, daemon=True, name=f"ImageWorker-{i+1}").start()

    for i in range(WEB_MAX_CONCURRENT_TASKS):
        threading.Thread(target=webtask_worker, daemon=True, name=f"WebTaskWorker-{i+1}").start()

    logger.info(f"[System] ✓ Workers started: image={MAX_CONCURRENT_IMAGE_TASKS}, web={WEB_MAX_CONCURRENT_TASKS}")

    # 启动内存管理器
    memory_manager.start()
    logger.info("[System] ✓ Memory manager started")

    # 注册清理函数（在内存管理器的清理循环中调用）
    def custom_cleanup():
        """自定义清理函数"""
        try:
            # 清理用户昵称缓存
            cleaned_nicknames = cleanup_user_caches(user_manager_module)

            # 清理频率限制追踪数据
            cleaned_rate_limits = cleanup_rate_limiter_tracking(rate_limiter_module)

            # 清理未绑定的用户（没有 sega_id 或 sega_pwd）
            cleanup_result = clean_unbound_users()
            cleaned_unbound_users = cleanup_result.get('deleted_count', 0)

            logger.info(f"[System] ✓ Custom cleanup completed: nicknames={cleaned_nicknames}, rate_limits={cleaned_rate_limits}, unbound_users={cleaned_unbound_users}")
        except Exception as e:
            logger.error(f"[System] ✗ Custom cleanup error: error={e}", exc_info=True)

    # 覆盖内存管理器的cleanup方法，加入自定义清理
    original_cleanup = memory_manager.cleanup
    def enhanced_cleanup():
        stats = original_cleanup()
        custom_cleanup()
        return stats
    memory_manager.cleanup = enhanced_cleanup

    try:
        app.run(host="0.0.0.0", port=PORT)
    finally:
        # 停止内存管理器
        memory_manager.stop()
        logger.info("[System] Memory manager stopped")
