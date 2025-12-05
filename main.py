"""
JiETNG Maimai DX LINE Bot 主程序
"""

import gc
import random
import requests
import json
import re
import traceback
import math
import difflib
import numpy
import threading
import queue
import textwrap
import logging
import psutil
import platform
import socket
import secrets
import hashlib
import copy
import asyncio

from datetime import datetime, timedelta
from typing import List, Optional, Any

from PIL import Image, ImageDraw
from io import BytesIO

from pyzbar.pyzbar import decode
from urllib.parse import urlparse

from flask import (
    Flask,
    request,
    abort,
    render_template,
    redirect,
    session,
    jsonify,
    make_response
)
from flask_wtf.csrf import CSRFProtect

from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    MessagingApiBlob,
    ReplyMessageRequest,
    PushMessageRequest,
    TextMessage,
    ImageMessage,
    TemplateMessage,
    ButtonsTemplate,
    MessageAction,
    URIAction
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
    ImageMessageContent,
    LocationMessageContent
)

# Song and record generators
from modules.song_generator import song_info_generate, generate_version_list
from modules.record_generator import *

# User and data managers
from modules.user_manager import *
from modules.token_manager import generate_token, get_user_id_from_token
from modules.notice_manager import *
from modules.maimai_manager import *
from modules.dxdata_manager import update_dxdata_with_comparison
from modules.record_manager import *

# Config loader
from modules.config_loader import *

# UI and message modules
from modules.message_manager import *
from modules.friendlist_generator import generate_friend_buttons

# Image processing
from modules.image_uploader import smart_upload
from modules.image_manager import *
from modules.image_matcher import find_song_by_cover

# System utilities
from modules.system_checker import run_system_check
from modules.rate_limiter import check_rate_limit
from modules.line_messenger import smart_reply, smart_push, notify_admins_error
from modules.song_matcher import find_matching_songs, is_exact_song_match
from modules.memory_manager import memory_manager, cleanup_user_caches, cleanup_rate_limiter_tracking

# Module aliases for specific use cases
import modules.user_manager as user_manager_module
import modules.rate_limiter as rate_limiter_module

# ==================== 常量定义 ====================

# 分隔线
DIVIDER = "-" * 33

# 队列配置
MAX_QUEUE_SIZE = 10
MAX_CONCURRENT_IMAGE_TASKS = 3  # 图片生成并发数
WEB_MAX_CONCURRENT_TASKS = 1    # 网络任务并发数
TASK_TIMEOUT_SECONDS = 120

# 搜索结果限制
MAX_SEARCH_RESULTS = 5

# Rating计算范围
RC_SCORE_MIN = 97.0000
RC_SCORE_MAX = 100.5001
RC_SCORE_STEP = 0.0001

ERROR_NOTIFICATION_ENABLED = True  # 是否启用错误通知

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

app = Flask(__name__)
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

# 图片生成任务队列 (处理图片生成任务，如 b50, yang rating 等)
image_queue = queue.Queue(maxsize=MAX_QUEUE_SIZE)
image_concurrency_limit = threading.Semaphore(MAX_CONCURRENT_IMAGE_TASKS)

# Web任务队列 (处理耗时的网络请求，如 maimai_update 等)
webtask_queue = queue.Queue(maxsize=MAX_QUEUE_SIZE)
webtask_concurrency_limit = threading.Semaphore(WEB_MAX_CONCURRENT_TASKS)

# 缓存生成任务队列 (处理定数表缓存生成等后台任务)
cache_queue = queue.Queue(maxsize=5)  # 缓存任务通常较少，队列较小
cache_concurrency_limit = threading.Semaphore(1)  # 同时只允许1个缓存任务

# 缓存生成进度跟踪
cache_generation_progress = {
    "status": "idle",  # idle, running, completed, error
    "current_server": "",  # jp, intl
    "current_level": "",  # 12, 12+, 13, etc.
    "progress": 0,  # 0-100
    "total_levels": 0,
    "completed_levels": 0,
    "error_message": "",
    "start_time": None,
    "end_time": None
}


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
                logger.info(f"Task {task_id} was cancelled, skipping execution")
                q.task_done()
                return

    # 添加到运行中的任务
    if task_id:
        with task_tracking_lock:
            # 从排队中移除
            task_tracking['queued'] = [t for t in task_tracking['queued'] if t.get('id') != task_id]
            # 添加到运行中
            task_info = {
                'id': task_id,
                'function': func.__name__,
                'start_time': start_time.strftime('%Y-%m-%d %H:%M:%S'),
                'user_id': args[0].source.user_id if hasattr(args[0], 'source') else 'Unknown'
            }
            task_tracking['running'].append(task_info)

    with sem:
        task_done = threading.Event()

        def target():
            try:
                func(*args)
            except Exception as e:
                logger.error(f"Task execution error: {e}", exc_info=True)

                # 尝试获取用户信息以便回复
                user_id = None
                reply_token = None
                if args and hasattr(args[0], 'source') and hasattr(args[0], 'reply_token'):
                    user_id = args[0].source.user_id
                    reply_token = args[0].reply_token

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
            logger.info(f"Task completed: {func.__name__}, Total: {STATS['tasks_processed']}, Avg: {STATS['response_time']/STATS['tasks_processed']:.1f}ms")

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
            logger.error(f"Image task worker error: {e}", exc_info=True)
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
            logger.error(f"Web task worker error: {e}", exc_info=True)
            notify_admins_error(
                error_title="Web Task Worker Error",
                error_details=f"{type(e).__name__}: {str(e)}\n\n{traceback.format_exc()}",
                context={"Worker": "webtask_worker"},
                admin_id=ADMIN_ID,
                configuration=configuration,
                error_notification_enabled=ERROR_NOTIFICATION_ENABLED
            )
            webtask_queue.task_done()


def cache_worker() -> None:
    """缓存生成任务队列的工作线程"""
    while True:
        try:
            item = cache_queue.get()
            func, args = item
            run_task_with_limit(func, args, cache_concurrency_limit, cache_queue, None, False)
        except Exception as e:
            logger.error(f"Cache task worker error: {e}", exc_info=True)
            with stats_lock:
                cache_generation_progress["status"] = "error"
                cache_generation_progress["error_message"] = str(e)
                cache_generation_progress["end_time"] = datetime.now().isoformat()
            cache_queue.task_done()


# ==================== 系统启动自检 ====================
# 在启动 worker 线程之前执行系统自检
print("\n" + "=" * 60)
print("JiETNG Maimai DX LINE Bot Starting...")
print("=" * 60)

try:
    system_check_results = run_system_check()

    # 如果有关键问题，显示警告
    if system_check_results["overall_status"] == "WARNING":
        print("\n⚠️  WARNING: System check found some issues")
        print("   Check logs for details\n")
    else:
        print("\n✓ System check passed\n")

except Exception as e:
    print(f"\n⚠️  System check failed: {e}")
    print("   Continuing startup anyway...\n")

# 启动 worker 线程
for i in range(MAX_CONCURRENT_IMAGE_TASKS):
    threading.Thread(target=image_worker, daemon=True, name=f"ImageWorker-{i+1}").start()

for i in range(WEB_MAX_CONCURRENT_TASKS):
    threading.Thread(target=webtask_worker, daemon=True, name=f"WebTaskWorker-{i+1}").start()

# 启动缓存生成 worker（只需1个）
threading.Thread(target=cache_worker, daemon=True, name="CacheWorker-1").start()

print(f"Started {MAX_CONCURRENT_IMAGE_TASKS} image workers, {WEB_MAX_CONCURRENT_TASKS} web task workers, and 1 cache worker")
print("=" * 60 + "\n")


def cancel_if_timeout(task_done: threading.Event) -> None:
    """
    检查任务是否超时

    Args:
        task_done: 任务完成事件
    """
    if not task_done.is_set():
        logger.warning("Task execution timeout")

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
    from functools import wraps

    @wraps(f)
    def decorated_function(*args, **kwargs):
        from modules.devtoken_manager import verify_dev_token

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
    from functools import wraps

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
        read_user()

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
    from functools import wraps

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
        read_user()
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
    from modules.devtoken_manager import load_dev_tokens

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
    logger.info("Received webhook request")

    try:
        json_data = json.loads(body)
        destination = json_data.get("destination")
        request.destination = destination
        handler.handle(body, signature)

    except json.JSONDecodeError as e:
        logger.error(f"JSON parse failed: {e}")
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
        logger.error(f"LINE signature verification failed: {e}")
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
        logger.error(f"Webhook handling error: {e}", exc_info=True)
        notify_admins_error(
            error_title="Webhook Handling Error",
            error_details=f"{type(e).__name__}: {str(e)}\n\n{traceback.format_exc()}",
            context={"Event": "Webhook"},
            admin_id=ADMIN_ID,
            configuration=configuration,
            error_notification_enabled=ERROR_NOTIFICATION_ENABLED
        )
        abort(500)

    gc.collect()
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
        logger.error(f"Token verification failed: {e}")
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

        result = process_sega_credentials(user_id, segaid, password, user_version, user_language)
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


def process_sega_credentials(user_id, segaid, password, ver="jp", language="ja"):
    base = (
        "https://maimaidx-eng.com/maimai-mobile"
        if ver == "intl"
        else "https://maimaidx.jp/maimai-mobile"
    )

    session = login_to_maimai(segaid, password, ver=ver)
    if session == "MAINTENANCE":
        return "MAINTENANCE"
    if fetch_dom(session, f"{base}/home/") is None:
        return False

    user_bind_sega_id(user_id, segaid)
    user_bind_sega_pwd(user_id, password)
    user_set_version(user_id, ver)
    user_set_language(user_id, language)
    if "registered_via_token" not in USERS[user_id]:
        smart_push(user_id, bind_msg(user_id), configuration)
    return True



# ==================== 用户管理函数 ====================

def user_bind_sega_id(user_id, sega_id):
    read_user()

    if user_id not in USERS :
        add_user(user_id)

    edit_user_value(user_id, 'sega_id', sega_id)

def user_bind_sega_pwd(user_id, sega_pwd):
    read_user()

    if user_id not in USERS :
        add_user(user_id)

    edit_user_value(user_id, 'sega_pwd', sega_pwd)

def user_set_version(user_id, version):
    read_user()

    if user_id not in USERS :
        add_user(user_id)

    edit_user_value(user_id, 'version', version)

def user_set_language(user_id, language):
    read_user()

    if user_id not in USERS :
        add_user(user_id)

    edit_user_value(user_id, 'language', language)

def get_user(user_id):
    read_user()

    from modules.message_manager import get_user_language, get_multilingual_text

    # 多语言文本
    texts = {
        'title': {
            'ja': '👤 ユーザー情報',
            'en': '👤 User Information',
            'zh': '👤 用户信息'
        },
        'user_id': {
            'ja': 'LINE ID',
            'en': 'LINE ID',
            'zh': 'LINE ID'
        },
        'name': {
            'ja': 'プレイヤー名',
            'en': 'Player Name',
            'zh': '玩家名称'
        },
        'rating': {
            'ja': 'レーティング',
            'en': 'Rating',
            'zh': 'Rating'
        },
        'sega_id': {
            'ja': 'SEGA ID',
            'en': 'SEGA ID',
            'zh': 'SEGA ID'
        },
        'password': {
            'ja': 'パスワード',
            'en': 'Password',
            'zh': '密码'
        },
        'server': {
            'ja': 'サーバー',
            'en': 'Server',
            'zh': '服务器'
        },
        'language': {
            'ja': '言語',
            'en': 'Language',
            'zh': '语言'
        },
        'bound': {
            'ja': '連携済み',
            'en': 'Bound',
            'zh': '已绑定'
        },
        'not_bound': {
            'ja': '未連携',
            'en': 'Not Bound',
            'zh': '未绑定'
        },
        'jp_server': {
            'ja': '日本版',
            'en': 'Japanese Server',
            'zh': '日服'
        },
        'intl_server': {
            'ja': '海外版',
            'en': 'International Server',
            'zh': '国际服'
        },
        'lang_ja': {
            'ja': '日本語',
            'en': 'Japanese',
            'zh': '日语'
        },
        'lang_en': {
            'ja': '英語',
            'en': 'English',
            'zh': '英语'
        },
        'lang_zh': {
            'ja': '中国語',
            'en': 'Chinese',
            'zh': '中文'
        }
    }

    # 获取用户语言
    lang = get_user_language(user_id)

    # 构建输出
    result = f"{'='*30}\n"
    result += f"{get_multilingual_text(texts['title'], language=lang)}\n"
    result += f"{'='*30}\n\n"

    if user_id in USERS:
        user_data = USERS[user_id]

        # 基本信息
        result += f"📱 {get_multilingual_text(texts['user_id'], language=lang)}: {user_id}\n\n"

        # 玩家信息
        if "personal_info" in user_data:
            personal_info = user_data['personal_info']
            if 'name' in personal_info:
                result += f"🎮 {get_multilingual_text(texts['name'], language=lang)}: {personal_info['name']}\n"
            if 'rating' in personal_info:
                result += f"⭐ {get_multilingual_text(texts['rating'], language=lang)}: {personal_info['rating']}\n"
            result += "\n"

        # SEGA账号信息
        if "sega_id" in user_data:
            result += f"🔑 {get_multilingual_text(texts['sega_id'], language=lang)}: {user_data['sega_id']}\n"
        else:
            result += f"🔑 {get_multilingual_text(texts['sega_id'], language=lang)}: {get_multilingual_text(texts['not_bound'], language=lang)}\n"

        if "sega_pwd" in user_data:
            result += f"🔐 {get_multilingual_text(texts['password'], language=lang)}: {get_multilingual_text(texts['bound'], language=lang)}\n"
        else:
            result += f"🔐 {get_multilingual_text(texts['password'], language=lang)}: {get_multilingual_text(texts['not_bound'], language=lang)}\n"

        result += "\n"

        # 服务器版本
        if "version" in user_data:
            server_text = texts['jp_server'] if user_data['version'] == 'jp' else texts['intl_server']
            result += f"🌐 {get_multilingual_text(texts['server'], language=lang)}: {get_multilingual_text(server_text, language=lang)}\n"

        # 语言设置
        lang_display = {
            'ja': texts['lang_ja'],
            'en': texts['lang_en'],
            'zh': texts['lang_zh']
        }.get(lang, texts['lang_ja'])
        result += f"🌍 {get_multilingual_text(texts['language'], language=lang)}: {get_multilingual_text(lang_display, language=lang)}\n"

    else:
        result += f"📱 {get_multilingual_text(texts['user_id'], language=lang)}: {user_id}\n\n"
        result += f"❌ {get_multilingual_text(texts['not_bound'], language=lang)}\n"

    result += f"\n{'='*30}"

    return result


# ==================== 异步任务处理函数 ====================

def async_maimai_update_task(event):
    """异步maimai更新任务 - 在webtask_queue中执行"""
    user_id = event.source.user_id
    reply_token = event.reply_token

    # 获取用户版本
    read_user()
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
    read_user()
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
    read_user()
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
            logger.error(f"Failed to notify admin: {e}")

# ==================== 主程序入口 ====================

def maimai_update(user_id, ver="jp"):
    messages = []
    func_status = {
        "User Info": True,
        "Best Records": True,
        "Recent Records": True,
        "Friends List": True
    }

    read_user()

    if user_id not in USERS:
        return segaid_error(user_id)

    elif 'sega_id' not in USERS[user_id] or 'sega_pwd' not in USERS[user_id]:
        return segaid_error(user_id)

    sega_id = USERS[user_id]['sega_id']
    sega_pwd = USERS[user_id]['sega_pwd']

    user_session = login_to_maimai(sega_id, sega_pwd, ver)
    if user_session == None:
        return segaid_error(user_id)
    if user_session == "MAINTENANCE":
        return maintenance_error(user_id)

    # 使用异步函数并发获取所有数据
    cookies = user_session.cookies.get_dict()

    async def fetch_all_data():
        return await asyncio.gather(
            get_maimai_info_async(cookies, ver),
            get_maimai_records_async(cookies, ver),
            get_recent_records_async(cookies, ver),
            get_friends_list_async(cookies, ver)
        )

    user_info, maimai_records, recent_records, friends_list = asyncio.run(fetch_all_data())

    if (user_info == "MAINTENANCE" or
        maimai_records == "MAINTENANCE" or
        recent_records == "MAINTENANCE" or
        friends_list == "MAINTENANCE"):
        return maintenance_error(user_id)

    error = False

    if user_info:
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

    details = "詳しい情報："
    for func, status in func_status.items():
        details += f"\n「{func}」Error" if not status else ""

    if not error:
        messages.append(update_over(user_id))
    else:
        messages.append(update_error(user_id))
        messages.append(TextMessage(text=details))

    return messages

def get_rc(level: float) -> str:
    """
    生成指定难度的Rating对照表

    Args:
        level: 谱面定数 (如 14.5)

    Returns:
        格式化的Rating对照表字符串,显示不同达成率对应的Rating值
    """
    result = f"LEVEL: {level}\n"
    result += DIVIDER
    last_ra = 0

    for score in numpy.arange(RC_SCORE_MIN, RC_SCORE_MAX, RC_SCORE_STEP):
        ra = get_single_ra(level, score)
        if ra != last_ra:
            result += f"\n{format(score, '.4f')}% \t-\t {ra}"
            last_ra = ra

    return result

def search_song(user_id, acronym, ver="jp"):
    """
    搜索歌曲并返回歌曲信息图片

    Args:
        acronym: 搜索关键词
        ver: 服务器版本 (jp/intl)

    Returns:
        搜索结果消息列表 (最多6个) 或错误消息
    """
    read_dxdata(ver)

    # 使用优化的歌曲匹配函数
    matching_songs = find_matching_songs(acronym, SONGS, max_results=6, threshold=0.85)

    # 没有匹配结果
    if not matching_songs or len(matching_songs) > MAX_SEARCH_RESULTS:
        return song_error(user_id)

    # 生成消息列表
    result = []
    for song in matching_songs:
        original_url, preview_url = smart_upload(song_info_generate(song))
        message = ImageMessage(original_content_url=original_url, preview_image_url=preview_url)
        result.append(message)

    return result

def random_song(user_id, key="", ver="jp"):
    read_dxdata(ver)
    length = len(SONGS)
    is_exit = False
    valid_songs = []

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

    original_url, preview_url = smart_upload(song_info_generate(song))
    result = ImageMessage(original_content_url=original_url, preview_image_url=preview_url)

    return result

def get_friend_list(user_id):
    read_user()
    if user_id not in USERS:
        return segaid_error(user_id)

    elif 'mai_friends' not in USERS[user_id]:
        return friend_error(user_id)

    friends_list = copy.deepcopy(get_user_value(user_id, "mai_friends"))
    if not friends_list:
        friends_list = []

    return generate_friend_buttons(user_id, get_friend_list_alt_text(user_id), format_favorite_friends(friends_list))

def get_song_record(user_id, acronym, ver="jp"):
    """
    查询用户在特定歌曲上的游玩记录

    Args:
        user_id: 用户ID
        acronym: 歌曲搜索关键词
        ver: 服务器版本 (jp/intl)

    Returns:
        包含用户成绩的歌曲信息图片消息列表 或错误消息
    """
    read_dxdata(ver)

    song_record = read_record(user_id)

    if not len(song_record):
        return record_error(user_id)

    # 使用优化的歌曲匹配函数
    matching_songs = find_matching_songs(acronym, SONGS, max_results=6, threshold=0.85)

    if not matching_songs:
        return song_error(user_id)

    result = []

    # 对每首匹配的歌曲,查找用户的游玩记录
    for song in matching_songs:
        played_data = []

        # 使用优化的精确匹配函数
        for rcd in song_record:
            if is_exact_song_match(rcd['cover_name'], song['cover_name']) and rcd['type'] == song['type']:
                rcd['rank'] = ""
                played_data.append(rcd)

        # 如果该歌曲没有游玩记录,跳过
        if not played_data:
            continue

        original_url, preview_url = smart_upload(song_info_generate(song, played_data))
        message = ImageMessage(original_content_url=original_url, preview_image_url=preview_url)
        result.append(message)

    # 没有找到任何有记录的歌曲,或结果过多
    if len(result) == 0 or len(result) > 6:
        result = song_error(user_id)

    return result

def generate_plate_rcd(user_id, title, ver="jp"):
    if not (len(title) == 2 or len(title) == 3):
        return plate_error(user_id)

    read_user()
    read_dxdata(ver)

    song_record = read_record(user_id)

    if not len(song_record):
        return record_error(user_id)

    if "personal_info" not in USERS[user_id]:
        return info_error(user_id)

    version_name = title[0]
    plate_type = title[1:]

    target_version = []
    target_icon = []
    target_type = ""

    for version in VERSIONS :
        if version_name in version['abbr'] :
            target_version.append(version['version'])

    if not len(target_version) :
        return version_error(user_id)

    if plate_type in ["極", "极"] :
        target_type = "combo"
        target_icon = ["fc", "fcp", "ap", "app"]

    elif plate_type == "将" :
        target_type = "score"
        target_icon = ["sss", "sssp"]

    elif plate_type == "神" :
        target_type = "combo"
        target_icon = ["ap", "app"]

    elif plate_type == "舞舞" :
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
    from modules.song_matcher import normalize_text

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

    for song in SONGS :
        if song['version'] not in target_version or song['type'] == 'utage':
            continue

        for sheet in song['sheets'] :
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

            if sheet['difficulty'] == "master" :
                target_data.append({"img": generate_cover(song['cover_url'], song_type, icon, target_type, cover_name=song.get('cover_name')), "level": sheet['level']})

    img = generate_plate_image(target_data, title, headers = target_num)

    # 获取用户信息并创建用户信息图片
    user_info = USERS[user_id]['personal_info']
    img = compose_images([create_user_info_img(user_info), img])

    original_url, preview_url = smart_upload(img)
    message = ImageMessage(original_content_url=original_url, preview_image_url=preview_url)

    return message

def generate_internallevel_songs(user_id, level, ver="jp"):
    """
    生成指定定数范围的歌曲列表图片

    参数:
        level: 难度等级（如 "13", "13+", "14", "14+"）
        ver: 服务器版本（"jp" 或 "intl"）
    """
    import os
    from modules.message_manager import song_error, level_not_supported, cache_not_found

    read_dxdata(ver)

    # 验证 level 参数
    valid_levels = ["10", "10+", "11", "11+", "12", "12+", "13", "13+", "14", "14+", "15"]
    if level not in valid_levels:
        return song_error(user_id)

    # 检查等级是否支持（只支持12及以上）
    supported_levels = ["12", "12+", "13", "13+", "14", "14+", "15"]
    if level not in supported_levels:
        return level_not_supported(user_id)

    # 检查缓存
    cache_filename = f"{ver}_{level.replace('+', 'plus')}.png"
    cache_path = os.path.join(LEVEL_CACHE_DIR, cache_filename)

    if not os.path.exists(cache_path):
        # 缓存不存在，返回错误
        return cache_not_found(user_id)

    # 从缓存读取图片并上传
    try:
        cached_img = Image.open(cache_path)
        original_url, preview_url = smart_upload(cached_img)
        # 返回图片和提示消息
        return [
            ImageMessage(original_content_url=original_url, preview_image_url=preview_url),
            level_list_hint(user_id)
        ]
    except Exception as e:
        print(f"读取缓存失败: {e}")
        return cache_not_found(user_id)

def _generate_level_cache_for_server(ver):
    """
    为指定服务器生成所有等级的缓存

    参数:
        ver: 服务器版本（"jp" 或 "intl"）
    """
    import os
    from modules.image_cache import batch_download_images

    print(f"[Cache] 开始为 {ver.upper()} 服务器生成等级缓存...")

    read_dxdata(ver)

    # 定义所有支持的等级（只生成12及以上，14+ 会包含 14+ 和 15，15 单独只包含 15.0）
    valid_levels = ["12", "12+", "13", "13+", "14", "14+", "15"]

    # 创建缓存目录
    os.makedirs(LEVEL_CACHE_DIR, exist_ok=True)

    generated_count = 0

    for idx, level in enumerate(valid_levels):
        try:
            # 更新进度 - 开始处理这个等级
            with stats_lock:
                cache_generation_progress["current_server"] = ver.upper()
                cache_generation_progress["current_level"] = level
                cache_generation_progress["completed_levels"] = generated_count
                cache_generation_progress["progress"] = int((generated_count / 14) * 100)
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
                print(f"[Cache] {ver.upper()} Lv.{level}: 无歌曲，跳过")
                continue

            # 批量并发下载所有封面
            print(f"[Cache] {ver.upper()} Lv.{level}: 并发下载 {len(song_data_list)} 首歌曲封面...")
            cover_urls = [s['cover_url'] for s in song_data_list]
            downloaded_covers = batch_download_images(cover_urls, max_workers=5)

            # 生成封面图片（使用已下载的图片）
            target_data = []
            for song_data in song_data_list:
                cover_url = song_data['cover_url']
                if cover_url in downloaded_covers:
                    cover_img = generate_cover(cover_url, song_data['type'], size=135, cover_name=song_data.get('cover_name'))
                    target_data.append({
                        "img": cover_img,
                        "internal_level": song_data['internal_level']
                    })

            if not target_data:
                print(f"[Cache] {ver.upper()} Lv.{level}: 封面下载失败，跳过")
                continue

            # 生成图片
            level_img = generate_internallevel_image(target_data, level)

            # 不再缩小图片 - 保持高清晰度 (原本缩小到3/5会降低清晰度)
            # 已提升 img_size 从 135px 到 180px,水印会自动按比例调整

            # 用compose函数包装
            final_img = compose_images([level_img])

            # 保存到缓存
            cache_filename = f"{ver}_{level.replace('+', 'plus')}.png"
            cache_path = os.path.join(LEVEL_CACHE_DIR, cache_filename)
            final_img.save(cache_path, 'PNG')

            generated_count += 1

            # 立即更新完成的等级数和进度
            with stats_lock:
                cache_generation_progress["completed_levels"] = generated_count
                cache_generation_progress["progress"] = int((generated_count / 14) * 100)

            print(f"[Cache] {ver.upper()} Lv.{level}: ✓ ({len(target_data)} 首歌曲)")

        except Exception as e:
            print(f"[Cache] {ver.upper()} Lv.{level}: ✗ 错误: {e}")
            import traceback
            traceback.print_exc()

    print(f"[Cache] {ver.upper()} 服务器缓存生成完成：{generated_count}/{len(valid_levels)} 个等级")

def generate_all_level_caches():
    """后台生成所有服务器的等级缓存（带进度跟踪）"""
    from datetime import datetime

    # 计算实际的总等级数
    valid_levels = ["12", "12+", "13", "13+", "14", "14+", "15"]
    total_levels = len(valid_levels)  # 每个服务器都有这些等级

    # 初始化进度
    with stats_lock:
        cache_generation_progress["status"] = "running"
        cache_generation_progress["progress"] = 0
        cache_generation_progress["total_levels"] = total_levels
        cache_generation_progress["completed_levels"] = 0
        cache_generation_progress["error_message"] = ""
        cache_generation_progress["start_time"] = datetime.now().isoformat()
        cache_generation_progress["end_time"] = None

    try:
        _generate_level_cache_for_server("jp")
        _generate_level_cache_for_server("intl")
        print("[Cache] 所有等级缓存生成完成")

        # 标记完成
        with stats_lock:
            cache_generation_progress["status"] = "completed"
            cache_generation_progress["progress"] = 100
            cache_generation_progress["end_time"] = datetime.now().isoformat()

        # 通知所有管理员缓存生成完成
        from modules.line_messenger import smart_push
        for admin_user_id in ADMIN_ID:
            try:
                smart_push(admin_user_id, TextMessage(
                    text="✅ 定数表缓存生成完成\n已为所有服务器生成12级及以上的定数表缓存"
                ), configuration)
            except Exception as e:
                logger.error(f"Failed to notify admin {admin_user_id} about cache completion: {e}")
    except Exception as e:
        print(f"[Cache] 缓存生成失败: {e}")
        import traceback
        traceback.print_exc()

        # 通知所有管理员缓存生成失败
        from modules.line_messenger import smart_push
        for admin_user_id in ADMIN_ID:
            try:
                smart_push(admin_user_id, TextMessage(
                    text=f"❌ 定数表缓存生成失败\n错误: {e}"
                ), configuration)
            except Exception as notify_error:
                logger.error(f"Failed to notify admin {admin_user_id} about cache failure: {notify_error}")

def create_user_info_img(user_info, scale=1.5):
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
                print(f"加载图片失败 {user_info[key]}: {e}")
                return None
        return None

    paste_image("nameplate_url", (0, 0), (802, 128))

    paste_image("icon_url", (15, 13), (100, 100))

    paste_image("rating_block_url", (129, 13), (131, 34))

    # 使用等宽方式绘制 rating 数字
    rating_text = f"{user_info['rating']}"
    char_width = 13  # 每个字符的固定宽度
    start_x = 188
    for i, char in enumerate(rating_text):
        draw.text((start_x + i * char_width, 17), char, fill=(255, 255, 255), font=font_large)

    # 绘制带灰色边框的圆角矩形
    draw.rounded_rectangle([129, 51, 129 + 266, 51 + 33], radius=10, fill=(255, 255, 255), outline=(180, 180, 180), width=2)
    draw.text((138, 54), user_info['name'], fill=(0, 0, 0), font=font_large)

    paste_image("class_rank_url", (296, 9), (70, 40))

    paste_image("cource_rank_url", (322, 54), (69, 28))

    _if_trophy = paste_image("trophy_url", (129, 92), (266, 21))

    def trophy_color(type):
        return {
            "normal": (255, 255, 255),
            "bronze": (193, 102, 78),
            "silver": (186, 255, 251),
            "gold": (255, 243, 122),
            "rainbow": (233, 83, 106),
        }.get(type, (255, 255, 255))
    trophy_content = truncate_text(draw, user_info['trophy_content'], font_small, 253)

    # 计算文本居中位置
    bbox = draw.textbbox((0, 0), trophy_content, font=font_small)
    text_width = bbox[2] - bbox[0]
    rect_width = 266
    center_x = 129 + (rect_width - text_width) // 2

    if not _if_trophy:
        draw.rectangle([129, 92, 129 + 266, 92 + 21], fill=trophy_color(user_info['trophy_type']))
        draw.text((center_x, 93), trophy_content, fill=(0, 0, 0), font=font_small)
    else:
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
                        # 将 + 替换为 " PLUS"（注意前面有空格）
                        processed = v.strip().replace("+", " PLUS").upper()
                        versions.append(processed)
                # 筛选歌曲版本在指定列表中的记录（忽略大小写）
                song_record = list(filter(lambda x: (x.get('version') or '').upper() in versions, song_record))

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
    read_user()

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

def generate_yang_rating(user_id, ver="jp"):
    song_record = read_record(user_id, yang=True)
    if not len(song_record):
        return record_error(user_id)

    read_user()
    if "personal_info" not in USERS[user_id]:
        return info_error(user_id)

    now_version = MAIMAI_VERSION[USERS[user_id]['version']][-1]

    version_records = []

    read_dxdata(ver)
    for version in VERSIONS:
        if version['version'] == now_version:
            break

        version_data = {}
        version_data['version_title'] = version['version']
        version_song_data = list(filter(lambda x: x['version'] == version['version'], song_record))
        count = max(math.floor(version['count'] * 0.05), 1)
        version_data['songs'] = sorted(version_song_data, key=lambda x: -x["ra"])[:count]
        version_data['count'] = count
        version_records.append(version_data)

    img = generate_yang_records_picture(version_records)

    # 获取用户信息并创建用户信息图片
    user_info = USERS[user_id]['personal_info']
    img = compose_images([create_user_info_img(user_info), img])

    original_url, preview_url = smart_upload(img)
    message = ImageMessage(original_content_url=original_url, preview_image_url=preview_url)
    return message

def generate_friend_b50(user_id, friend_code, ver="jp"):
    read_user()

    if user_id not in USERS :
        return segaid_error(user_id)

    elif 'sega_id' not in USERS[user_id] or 'sega_pwd' not in USERS[user_id] :
        return segaid_error(user_id)

    sega_id = USERS[user_id]['sega_id']
    sega_pwd = USERS[user_id]['sega_pwd']

    user_session = login_to_maimai(sega_id, sega_pwd, ver)
    if user_session == None:
        return segaid_error(user_id)
    if user_session == "MAINTENANCE":
        return maintenance_error(user_id)

    # 使用异步函数获取好友成绩（性能提升约5倍）
    cookies = user_session.cookies.get_dict()
    friend_name, song_record = asyncio.run(get_friend_records_async(cookies, friend_code, ver))

    if not friend_name or not song_record:
        return friend_rcd_error(user_id)

    song_record = get_detailed_info(song_record, ver)

    up_songs_data = list(filter(lambda x: x['new_song'] == False, song_record))
    down_songs_data = list(filter(lambda x: x['new_song'] == True, song_record))

    up_songs = sorted(up_songs_data, key=lambda x: -x["ra"])[:35]
    down_songs = sorted(down_songs_data, key=lambda x: -x["ra"])[:15]

    img = generate_records_picture(up_songs, down_songs, "FRD-B50")
    img = compose_images([img])

    original_url, preview_url = smart_upload(img)
    message = [
        friend_best50_title(friend_name, user_id),
        ImageMessage(original_content_url=original_url, preview_image_url=preview_url)
    ]
    return message

def generate_level_records(user_id, level, ver="jp", page=1):
    read_user()

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

    title = f"LV{level} #{page}"

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

    for version in VERSIONS :
        if version_title.lower() == version['version'].lower() :
            target_version.append(version['version'])

    if not len(target_version) :
        return version_error(user_id)

    songs_data = list(filter(lambda x: x['version'] in target_version and x['type'] not in ['utage'], SONGS))
    version_img = generate_version_list(songs_data)

    # 不再缩小图片 - 保持高清晰度 (原本缩小到1/3会严重降低清晰度)
    # 已提升缩略图尺寸从 300x150 到 400x200,水印会自动按比例调整

    img = compose_images([version_img])

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
    'exact': {
        "yang", "yrating", "yra", "ヤンレーティング"
    },
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
        "ab200", "allb200", "all best 200", "オールベスト200",
        "ap50", "apb50", "all perfect 50", "オールパーフェクト50",
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
    from modules.perm_request_handler import accept_perm_request
    from modules.message_manager import (
        get_multilingual_text,
        perm_request_accept_success_text,
        perm_request_error_text
    )

    result = accept_perm_request(user_id, request_id)

    if result['success']:
        text = get_multilingual_text(perm_request_accept_success_text, user_id).format(
            token_id=result['token_id'],
            requester_name=result.get('requester_name', result['token_id'])
        )
    else:
        text = get_multilingual_text(perm_request_error_text, user_id).format(
            error=result['error'],
            message=result['message']
        )

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
    from modules.perm_request_handler import reject_perm_request
    from modules.message_manager import (
        get_multilingual_text,
        perm_request_reject_success_text,
        perm_request_error_text
    )

    result = reject_perm_request(user_id, request_id)

    if result['success']:
        text = get_multilingual_text(perm_request_reject_success_text, user_id).format(
            token_id=result['token_id'],
            requester_name=result.get('requester_name', result['token_id'])
        )
    else:
        text = get_multilingual_text(perm_request_error_text, user_id).format(
            error=result['error'],
            message=result['message']
        )

    return TextMessage(text=text)


@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event):
    """
    文本消息处理入口

    根据消息类型智能路由:
    - Web任务 → webtask_queue (网络请求，如 maimai_update)
    - 图片生成任务 → image_queue (图片生成，如 b50, yang rating)
    - 其他任务 → 同步处理 (快速文本响应)
    """
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

    处理快速文本命令，如：
    - check, network, get me, unbind
    - rc 计算, calc 命令
    - SEGA ID 绑定
    - 管理员命令
    """
    user_message = event.message.text.strip()
    user_id = event.source.user_id

    # 检查消息中是否有 mention（@）
    mentioned_user_id = None
    if hasattr(event.message, 'mention') and event.message.mention:
        # 获取第一个被 @ 的用户
        mentionees = event.message.mention.mentionees
        if mentionees and len(mentionees) > 0:
            first_mention = mentionees[0]
            # 检查是否是用户类型的 mention（不是 @all）
            if hasattr(first_mention, 'user_id') and first_mention.user_id:
                mentioned_user_id = first_mention.user_id
                logger.info(f"[Mention] User {user_id} mentioned {mentioned_user_id}, will use mentioned user's data")

    read_user()
    if user_id in USERS:
        mai_ver = USERS[user_id].get("version", "jp")
        # 如果有 mention，优先使用被 @ 的用户 ID
        if mentioned_user_id:
            id_use = mentioned_user_id
        else:
            id_use = USERS[user_id].get("id_use", user_id)
        # 获取目标用户的版本信息
        if id_use in USERS:
            mai_ver_use = USERS[id_use].get("version", "jp")
        else:
            mai_ver_use = mai_ver
        # 重置 id_use（如果不是 mention 的情况）
        if not mentioned_user_id:
            edit_user_value(user_id, "id_use", user_id)
    else:
        id_use = user_id
        mai_ver = "jp"
        mai_ver_use = "jp"


    # ====== 基础命令映射 ======
    COMMAND_MAP = {
        # 捐赠
        "donate": lambda: donate_message,
        "ドネーション": lambda: donate_message,

        # 账户管理
        "unbind": lambda: (delete_user(user_id), unbind_msg(user_id))[-1],
        "アンバインド": lambda: (delete_user(user_id), unbind_msg(user_id))[-1],
        "get me": lambda: TextMessage(text=get_user(user_id)),
        "getme": lambda: TextMessage(text=get_user(user_id)),
        "ゲットミー": lambda: TextMessage(text=get_user(user_id)),

        # Yang Rating
        "yang": lambda: generate_yang_rating(id_use, mai_ver_use),
        "yrating": lambda: generate_yang_rating(id_use, mai_ver_use),
        "yra": lambda: generate_yang_rating(id_use, mai_ver_use),
        "ヤンレーティング": lambda: generate_yang_rating(id_use, mai_ver_use),

        # 好友列表
        "friend list": lambda: get_friend_list(user_id),
        "フレンドリスト": lambda: get_friend_list(user_id),
        "friendlist": lambda: get_friend_list(user_id)
    }

    if user_message in COMMAND_MAP:
        reply_message = COMMAND_MAP[user_message]()
        return smart_reply(user_id, event.reply_token, reply_message, configuration, DIVIDER)

    # ====== 模糊匹配规则 ======
    SPECIAL_RULES = [
        # 歌曲信息查询
        (lambda msg: msg.endswith(("ってどんな曲", "info", "song-info")),
        lambda msg: search_song(
            user_id,
            re.sub(r"\s*(ってどんな曲|info|song-info)$", "", msg).strip(),
            mai_ver
        )),

        # 随机歌曲
        (lambda msg: msg.startswith(("ランダム曲", "ランダム", "random-song", "random")),
        lambda msg: random_song(
            user_id,
            re.sub(r"^(ランダム曲|ランダム|random-song|random)", "", msg).strip(),
            mai_ver
        )),

        # Rating 对照表
        (lambda msg: msg.startswith(("rc ", "RC ", "Rc ")),
        lambda msg: TextMessage(
            text=get_rc(float(re.sub(r"^rc\b[ 　]*", "", msg, flags=re.IGNORECASE)))
        )),

        # 版本达成情况
        (lambda msg: msg.endswith(("の達成状況", "の達成情報", "の達成表", "achievement-list", "achievement")),
        lambda msg: generate_plate_rcd(
            id_use,
            re.sub(r"\s*(の達成状況|の達成情報|の達成表|achievement-list|achievement)$", "", msg).strip(),
            mai_ver_use
        )),

        # 歌曲成绩记录
        (lambda msg: msg.endswith(("のレコード", "song-record", "record")),
        lambda msg: get_song_record(
            id_use,
            re.sub(r"\s*(のレコード|song-record|record)$", "", msg).strip(),
            mai_ver_use
        )),

        # 等级成绩列表
        (lambda msg: re.match(r".+(のレコードリスト|record-list|records)[ 　]*\d*$", msg),
        lambda msg: generate_level_records(
            id_use,
            re.sub(r"\s*(のレコードリスト|record-list|records)[ 　]*\d*$", "", msg).strip(),
            mai_ver_use,
            int(re.search(r"(\d+)$", msg).group(1)) if re.search(r"(\d+)$", msg) else 1
        )),

        # 版本歌曲列表
        (lambda msg: msg.endswith(("のバージョンリスト", "version-list", "version")),
        lambda msg: generate_version_songs(
            user_id,
            re.sub(r"\s*\+\s*", " PLUS", re.sub(r"(のバージョンリスト|version-list|version)$", "", msg)).strip(),
            mai_ver
        )),

        # 定数查询
        (lambda msg: msg.endswith(("の定数リスト", "のレベルリスト", "level-list")),
        lambda msg: generate_internallevel_songs(
            user_id,
            re.sub(r"\s*(の定数リスト|のレベルリスト|level-list)$", "", msg),
            mai_ver
        )),

        # 权限请求管理
        (lambda msg: msg.startswith("accept-perm-request "),
        lambda msg: handle_accept_perm_request(
            user_id,
            re.sub(r"^accept-perm-request ", "", msg).strip()
        )),

        (lambda msg: msg.startswith("reject-perm-request "),
        lambda msg: handle_reject_perm_request(
            user_id,
            re.sub(r"^reject-perm-request ", "", msg).strip()
        ))
    ]

    for cond, func in SPECIAL_RULES:
        if cond(user_message):
            reply_message = func(user_message)
            return smart_reply(user_id, event.reply_token, reply_message, configuration, DIVIDER)

    # ====== B 系列命令 ======
    first_word = re.split(r"[ \n]", user_message.lower(), 1)[0]
    rest_text = re.split(r"[ \n]", user_message.lower(), 1)[1] if re.search(r"[ \n]", user_message) else ""

    RANK_COMMANDS = {
        ("b50", "best50", "best 50", "ベスト50"): "best50",
        ("b100", "best100", "best 100", "ベスト100"): "best100",
        ("b35", "best35", "best 35", "ベスト35"): "best35",
        ("b15", "best15", "best 15", "ベスト15"): "best15",
        ("ab35", "allb35", "all best 35", "オールベスト35"): "allb35",
        ("ab50", "allb50", "all best 50", "オールベスト50"): "allb50",
        ("ab100", "allb100", "all best 100", "オールベスト100"): "allb100",
        ("ab200", "allb200", "all best 200", "オールベスト200"): "allb200",
        ("ap50", "apb50", "all perfect 50", "オールパーフェクト50"): "apb50",
        ("rct50", "r50", "recent50", "recent 50"): "rct50",
        ("idealb50", "idlb50", "ideal best 50", "理想的ベスト50"): "idealb50",
        ("unknown", "unknown songs", "unknown data", "未発見"): "UNKNOWN",
    }

    for aliases, mode in RANK_COMMANDS.items():
        if first_word in aliases:
            reply_message = generate_records(id_use, mode, rest_text, mai_ver_use)
            return smart_reply(user_id, event.reply_token, reply_message, configuration, DIVIDER)

    # ====== SEGA ID 绑定逻辑 ======
    BIND_COMMANDS = ["bind", "segaid bind", "バインド"]
    if user_message.lower() in BIND_COMMANDS:
        # 检查用户是否已设置语言
        user_data = USERS.get(user_id, {})
        has_language = 'language' in user_data

        # 如果用户还没有设置语言，先让用户选择语言
        if not has_language:
            from modules.message_manager import (
                language_select_title, language_select_description,
                language_button_jp, language_button_en, language_button_zh,
                language_select_alt
            )

            buttons_template = ButtonsTemplate(
                title=language_select_title,
                text=language_select_description,
                actions=[
                    MessageAction(label=language_button_jp, text="language jp"),
                    MessageAction(label=language_button_en, text="language en"),
                    MessageAction(label=language_button_zh, text="language zh")
                ]
            )
            reply_message = TemplateMessage(
                alt_text=language_select_alt,
                template=buttons_template
            )

            return smart_reply(user_id, event.reply_token, reply_message, configuration, DIVIDER)

        # 用户已设置语言，检查是否已经绑定账号
        has_account = all(key in user_data for key in ['sega_id', 'sega_pwd', 'version'])

        if has_account:
            # 已经绑定过账号，提示先解绑
            from modules.message_manager import already_bound_text, get_multilingual_text
            reply_message = TextMessage(text=get_multilingual_text(already_bound_text, user_id))
            return smart_reply(user_id, event.reply_token, reply_message, configuration, DIVIDER)

        # 用户已设置语言且未绑定账号，显示绑定按钮
        bind_url = f"https://{DOMAIN}/linebot/sega_bind?token={generate_token(user_id)}"

        # 使用多语言文本
        from modules.message_manager import (
            sega_bind_title_text, sega_bind_description_text,
            sega_bind_button_text, sega_bind_alt_text, get_multilingual_text
        )

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

        return smart_reply(user_id, event.reply_token, reply_message, configuration, DIVIDER)

    # ====== language 命令 ======
    if user_message.startswith("language "):
        lang_code = user_message[9:].strip().lower()

        # 验证语言代码
        if lang_code not in ["jp", "en", "zh"]:
            reply_message = TextMessage(text="Invalid language code. Please use: jp, en, or zh")
            return smart_reply(user_id, event.reply_token, reply_message, configuration, DIVIDER)

        # 设置用户语言
        user_set_language(user_id, lang_code)

        # 使用多语言成功消息
        from modules.message_manager import language_set_success_text, get_multilingual_text, get_bind_quick_reply
        success_text = get_multilingual_text(language_set_success_text, user_id)

        # 添加快捷回复按钮
        quick_reply = get_bind_quick_reply(user_id)

        reply_message = TextMessage(text=success_text, quick_reply=quick_reply)
        return smart_reply(user_id, event.reply_token, reply_message, configuration, DIVIDER)

    # ====== calc 命令 ======
    if user_message.startswith("calc "):
        try:
            num = list(map(int, user_message[5:].split()))
            if len(num) == 4:
                num = [num[0], num[1], num[2], 0, num[3]]
            if len(num) != 5:
                raise ValueError
            notes = dict(zip(['tap', 'hold', 'slide', 'touch', 'break'], num))
            scores = get_note_score(notes)
            result = (
                f"TAP: \t {num[0]}\nHOLD: \t {num[1]}\nSLIDE: \t {num[2]}\n"
                f"TOUCH: \t {num[3]}\nBREAK: \t {num[4]}\n{DIVIDER}\n"
            )
            for k, v in scores.items():
                result += f"{k.ljust(20)} -{v:.5f}%\n"
            reply_message = TextMessage(text=result)
        except Exception:
            reply_message = input_error(user_id)
        return smart_reply(user_id, event.reply_token, reply_message, configuration, DIVIDER)

    # ====== 管理员命令 ======
    if user_id in ADMIN_ID:
        if user_message.startswith("upload notice"):
            new_notice = user_message.replace("upload notice", "").strip()
            upload_notice(new_notice)
            clear_user_value("notice_read", False)
            return smart_reply(user_id, event.reply_token, notice_upload(user_id), configuration, DIVIDER)

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
                        logger.error(f"Failed to notify admin {admin_user_id}: {e}")

            # 将缓存生成任务添加到队列
            try:
                cache_queue.put((generate_all_level_caches, ()), block=False)
                logger.info("Cache generation task queued")
            except queue.Full:
                logger.warning("Cache queue is full, task not queued")

            return

        if user_message.startswith("devtoken "):
            from modules.devtoken_manager import (
                create_dev_token, list_dev_tokens, revoke_dev_token, get_token_info
            )
            from modules.message_manager import (
                devtoken_create_success_text, devtoken_create_failed_text,
                devtoken_list_header_text, devtoken_list_empty_text,
                devtoken_revoke_success_text, devtoken_revoke_failed_text,
                devtoken_info_text, devtoken_info_not_found_text,
                devtoken_usage_text, get_multilingual_text
            )

            # Parse command
            parts = user_message.split(maxsplit=2)

            if len(parts) < 2:
                # Show usage
                reply_message = TextMessage(text=get_multilingual_text(devtoken_usage_text, user_id))
                return smart_reply(user_id, event.reply_token, reply_message, configuration, DIVIDER)

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
                return smart_reply(user_id, event.reply_token, reply_message, configuration, DIVIDER)

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
                return smart_reply(user_id, event.reply_token, reply_message, configuration, DIVIDER)

            elif subcommand == "revoke" and len(parts) >= 3:
                token_id = parts[2]
                success = revoke_dev_token(token_id)
                if success:
                    text = get_multilingual_text(devtoken_revoke_success_text, user_id)
                    text = text.format(token_id=token_id)
                    reply_message = TextMessage(text=text)
                else:
                    reply_message = TextMessage(text=get_multilingual_text(devtoken_revoke_failed_text, user_id))
                return smart_reply(user_id, event.reply_token, reply_message, configuration, DIVIDER)

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
                return smart_reply(user_id, event.reply_token, reply_message, configuration, DIVIDER)

            else:
                # Invalid subcommand or missing arguments
                reply_message = TextMessage(text=get_multilingual_text(devtoken_usage_text, user_id))
                return smart_reply(user_id, event.reply_token, reply_message, configuration, DIVIDER)


    # ====== 默认：不匹配任何命令 ======
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
        # 发现 QR 码，解析并处理
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

    else:
        # 没有 QR 码，尝试封面匹配
        user_id = event.source.user_id
        mai_ver = "jp"
        read_user()
        if user_id in USERS:
            if 'version' in USERS[user_id]:
                mai_ver = USERS[user_id]['version']

        read_dxdata(mai_ver)

        # 混合策略匹配：hash 快速匹配完整封面，sift 处理场景图片和部分遮挡
        # 直接尝试多个匹配（图片中可能有多个封面）
        matched_songs = find_song_by_cover(image, SONGS, hash_threshold=15, return_multiple=True, max_results=3)

        if matched_songs:
            try:
                reply_messages = []

                # 处理所有匹配结果（1个或多个）
                for song in matched_songs:
                    original_url, preview_url = smart_upload(song_info_generate(song))
                    reply_messages.append(ImageMessage(original_content_url=original_url, preview_image_url=preview_url))

                if reply_messages:
                    smart_reply(
                        event.source.user_id,
                        event.reply_token,
                        reply_messages,
                        configuration,
                        DIVIDER
                    )
            except Exception as e:
                logger.error(f"Loading level cache error: {e}")
                smart_reply(
                    event.source.user_id,
                    event.reply_token,
                    qrcode_error(event.source.user_id),
                    configuration,
                    DIVIDER
                )
        else:
            # 未找到匹配，返回错误
            smart_reply(
                event.source.user_id,
                event.reply_token,
                qrcode_error(event.source.user_id),
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
    read_user()
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
    位置消息处理 - 同步处理，返回机厅按钮列表
    """
    read_user()

    lat = event.message.latitude
    lng = event.message.longitude
    user_id = event.source.user_id

    stores = get_nearby_maimai_stores(lat, lng, USERS[user_id]['version'])

    # 检查维护状态
    if stores == "MAINTENANCE":
        reply_message = maintenance_error(user_id)
    elif not stores:
        reply_message = store_error(user_id)
    else:
        # 使用 LINE SDK v3 对象构建的 Flex Message（已修复结构问题）
        from modules.storelist_generator import generate_store_buttons
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
            from modules.user_manager import get_user_nickname
            nickname = get_user_nickname(user_id, line_bot_api, use_cache)

            # 检查是否为错误消息
            if nickname and ("Unknown" in nickname or "API Error" in nickname or "Blocked" in nickname):
                nickname = None
    except Exception as e:
        logger.debug(f"Failed to get LINE nickname for {user_id}: {e}")
        nickname = None

    # 如果LINE API失败,尝试从用户数据获取
    if not nickname:
        read_user()
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

    # 已登录，显示管理面板
    read_user()

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
        logger.error(f"Admin trigger update error: {e}")
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

        logger.info(f"Admin cancelled task: {task_id}")

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
        logger.error(f"Admin memory stats error: {e}", exc_info=True)
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
        logger.error(f"Admin trigger cleanup error: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/linebot/admin/get_notices", methods=["GET"])
def admin_get_notices():
    """获取所有公告"""
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        from modules.notice_manager import get_all_notices
        notices = get_all_notices()
        return jsonify({'success': True, 'notices': notices})
    except Exception as e:
        logger.error(f"Admin get notices error: {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route("/linebot/admin/create_notice", methods=["POST"])
@csrf.exempt
def admin_create_notice():
    """创建新公告"""
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    content = data.get('content', '').strip()

    if not content:
        return jsonify({'success': False, 'message': 'Content is required'}), 400

    try:
        from modules.notice_manager import upload_notice
        notice_id = upload_notice(content)
        clear_user_value("notice_read", False)
        logger.info(f"Admin created notice: {notice_id}")

        return jsonify({
            'success': True,
            'message': 'Notice created successfully',
            'notice_id': notice_id
        })
    except Exception as e:
        logger.error(f"Admin create notice error: {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route("/linebot/admin/update_notice", methods=["POST"])
@csrf.exempt
def admin_update_notice():
    """更新公告"""
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    notice_id = data.get('notice_id')
    content = data.get('content', '').strip()

    if not notice_id or not content:
        return jsonify({'success': False, 'message': 'Notice ID and content are required'}), 400

    try:
        from modules.notice_manager import update_notice, get_latest_notice

        # 检查是否为最新公告
        latest_notice = get_latest_notice()
        is_latest = latest_notice and latest_notice.get('id') == notice_id

        success = update_notice(notice_id, content)

        if success:
            # 如果修改的是最新公告，将全体用户状态修改为未阅读
            if is_latest:
                clear_user_value("notice_read", False)
                logger.info(f"Admin updated latest notice: {notice_id}, cleared all users' read status")
            else:
                logger.info(f"Admin updated notice: {notice_id}")

            return jsonify({'success': True, 'message': 'Notice updated successfully'})
        else:
            return jsonify({'success': False, 'message': 'Notice not found'}), 404

    except Exception as e:
        logger.error(f"Admin update notice error: {e}", exc_info=True)
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
        from modules.notice_manager import delete_notice
        clear_user_value("notice_read", True)
        success = delete_notice(notice_id)

        if success:
            logger.info(f"Admin deleted notice: {notice_id}")
            return jsonify({'success': True, 'message': 'Notice deleted successfully'})
        else:
            return jsonify({'success': False, 'message': 'Notice not found'}), 404

    except Exception as e:
        logger.error(f"Admin delete notice error: {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

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
        read_user()

        if user_id not in USERS:
            return jsonify({
                'success': False,
                'message': f'User {user_id} not found'
            }), 404

        # 更新用户数据
        USERS[user_id] = user_data
        mark_user_dirty()
        write_user()

        logger.info(f"Admin edited user data for {user_id}")

        # 不再发送通知给管理员

        return jsonify({
            'success': True,
            'message': 'User data updated successfully'
        })

    except Exception as e:
        logger.error(f"Admin edit user error: {e}", exc_info=True)
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
        read_user()

        if user_id not in USERS:
            return jsonify({
                'success': False,
                'message': f'User {user_id} not found'
            }), 404

        # 使用 delete_user 函数删除用户
        from modules.user_manager import delete_user
        delete_user(user_id)

        logger.info(f"Admin deleted user: {user_id}")

        return jsonify({
            'success': True,
            'message': f'User {user_id} deleted successfully'
        })

    except Exception as e:
        logger.error(f"Admin delete user error: {e}", exc_info=True)
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

        logger.info(f"Admin cleared nickname cache ({cache_size} entries)")

        return jsonify({
            'success': True,
            'message': f'Cache cleared ({cache_size} entries)'
        })

    except Exception as e:
        logger.error(f"Admin clear cache error: {e}", exc_info=True)
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
        read_user()

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
        logger.error(f"Admin get user data error: {e}", exc_info=True)
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
        read_user()

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
        logger.error(f"Admin load nicknames error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route("/linebot/admin/cache_progress", methods=["GET"])
def admin_cache_progress():
    """获取缓存生成进度"""
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    with stats_lock:
        progress_data = cache_generation_progress.copy()

    return jsonify(progress_data)

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
        logger.error(f"Admin DXData status error: {e}", exc_info=True)
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
        from modules.devtoken_manager import load_dev_tokens

        read_user()

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
        logger.info(f"API: List users via token {token_id} ({token_info['note']})")

        return jsonify({
            "success": True,
            "count": len(users_list),
            "users": users_list
        })

    except Exception as e:
        logger.error(f"API list users error: {e}", exc_info=True)
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
        from modules.token_manager import generate_token as generate_bind_token
        from modules.user_manager import get_user_nickname

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
        logger.info(f"API: Register user {user_id} (nickname={nickname}, language={language}) via token {token_info['token_id']} ({token_info['note']})")

        # 读取用户数据
        read_user()

        if user_id in USERS:
            return jsonify({
                "error": "User already exists",
                "message": f"User {user_id} was created already."
            }), 409  # 409 Conflict 更合适

        # 生成绑定 token
        bind_token = generate_bind_token(user_id)

        # 构建绑定 URL
        bind_url = f"{DOMAIN}/linebot/sega_bind?token={bind_token}"

        # 初始化用户数据
        from datetime import datetime
        add_user(user_id)
        user_set_language(user_id, language)
        edit_user_value(user_id, "nickname", nickname)
        edit_user_value(user_id, "registered_via_token", token_info['token_id'])
        edit_user_value(user_id, "registered_at", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        logger.info(f"Created new user {user_id} via API token {token_info['token_id']}")

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
        logger.error(f"API register user error: {e}", exc_info=True)
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
        logger.info(f"API: Get user {user_id} via token {token_info['token_id']} ({token_info['note']})")

        return jsonify({
            "success": True,
            "user_id": user_id,
            "nickname": nickname,
            "data": user_data
        })

    except Exception as e:
        logger.error(f"API get user error: {e}", exc_info=True)
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
        from modules.user_manager import delete_user

        # 获取用户信息用于日志
        nickname = get_user_nickname_wrapper(user_id, use_cache=True)

        # 删除用户
        delete_user(user_id)

        # 记录 API 访问日志
        token_info = request.token_info
        logger.info(f"API: Delete user {user_id} ({nickname}) via token {token_info['token_id']} ({token_info['note']})")

        return jsonify({
            "success": True,
            "user_id": user_id,
            "message": f"User {user_id} has been deleted successfully"
        })

    except Exception as e:
        logger.error(f"API delete user error: {e}", exc_info=True)
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
        from modules.perm_request_handler import send_perm_request

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
        logger.info(f"API: Request permission to user {user_id} via token {token_id} ({token_info['note']})")

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
        logger.error(f"API request permission error: {e}", exc_info=True)
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
        from modules.perm_request_handler import get_pending_perm_requests

        # 获取待处理的权限请求
        requests = get_pending_perm_requests(user_id)

        # 记录 API 访问日志
        token_info = request.token_info
        logger.info(f"API: Get permission requests for user {user_id} via token {token_info['token_id']} ({token_info['note']})")

        return jsonify({
            "success": True,
            "user_id": user_id,
            "count": len(requests),
            "requests": requests
        })

    except Exception as e:
        logger.error(f"API get permission requests error: {e}", exc_info=True)
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
        from modules.perm_request_handler import accept_perm_request

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
        logger.info(f"API: Accept permission request {request_id} for user {user_id} via token {token_info['token_id']} ({token_info['note']})")

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
        logger.error(f"API accept permission request error: {e}", exc_info=True)
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
        from modules.perm_request_handler import reject_perm_request

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
        logger.info(f"API: Reject permission request {request_id} for user {user_id} via token {token_info['token_id']} ({token_info['note']})")

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
        logger.error(f"API reject permission request error: {e}", exc_info=True)
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
        from modules.devtoken_manager import load_dev_tokens, save_dev_tokens

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
        logger.info(f"API: Revoke permission for token {target_token_id} from user {user_id} via token {token_info['token_id']} ({token_info['note']})")

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
        logger.error(f"API revoke permission error: {e}", exc_info=True)
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
        logger.error(f"API get task status error: {e}", exc_info=True)
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
        import secrets
        task_id = f"api_update_{secrets.token_hex(8)}"

        # 将更新任务加入队列
        try:
            webtask_queue.put_nowait((async_maimai_update_task, (mock_event,), task_id))

            # 记录 API 访问日志
            token_info = request.token_info
            logger.info(f"API: Triggered update for user {user_id} via token {token_info['token_id']} ({token_info['note']})")

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
        logger.error(f"API update user error: {e}", exc_info=True)
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
        logger.info(f"API: Get records for user {user_id} (type={record_type}) via token {token_info['token_id']} ({token_info['note']})")

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
        logger.error(f"API get records error: {e}", exc_info=True)
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
        max_results = request.args.get('max_results', 6, type=int)

        # 处理特殊占位符
        if query == '__empty__':
            query = ''
        
        token_info = request.token_info

        if not user_id:
            ver = request.args.get('ver', 'jp')
        else:
            read_user()

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
        logger.info(f"API: Search songs with query '{query}' via token {token_info['token_id']} ({token_info['note']})")

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

        if len(matching_songs) > MAX_SEARCH_RESULTS:
            return jsonify({
                "error": "Too many results",
                "message": f"Found {len(matching_songs)} songs, please refine your search (max: {MAX_SEARCH_RESULTS})",
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

        if len(result) > MAX_SEARCH_RESULTS:
            return jsonify({
                "error": "Too many results",
                "message": f"Found {len(result)} songs, please refine your search (max: {MAX_SEARCH_RESULTS})",
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
        logger.error(f"API search songs error: {e}", exc_info=True)
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
        logger.info(f"API: Get versions info via token {token_info['token_id']} ({token_info['note']})")

        read_dxdata()

        return jsonify({
            "success": True,
            "versions": VERSIONS
        })

    except Exception as e:
        logger.error(f"API get versions error: {e}", exc_info=True)
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500

if __name__ == "__main__":
    # 启动内存管理器
    memory_manager.start()
    logger.info("Memory manager started successfully")

    # 注册清理函数（在内存管理器的清理循环中调用）
    def custom_cleanup():
        """自定义清理函数"""
        try:
            # 清理用户昵称缓存
            cleaned_nicknames = cleanup_user_caches(user_manager_module)

            # 清理频率限制追踪数据
            cleaned_rate_limits = cleanup_rate_limiter_tracking(rate_limiter_module)

            # 清理未绑定的用户（没有 sega_id 或 sega_pwd）
            from modules.system_checker import clean_unbound_users
            cleanup_result = clean_unbound_users()
            cleaned_unbound_users = cleanup_result.get('deleted_count', 0)

            logger.debug(f"Custom cleanup: {cleaned_nicknames} nicknames, {cleaned_rate_limits} rate limit entries, {cleaned_unbound_users} unbound users")
        except Exception as e:
            logger.error(f"Custom cleanup error: {e}", exc_info=True)

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
        logger.info("Memory manager stopped")
