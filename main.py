"""
JiETNG Maimai DX LINE Bot 主程序

提供 Maimai DX 成绩追踪、好友系统、数据可视化等功能
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

from modules.song_generate import *
from modules.record_generate import *
from modules.user_console import *
from modules.token_console import *
from modules.notice_console import *
from modules.maimai_console import *
from modules.dxdata_console import *
from modules.record_console import *
from modules.config_loader import *
from modules.friend_list import *
from modules.reply_text import *
from modules.note_score import *
from modules.img_upload import *

from modules.img_console import (
    combine_with_rounded_background,
    wrap_in_rounded_background,
    generate_qr_with_title
)
from modules.system_check import run_system_check
from modules.rate_limiter import check_rate_limit
from modules.line_messenger import smart_reply, smart_push, notify_admins_error
from modules.song_matcher import find_matching_songs, is_exact_song_title_match
from modules.memory_manager import memory_manager, cleanup_user_caches, cleanup_rate_limiter_tracking
import modules.user_console as user_console_module
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
MAX_SEARCH_RESULTS = 6

# Rating计算范围
RC_SCORE_MIN = 97.0000
RC_SCORE_MAX = 100.5001
RC_SCORE_STEP = 0.0001

# 成绩列表分页
B50_OLD_SONGS = 35
B50_NEW_SONGS = 15
B100_OLD_SONGS = 70
B100_NEW_SONGS = 30

# 请求超时
HTTP_TIMEOUT = 30

# 错误通知配置
ERROR_MESSAGE_MAX_LENGTH = 1000  # LINE消息最大长度限制
ERROR_NOTIFICATION_ENABLED = True  # 是否启用错误通知

# ==================== 日志配置 ====================

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler('jietng.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)  # 用于session加密

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

# Web任务队列 (处理耗时的网络请求，如 maimai_update, friend_list 等)
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
                # 通知管理员
                notify_admins_error(
                    error_title=f"Task Execution Failed: {func.__name__}",
                    error_details=f"{type(e).__name__}: {str(e)}\n\n{traceback.format_exc()}",
                    context={
                        "Task": func.__name__,
                        "Error Type": type(e).__name__
                    },
                    admin_id=admin_id,
                    configuration=configuration,
                    error_notification_enabled=ERROR_NOTIFICATION_ENABLED
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
                admin_id=admin_id,
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
                admin_id=admin_id,
                configuration=configuration,
                error_notification_enabled=ERROR_NOTIFICATION_ENABLED
            )
            webtask_queue.task_done()


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

print(f"Started {MAX_CONCURRENT_IMAGE_TASKS} image workers and {WEB_MAX_CONCURRENT_TASKS} web task workers")
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

# ==================== Flask 路由 ====================

@app.route("/linebot/webhook", methods=['POST'])
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
            admin_id=admin_id,
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
            admin_id=admin_id,
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
            admin_id=admin_id,
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


@app.route("/linebot/add_friend", methods=["GET"])
def maimai_add_friend_page():
    """
    好友添加页面

    通过好友码生成LINE深链接

    Query Args:
        code: 好友码
    """
    friend_code = request.args.get("code")
    return redirect(f"line://oaMessage/{LINE_ACCOUNT_ID}/?add-friend%20{friend_code}")


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
        return render_template("error.html", message="トークン未申請"), 400

    try:
        user_id = get_user_id_from_token(token)
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        return render_template("error.html", message="トークン無効"), 400

    if request.method == "POST":
        segaid = request.form.get("segaid")
        password = request.form.get("password")
        user_version = request.form.get("ver", "jp")

        if not segaid or not password:
            return render_template("error.html", message="すべての項目を入力してください"), 400

        result = process_sega_credentials(user_id, segaid, password, user_version)
        if result == "MAINTENANCE":
            return render_template("error.html", message="公式サイトがメンテナンス中です。しばらくしてからもう一度お試しください。"), 503
        elif result:
            return render_template("success.html")
        else:
            return render_template("error.html", message="SEGA ID と パスワード をもう一度確認してください"), 500

    return render_template("bind_form.html")


def process_sega_credentials(user_id, segaid, password, ver="jp"):
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
    smart_push(user_id, bind_msg, configuration)
    return True

def user_bind_sega_id(user_id, sega_id):
    read_user()

    if user_id not in USERS :
        add_user(user_id)

    USERS[user_id]['sega_id'] = sega_id
    write_user()

def user_bind_sega_pwd(user_id, sega_pwd):
    read_user()

    if user_id not in USERS :
        add_user(user_id)

    USERS[user_id]['sega_pwd'] = sega_pwd
    write_user()

def user_set_version(user_id, version):
    read_user()

    if user_id not in USERS :
        add_user(user_id)

    USERS[user_id]['version'] = version
    write_user()

def get_user(user_id):
    read_user()

    result = f"USER_ID: {user_id}\n"

    if user_id in USERS :
        if "sega_id" in USERS[user_id] :
            result += f"SEGA_ID: {USERS[user_id]['sega_id']}\n"
        else :
            result += "SEGA_ID: 未連携\n"

        if "sega_pwd" in USERS[user_id] :
            result += f"PASSWORD: 連携完了"
        else :
            result += "PASSWORD: 未連携"

    else :
        result += "USER_INFO: 未連携"

    return result

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

    reply_msg = generate_friend_b50(user_id, friend_code, ver)
    smart_reply(user_id, reply_token, reply_msg, configuration, DIVIDER)

def async_add_friend_task(event):
    """异步添加好友任务 - 在webtask_queue中执行（事件处理版本）"""
    user_message = event.message.text.strip()
    user_id = event.source.user_id
    reply_token = event.reply_token
    friend_code = user_message.replace("add-friend ", "").strip()

    # 获取用户版本
    read_user()
    ver = "jp"
    if user_id in USERS and 'version' in USERS[user_id]:
        ver = USERS[user_id]['version']

    # 调用实际的添加好友逻辑并发送回复
    reply_msg = add_friend_with_params(user_id, friend_code, ver)
    smart_reply(user_id, reply_token, reply_msg, configuration, DIVIDER)

def add_friend_with_params(user_id, friend_code, ver):
    """
    添加好友的实际逻辑（参数版本）

    Args:
        user_id: 用户ID
        friend_code: 好友代码
        ver: 游戏版本 (jp/intl)

    Returns:
        TextMessage: 返回消息对象
    """
    read_user()

    if user_id not in USERS or 'sega_id' not in USERS[user_id] or 'sega_pwd' not in USERS[user_id]:
        return segaid_error

    sega_id = USERS[user_id]['sega_id']
    sega_pwd = USERS[user_id]['sega_pwd']

    user_session = login_to_maimai(sega_id, sega_pwd, ver)
    if user_session == None:
        return segaid_error
    if user_session == "MAINTENANCE":
        return maintenance_error

    reply_msg_data = add_friend(user_session, friend_code, ver)
    return TextMessage(text=reply_msg_data)

def async_friend_list_task(event):
    """异步获取好友列表任务 - 在webtask_queue中执行"""
    user_id = event.source.user_id
    reply_token = event.reply_token

    # 获取用户版本
    read_user()
    ver = "jp"
    if user_id in USERS and 'version' in USERS[user_id]:
        ver = USERS[user_id]['version']

    reply_msg = get_friends_list_buttons(user_id, ver)
    smart_reply(user_id, reply_token, reply_msg, configuration, DIVIDER)

def maimai_update(user_id, ver="jp"):
    messages = []
    func_status = {
        "User Info": True,
        "Best Records": True,
        "Recent Records": True
    }

    read_user()

    if user_id not in USERS:
        return segaid_error

    elif 'sega_id' not in USERS[user_id] or 'sega_pwd' not in USERS[user_id]:
        return segaid_error

    sega_id = USERS[user_id]['sega_id']
    sega_pwd = USERS[user_id]['sega_pwd']

    user_session = login_to_maimai(sega_id, sega_pwd, ver)
    if user_session == None:
        return segaid_error
    if user_session == "MAINTENANCE":
        return maintenance_error

    user_info = get_maimai_info(user_session, ver)
    maimai_records = get_maimai_records(user_session, ver)
    recent_records = get_recent_records(user_session, ver)

    # 检查记录是否处于维护状态
    if maimai_records == "MAINTENANCE" or recent_records == "MAINTENANCE":
        return maintenance_error

    error = False

    if user_info:
        USERS[user_id]['personal_info'] = user_info
        write_user()
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

    details = "詳しい情報："
    for func, status in func_status.items():
        details += f"\n「{func}」Error" if not status else ""

    if not error:
        messages.append(update_over)
    else:
        messages.append(update_error)
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

def search_song(acronym, ver="jp"):
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
    if not matching_songs:
        return song_error

    # 生成消息列表
    result = []
    for song in matching_songs:
        image_url = smart_upload(song_info_generate(song))
        message = ImageMessage(original_content_url=image_url, preview_image_url=image_url)
        result.append(message)

    return result

def random_song(key="", ver="jp"):
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
        return song_error

    song = random.choice(valid_songs)

    image_url = smart_upload(song_info_generate(song))
    result = ImageMessage(original_content_url=image_url, preview_image_url=image_url)

    return result

def get_friends_list_buttons(user_id, ver="jp"):
    read_user()
    if user_id not in USERS:
        return segaid_error

    elif 'sega_id' not in USERS[user_id] or 'sega_pwd' not in USERS[user_id]:
        return segaid_error

    sega_id = USERS[user_id]['sega_id']
    sega_pwd = USERS[user_id]['sega_pwd']

    user_session = login_to_maimai(sega_id, sega_pwd, ver)
    if user_session == None:
        return segaid_error
    if user_session == "MAINTENANCE":
        return maintenance_error

    friends_list = get_friends_list(user_session, ver)

    return generate_friend_buttons("フレンドリスト・Friends List", format_favorite_friends(friends_list))


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
        return record_error

    # 使用优化的歌曲匹配函数
    matching_songs = find_matching_songs(acronym, SONGS, max_results=6, threshold=0.85)

    if not matching_songs:
        return song_error

    result = []

    # 对每首匹配的歌曲,查找用户的游玩记录
    for song in matching_songs:
        played_data = []

        # 使用优化的精确匹配函数
        for rcd in song_record:
            if is_exact_song_title_match(rcd['name'], song['title']) and rcd['kind'] == song['type']:
                rcd['rank'] = ""
                played_data.append(rcd)

        # 如果该歌曲没有游玩记录,跳过
        if not played_data:
            continue

        image_url = smart_upload(song_info_generate(song, played_data))
        message = ImageMessage(original_content_url=image_url, preview_image_url=image_url)
        result.append(message)

    # 没有找到任何有记录的歌曲,或结果过多
    if len(result) == 0 or len(result) > 6:
        result = song_error

    return result

def generate_plate_rcd(user_id, title, ver="jp"):
    if not (len(title) == 2 or len(title) == 3):
        return plate_error

    read_user()
    read_dxdata(ver)

    song_record = read_record(user_id)

    if not len(song_record):
        return record_error

    version_name = title[0]
    plate_type = title[1:]

    target_version = []
    target_icon = []
    target_type = ""

    for version in VERSIONS :
        if version_name in version['abbr'] :
            target_version.append(version['version'])

    if not len(target_version) :
        return version_error

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
        return plate_error

    version_rcd_data = list(filter(lambda x: x['version'] in target_version, song_record))
    if not version_rcd_data:
        return version_error

    target_data = []
    target_num = {
        'basic': {'all': 0, 'clear': 0},
        'advanced': {'all': 0, 'clear': 0},
        'expert': {'all': 0, 'clear': 0},
        'master': {'all': 0, 'clear': 0}
    }

    for song in SONGS :
        if song['version'] not in target_version or song['type'] == 'utage':
            continue

        for sheet in song['sheets'] :
            if not sheet['regions']['jp'] or sheet["difficulty"] not in target_num:
                continue

            icon = "back"
            target_num[sheet['difficulty']]['all'] += 1
            for rcd in version_rcd_data:
                # 使用优化的精确匹配函数
                if is_exact_song_title_match(rcd['name'], song['title']) and sheet['difficulty'] == rcd['difficulty'] and rcd['kind'] == song['type']:
                    icon = rcd[f'{target_type}_icon']
                    if icon in target_icon:
                        target_num[sheet['difficulty']]['clear'] += 1

            if sheet['difficulty'] == "master" :
                target_data.append({"img": create_small_record(song['cover_url'], icon, target_type), "level": sheet['level']})

    img = generate_plate_image(target_data, title, headers = target_num)

    img = combine_with_rounded_background(create_user_info_img(user_id), img)

    image_url = smart_upload(img)
    message = ImageMessage(original_content_url=image_url, preview_image_url=image_url)

    return message

def create_user_info_img(user_id, scale=1.5):
    read_user()

    user_info = USERS[user_id]['personal_info']

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

            except Exception as e:
                print(f"加载图片失败 {user_info[key]}: {e}")

    paste_image("nameplate_url", (0, 0), (802, 128))

    paste_image("icon_url", (15, 13), (100, 100))

    paste_image("rating_block_url", (129, 13), (131, 34))
    draw.text((188, 17), f"{user_info['rating']}", fill=(255, 255, 255), font=font_large)

    draw.rectangle([129, 51, 129 + 266, 51 + 33], fill=(255, 255, 255))
    draw.text((135, 54), user_info['name'], fill=(0, 0, 0), font=font_large)

    paste_image("class_rank_url", (296, 10), (61, 37))

    paste_image("cource_rank_url", (322, 52), (75, 33))

    def trophy_color(type):
        return {
            "normal": (255, 255, 255),
            "bronze": (193, 102, 78),
            "silver": (186, 255, 251),
            "gold": (255, 243, 122),
            "rainbow": (233, 83, 106),
        }.get(type, (255, 255, 255))

    draw.rectangle([129, 92, 129 + 266, 92 + 21], fill=trophy_color(user_info['trophy_type']))
    draw.text((135, 93), user_info['trophy_content'], fill=(0, 0, 0), font=font_small)

    info_img = info_img.resize((int(img_width * scale), int(img_height * scale)), Image.LANCZOS)
    return info_img

def generate_maipass(user_id):
    read_user()
    if user_id not in USERS:
        return segaid_error

    user_info = USERS[user_id]["personal_info"]
    user_img = create_user_info_img(user_id)

    title_list = [
        "QRコードをスキャンして",
        "画像を『JiETNG』に送っても",
        "maimai フレンドになれるよ！",
        "\n",
        "Scan the QR code,",
        "or send the image to 'JiETNG',",
        "and we'll become maimai friends!"
    ]

    qr_img = generate_qr_with_title(f"https://jietng.matsuki.top/linebot/add_friend?code={user_info['friend_code']}", title_list)

    img = combine_with_rounded_background(user_img, qr_img)

    image_url = smart_upload(img)
    img_msg = ImageMessage(original_content_url=image_url, preview_image_url=image_url)
    message = [img_msg, share_msg]
    return message

def selgen_records(user_id, type="best50", command="", ver="jp"):
    read_user()

    if user_id not in USERS:
        return segaid_error

    song_record = read_record(user_id)
    if not len(song_record):
        return record_error

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
        recent_song_record = read_record(user_id, recent=True)
        if not len(recent_song_record):
            return record_error

        up_songs = recent_song_record

    elif type == "idealb50":
        for rcd in up_songs_data:
            ideal_score = get_ideal_score(float(rcd['score'][:-1]))
            rcd['score'] = f"{ideal_score:.4f}%"
            rcd['ra'] = get_single_ra(rcd['internalLevelValue'], ideal_score)

        for rcd in down_songs_data:
            ideal_score = get_ideal_score(float(rcd['score'][:-1]))
            rcd['score'] = f"{ideal_score:.4f}%"
            rcd['ra'] = get_single_ra(rcd['internalLevelValue'], ideal_score)

        up_songs = sorted(up_songs_data, key=lambda x: -x["ra"])[:35]
        down_songs = sorted(down_songs_data, key=lambda x: -x["ra"])[:15]

    if not up_songs or not down_songs:
        return picture_error

    img = generate_records_picture(up_songs, down_songs, type.upper())
    img = combine_with_rounded_background(create_user_info_img(user_id), img)

    image_url = smart_upload(img)
    message = ImageMessage(original_content_url=image_url, preview_image_url=image_url)
    return message

def generate_yang_rating(user_id, ver="jp"):
    song_record = read_record(user_id, yang=True)
    if not len(song_record):
        return record_error

    read_user()
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
    img = combine_with_rounded_background(create_user_info_img(user_id), img)

    image_url = smart_upload(img)
    message = ImageMessage(original_content_url=image_url, preview_image_url=image_url)
    return message

def generate_friend_b50(user_id, friend_code, ver="jp"):
    read_user()

    if user_id not in USERS :
        return segaid_error

    elif 'sega_id' not in USERS[user_id] or 'sega_pwd' not in USERS[user_id] :
        return segaid_error

    sega_id = USERS[user_id]['sega_id']
    sega_pwd = USERS[user_id]['sega_pwd']

    user_session = login_to_maimai(sega_id, sega_pwd, ver)
    if user_session == None:
        return segaid_error
    if user_session == "MAINTENANCE":
        return maintenance_error

    friend_name, song_record = get_friend_records(user_session, friend_code, ver)

    if not friend_name or not song_record:
        return friend_rcd_error

    song_record = get_detailed_info(song_record, ver)

    up_songs_data = list(filter(lambda x: x['new_song'] == False, song_record))
    down_songs_data = list(filter(lambda x: x['new_song'] == True, song_record))

    up_songs = sorted(up_songs_data, key=lambda x: -x["ra"])[:35]
    down_songs = sorted(down_songs_data, key=lambda x: -x["ra"])[:15]

    img = generate_records_picture(up_songs, down_songs, "FRD-B50")
    img = wrap_in_rounded_background(img)

    image_url = smart_upload(img)
    message = [
        TextMessage(text=f"「{friend_name}」さんの Best 50"),
        ImageMessage(original_content_url=image_url, preview_image_url=image_url)
    ]
    return message

def generate_level_records(user_id, level, ver="jp", page=1):
    read_user()

    song_record = read_record(user_id)

    if not len(song_record):
        return record_error

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
        return TextMessage(text=f"指定されたレベル {level} の譜面記録は存在しないかも...")

    title = f"LV{level} #{page}"

    img = generate_records_picture(up_level_list, down_level_list, title)

    img = combine_with_rounded_background(create_user_info_img(user_id), img)

    image_url = smart_upload(img)
    message = ImageMessage(original_content_url=image_url, preview_image_url=image_url)
    return message

def generate_version_songs(version_title, ver="jp"):
    read_dxdata(ver)

    target_version = []
    target_icon = []
    target_type = ""

    for version in VERSIONS :
        if version_title.lower() == version['version'].lower() :
            target_version.append(version['version'])

    if not len(target_version) :
        return version_error

    songs_data = list(filter(lambda x: x['version'] in target_version and x['type'] not in ['utage'], SONGS))
    img = generate_version_list(songs_data)

    image_url = smart_upload(img)
    message = ImageMessage(original_content_url=image_url, preview_image_url=image_url)
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
        "アップデート": async_maimai_update_task,
        "friend list": async_friend_list_task,
        "フレンドリスト": async_friend_list_task,
        "friendlist": async_friend_list_task
    },
    # 前缀匹配规则
    'prefix': {
        "friend-b50 ": async_generate_friend_b50_task,
        "friend b50 ": async_generate_friend_b50_task,
        "フレンドb50 ": async_generate_friend_b50_task,
        "add-friend ": async_add_friend_task,
        "add friend ": async_add_friend_task,
        "addfriend ": async_add_friend_task,
        "フレンド追加 ": async_add_friend_task,
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
            smart_reply(user_id, event.reply_token, rate_limit_msg, configuration, DIVIDER)
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
            smart_reply(user_id, event.reply_token, access_error, configuration, DIVIDER)
            return True

    # 检查前缀匹配的web任务
    for prefix, task_func in WEB_TASK_ROUTES['prefix'].items():
        if user_message.startswith(prefix):
            # 频率限制检查
            if check_rate_limit(user_id, task_func.__name__):
                smart_reply(user_id, event.reply_token, rate_limit_msg, configuration, DIVIDER)
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
                smart_reply(user_id, event.reply_token, access_error, configuration, DIVIDER)
                return True

    # 不是web任务,返回False
    return False

# 图片生成任务路由规则
IMAGE_TASK_ROUTES = {
    # 精确匹配规则 - 这些命令会生成图片
    'exact': {
        "yang", "yrating", "yra", "ヤンレーティング",
        "maid card", "maid", "mai pass", "maipass", "マイパス", "マイカード"
    },
    # 前缀匹配规则
    'prefix': [],
    # 后缀匹配规则
    'suffix': [
        ("ってどんな曲", "info", "song-info"),
        ("の達成状況", "の達成情報", "の達成表", "achievement-list", "achievement"),
        ("のレコード", "song-record", "record"),
        ("のバージョンリスト", "version-list", "version")
    ],
    # B系列命令 (生成图片)
    'b_commands': {
        "b50", "best50", "best 50", "ベスト50",
        "b100", "best100", "best 100", "ベスト100",
        "b35", "best35", "best 35", "ベスト35",
        "b15", "best15", "best 15", "ベスト15",
        "ab50", "allb50", "all best 50", "オールベスト50",
        "ab35", "allb35", "all best 35", "オールベスト35",
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
            smart_reply(user_id, event.reply_token, rate_limit_msg, configuration, DIVIDER)
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
            smart_reply(user_id, event.reply_token, access_error, configuration, DIVIDER)
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
                    smart_reply(user_id, event.reply_token, access_error, configuration, DIVIDER)
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
            smart_reply(user_id, event.reply_token, access_error, configuration, DIVIDER)
            return True

    # 检查 B 系列命令
    first_word = re.split(r"[ \n]", user_message.lower(), 1)[0]
    if first_word in IMAGE_TASK_ROUTES['b_commands']:
        # 频率限制检查 - B系列命令使用统一的限制
        if check_rate_limit(user_id, "image:b_series"):
            smart_reply(user_id, event.reply_token, rate_limit_msg, configuration, DIVIDER)
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
            smart_reply(user_id, event.reply_token, access_error, configuration, DIVIDER)
            return True

    # 检查 ランダム曲 / random-song
    if user_message.startswith(("ランダム曲", "random-song")):
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
            smart_reply(user_id, event.reply_token, access_error, configuration, DIVIDER)
            return True

    # 不是图片生成任务
    return False

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

def async_generate_image_task(event):
    """异步图片生成任务 - 在image_queue中执行"""
    handle_sync_text_command(event)

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
    id_use = user_id
    mai_ver = "jp"
    read_user()
    if user_id in USERS:
        if 'version' in USERS[user_id]:
            mai_ver = USERS[user_id]['version']

    # ====== 基础命令映射 ======
    COMMAND_MAP = {
        # 系统检查
        "check": lambda: active_reply,
        "チェック": lambda: active_reply,
        "network": lambda: active_reply,
        "ネットワーク": lambda: active_reply,

        # 账户管理
        "unbind": lambda: (delete_user(user_id), unbind_msg)[-1],
        "アンバインド": lambda: (delete_user(user_id), unbind_msg)[-1],
        "get me": lambda: TextMessage(text=get_user(user_id)),
        "getme": lambda: TextMessage(text=get_user(user_id)),
        "ゲットミー": lambda: TextMessage(text=get_user(user_id)),

        # Yang Rating
        "yang": lambda: generate_yang_rating(id_use, mai_ver),
        "yrating": lambda: generate_yang_rating(id_use, mai_ver),
        "yra": lambda: generate_yang_rating(id_use, mai_ver),
        "ヤンレーティング": lambda: generate_yang_rating(id_use, mai_ver),

        # 名片生成
        "maid card": lambda: generate_maipass(user_id),
        "maid": lambda: generate_maipass(user_id),
        "mai pass": lambda: generate_maipass(user_id),
        "maipass": lambda: generate_maipass(user_id),
        "マイパス": lambda: generate_maipass(user_id),
        "マイカード": lambda: generate_maipass(user_id)
    }

    if user_message in COMMAND_MAP:
        reply_message = COMMAND_MAP[user_message]()
        return smart_reply(user_id, event.reply_token, reply_message, configuration, DIVIDER)

    # ====== 模糊匹配规则 ======
    SPECIAL_RULES = [
        # 歌曲信息查询
        (lambda msg: msg.endswith(("ってどんな曲", "info", "song-info")),
        lambda msg: search_song(
            re.sub(r"(ってどんな曲|info|song-info)$", "", msg).strip(),
            mai_ver
        )),

        # 随机歌曲
        (lambda msg: msg.startswith(("ランダム曲", "random-song", "random")),
        lambda msg: random_song(
            re.sub(r"^(ランダム曲|random-song|random)", "", msg).strip(),
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
            re.sub(r"(の達成状況|の達成情報|の達成表|achievement-list|achievement)$", "", msg).strip(),
            mai_ver
        )),

        # 歌曲成绩记录
        (lambda msg: msg.endswith(("のレコード", "song-record", "record")),
        lambda msg: get_song_record(
            id_use,
            re.sub(r"(のレコード|song-record|record)$", "", msg).strip(),
            mai_ver
        )),

        # 等级成绩列表
        (lambda msg: re.match(r".+(のレコードリスト|record-list|records)[ 　]*\d*$", msg),
        lambda msg: generate_level_records(
            id_use,
            re.sub(r"(のレコードリスト|record-list|records)[ 　]*\d*$", "", msg).strip(),
            mai_ver,
            int(re.search(r"(\d+)$", msg).group(1)) if re.search(r"(\d+)$", msg) else 1
        )),

        # 版本歌曲列表
        (lambda msg: msg.endswith(("のバージョンリスト", "version-list", "version")),
        lambda msg: generate_version_songs(
            re.sub(r"\s*\+\s*", " PLUS", re.sub(r"(のバージョンリスト|version-list|version)$", "", msg)).strip(),
            mai_ver
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
        ("ab50", "allb50", "all best 50", "オールベスト50"): "allb50",
        ("ab35", "allb35", "all best 35", "オールベスト35"): "allb35",
        ("ap50", "apb50", "all perfect 50", "オールパーフェクト50"): "apb50",
        ("rct50", "r50", "recent50", "recent 50"): "rct50",
        ("idealb50", "idlb50", "ideal best 50", "理想的ベスト50"): "idealb50",
        ("unknown", "unknown songs", "unknown data", "未発見"): "UNKNOWN",
    }

    for aliases, mode in RANK_COMMANDS.items():
        if first_word in aliases:
            reply_message = selgen_records(id_use, mode, rest_text, mai_ver)
            return smart_reply(user_id, event.reply_token, reply_message, configuration, DIVIDER)

    # ====== SEGA ID 绑定逻辑 ======
    BIND_COMMANDS = ["segaid bind", "segaid バインド", "sega bind", "sega バインド", "bind", "バインド"]
    if user_message.lower() in BIND_COMMANDS:
        bind_url = f"https://{DOMAIN}/linebot/sega_bind?token={generate_token(user_id)}"

        buttons_template = ButtonsTemplate(
            title='SEGA アカウント連携',
            text='SEGA アカウントと連携されます\n有効期限は発行から2分間です',
            actions=[URIAction(label='押しで連携', uri=bind_url)]
        )
        reply_message = TemplateMessage(
            alt_text='SEGA アカウント連携',
            template=buttons_template
        )

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
            reply_message = input_error
        return smart_reply(user_id, event.reply_token, reply_message, configuration, DIVIDER)

    # ====== 管理员命令 ======
    if user_id in ADMIN_ID:
        if user_message.startswith("upload notice"):
            new_notice = user_message.replace("upload notice", "").strip()
            upload_notice(new_notice)
            edit_user_status_of_all("notice_read", False)
            return smart_reply(user_id, event.reply_token, notice_upload, configuration, DIVIDER)

        if user_message == "dxdata update":
            # 使用新的对比更新函数
            result = update_dxdata_with_comparison(DXDATA_URL, DXDATA_LIST)
            read_dxdata()  # 重新加载到内存

            reply_message = TextMessage(text=result['message'])

            # 回复执行命令的管理员
            smart_reply(user_id, event.reply_token, reply_message, configuration, DIVIDER)

            # 推送通知给所有其他管理员
            notification_message = TextMessage(text=f"📢 Dxdata 更新通知\n\n{result['message']}")
            for admin_user_id in ADMIN_ID:
                if admin_user_id != user_id:  # 不重复发送给执行命令的管理员
                    try:
                        smart_push(admin_user_id, notification_message, configuration)
                    except Exception as e:
                        logger.error(f"Failed to notify admin {admin_user_id}: {e}")

            return

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

    qr_results = decode(image)

    reply_msg = []

    if qr_results:
        for qr in qr_results:
            data = qr.data.decode("utf-8")
            new_reply_msg = handle_image_message_task(event.source.user_id, event.reply_token, data)
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
        smart_reply(
            event.source.user_id,
            event.reply_token,
            qrcode_error,
            configuration,
            DIVIDER
        )

def handle_image_message_task(user_id, reply_token, data):
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

    URL_MAP = [
        (
            lambda content, domain: re.match(
                rf"^(?:https?://)?{re.escape(domain)}/linebot/add_friend\?code=",
                content
            ),

            lambda content, user_id, reply_token, domain, mai_ver: add_friend_with_params(
                user_id,
                re.sub(
                    rf"^(?:https?://)?{re.escape(domain)}/linebot/add_friend\?code=",
                    "",
                    content
                ).strip(),
                mai_ver
            )
        ),
    ]

    for condition, action in URL_MAP:
        if condition(data, DOMAIN):
            return action(data, user_id, reply_token, DOMAIN, mai_ver)
        else:
            return TextMessage(text=data)


#位置信息处理
@handler.add(MessageEvent, message=LocationMessageContent)
def handle_location_message(event):
    """
    位置消息处理 - 同步处理
    """
    read_user()

    lat = event.message.latitude
    lng = event.message.longitude
    user_id = event.source.user_id

    stores = get_nearby_maimai_stores(lat, lng, USERS[user_id]['version'])
    if not stores:
        reply_message = TextMessage(text="🥹 周辺の設置店舗がないね")
    else:
        reply_message = [TextMessage(text="🗺️ 最寄りの maimai 設置店舗")]
        for i, store in enumerate(stores[:4]):
            reply_message.append(TextMessage(text=f"📌 {store['name']}\n{store['address']}\n（{store['distance']}）\n地図: {store['map_url']}"))

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
    """
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        from modules.user_console import get_user_nickname
        return get_user_nickname(user_id, line_bot_api, use_cache)

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
        from modules.notice_console import get_all_notices
        notices = get_all_notices()
        return jsonify({'success': True, 'notices': notices})
    except Exception as e:
        logger.error(f"Admin get notices error: {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route("/linebot/admin/create_notice", methods=["POST"])
def admin_create_notice():
    """创建新公告"""
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    content = data.get('content', '').strip()

    if not content:
        return jsonify({'success': False, 'message': 'Content is required'}), 400

    try:
        from modules.notice_console import upload_notice
        notice_id = upload_notice(content)
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
        from modules.notice_console import update_notice
        success = update_notice(notice_id, content)

        if success:
            logger.info(f"Admin updated notice: {notice_id}")
            return jsonify({'success': True, 'message': 'Notice updated successfully'})
        else:
            return jsonify({'success': False, 'message': 'Notice not found'}), 404

    except Exception as e:
        logger.error(f"Admin update notice error: {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route("/linebot/admin/delete_notice", methods=["POST"])
def admin_delete_notice():
    """删除公告"""
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    notice_id = data.get('notice_id')

    if not notice_id:
        return jsonify({'success': False, 'message': 'Notice ID is required'}), 400

    try:
        from modules.notice_console import delete_notice
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
        from modules.user_console import delete_user
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

if __name__ == "__main__":
    # 启动内存管理器
    memory_manager.start()
    logger.info("Memory manager started successfully")

    # 注册清理函数（在内存管理器的清理循环中调用）
    def custom_cleanup():
        """自定义清理函数"""
        try:
            # 清理用户昵称缓存
            cleaned_nicknames = cleanup_user_caches(user_console_module)

            # 清理频率限制追踪数据
            cleaned_rate_limits = cleanup_rate_limiter_tracking(rate_limiter_module)

            logger.debug(f"Custom cleanup: {cleaned_nicknames} nicknames, {cleaned_rate_limits} rate limit entries")
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
