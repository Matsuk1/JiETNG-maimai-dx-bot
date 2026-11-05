"""
JiETNG Maimai DX LINE Bot 主程序
"""

import os
import random
import json
import re
import traceback
import threading
import queue
import psutil
import platform
import socket
import asyncio
import aiohttp
import atexit
import time
import math
import binascii
import base64 as b64mod
import secrets
from urllib.parse import urlencode

from datetime import datetime
from types import SimpleNamespace

from io import BytesIO

from flask import (
    Flask,
    request,
    render_template,
    redirect,
    session,
    jsonify,
    send_file,
    send_from_directory,
)
from flask_wtf.csrf import CSRFProtect
from modules.session_key import load_session_key

from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    MessagingApiBlob,
    TextMessage,
    ImageMessage,
)
from linebot.v3.messaging.models import (
    MarkMessagesAsReadByTokenRequest,
    ShowLoadingAnimationRequest,
)
from linebot.v3.webhooks import (
    FollowEvent,
    UnfollowEvent,
    MessageEvent,
    PostbackEvent,
    JoinEvent,
    MemberJoinedEvent,
    TextMessageContent,
    LocationMessageContent
)

# Song and record generators
from modules.images.songs import (
    generate_version_list,
    song_info_generate,
)
from modules.images.records import (
    build_plate_entries,
    build_progress_entries,
    generate_level_rank_progress_image,
    generate_plate_image,
    generate_records_picture,
    generate_score_recognition_picture,
)

# User and data managers
from modules.user_manager import (
    add_user,
    delete_user,
    edit_user_value,
    get_user_nickname,
    get_user_timezone,
    record_notice_vote,
)
from modules.user_db import (
    save_user, get_user, user_exists,
    get_user_field, load_all_users,
)
from modules.bindtoken_manager import (
    generate_bind_token, get_user_id_from_token,
    generate_perm_token, get_user_id_from_perm_token,
    generate_settings_token, get_user_id_from_settings_token,
    generate_unbind_token, get_user_id_from_unbind_token,
)
from modules.notice_manager import calculate_notice_stats, get_notice_by_id, load_tip_ad_data
from modules.maimai_manager import (
    fetch_dom,
    get_aime_candidates,
    get_friend_info,
    get_friend_records,
    get_friends_list,
    get_maimai_info,
    get_maimai_records,
    get_nearby_maimai_stores,
    get_rating_image_path,
    get_recent_records,
    get_single_record,
    limit_maimai_operation_duration,
    login_to_maimai,
    MaimaiServiceTimeout,
)
from modules.score_calculator import get_note_score
from modules.dxdata_manager import start_weekly_update_scheduler as start_dxdata_weekly_update
from modules.record_manager import (
    PLATE_RULES,
    PROGRESS_RANKS,
    SUPPORTED_PROGRESS_LEVELS,
    achievement_value,
    filter_progress_entries,
    get_detailed_info,
    get_ideal_score,
    get_single_ra,
    read_record,
    write_record,
)
from modules.devtoken_manager import (
    load_dev_tokens,
    save_dev_tokens,
    flush_dev_tokens
)

from modules.perm_request_handler import accept_perm_request, reject_perm_request

from modules.config_loader import (
    BG_DIR,
    DOMAIN,
    DXDATA_FILE,
    DXDATA_URL,
    EXPORT_DIR,
    HOST,
    IMG_DIR,
    LINE_ADDING_URL,
    LINE_CHANNEL_ACCESS_TOKEN,
    LINE_CHANNEL_SECRET,
    LIFF_CHANNEL_ID,
    LIFF_ENABLED,
    LIFF_ID,
    LOG_FILE,
    MAIMAI_VERSION,
    PLUGIN_CONFIG,
    PORT,
    TEMP_VERSION,
    load_user,
    read_dxdata,
)
from modules.liff_urls import build_account_action_url
from modules.liff_auth import verify_liff_id_token

from modules.messages.service import (
    access_error,
    cannot_do_for_others,
    friend_error,
    friend_rcd_error,
    generate_account_action_flex,
    generate_bot_status_flex,
    generate_calc_carousel,
    generate_calc_result_flex,
    generate_export_flex,
    generate_friend_buttons,
    generate_ranking_flex,
    generate_rc_flex,
    generate_search_results_flex,
    generate_song_image_message,
    generate_song_list_flex,
    generate_status_flex,
    generate_update_result_flex,
    generate_user_info_flex,
    generate_welcome_flex,
    get_friend_list_alt_text,
    get_nearby_stores_alt_text,
    info_error,
    input_error,
    level_not_supported,
    level_record_not_found,
    level_record_page_hint,
    maintenance_error,
    mention_error,
    mention_not_allowed,
    mention_no_matching_data,
    mention_record_error,
    no_matching_data,
    plate_error,
    rate_limit_msg,
    rebind_msg,
    record_error,
    segaid_error,
    song_error,
    store_error,
    system_error,
    system_error_text,
    version_error,
)
from modules.messages.scores import generate_score_recognition_flex
from modules.i18n import (
    select_text as get_multilingual_text,
    get_user_language,
    error_page as _error_page,
    register_web_i18n,
    DEFAULT_LANGUAGE,
    DEFAULT_WEB_LANGUAGE,
    format_catalog,
    language_catalog,
    normalize_language,
    select_text,
)

# Image processing
from modules.images.upload import upload_generated_image, _start_periodic_cleanup, _encode_jpeg
from modules.export_manager import (
    export_records,
    shutdown_periodic_cleanup as shutdown_export_cleanup,
    start_periodic_cleanup as start_export_cleanup,
)
from modules.import_token_manager import (
    create_import_token,
    delete_revoked_import_token,
    list_import_tokens,
    revoke_import_token,
)
from modules.api.api_auth import maimai_session_cors as _maimai_session_cors
from modules.logging_config import configure_logging
from modules.commands.command_router import (
    Exact, Prefix, Regex, FirstWord,
    Command, CommandContext,
    QUEUE_SYNC, QUEUE_IMAGE, QUEUE_WEB,
)
from modules.plugin_manager import dispatch_plugin_session, load_plugin_commands
from modules.commands.command_parsers import (
    parse_fix_record_command,
    format_bpm_number,
    parse_bpm_number,
    parse_bpm_query,
    parse_filter_mode,
    parse_level_records_query,
    parse_note_counts,
    parse_paginated_keyword,
    parse_plate_query,
    PROGRESS_RANK_PATTERN,
    parse_level_rank_progress as _parse_level_rank_progress_text,
    resolve_progress_category as _resolve_progress_category,
)
from modules.dbpool_manager import close_pool
from modules.images.skins import DEFAULT_USER_SKIN, available_skins, normalize_skin, user_image, user_skin
from modules.images.composition import compose_generated_images

# System utilities
from modules.system_checker import run_system_check, clean_unbound_users
from modules.event_tracker import (
    get_business_stats,
    shutdown_event_tracker,
    track_event,
)
from modules.line_messenger import smart_reply, smart_push, notify_admins_error, notify_on_error
from modules.rich_menu_manager import (
    link_bound_rich_menu,
    link_rich_menu_for_state,
    link_unbound_rich_menu,
    unlink_rich_menu,
)
from modules.song_matcher import find_matching_songs
from modules.memory_manager import memory_manager, cleanup_user_caches, get_process_memory_stats
from modules.score_recognition.results import expand_score_recognition_calc_variants
from modules.score_recognition.recognizer import (
    InvalidScoreImageError,
    build_score_crop_preview_image,
    cleanup_score_recognizer_memory,
    initialize_score_recognizer,
    recognize_score_image_bytes,
    recognize_score_with_ai,
    score_recognition_needs_manual_fix,
    validate_recognized_judgement,
)
from modules.commands.command_config import (
    MAX_SEARCH_RESULTS,
    RANK_COMMANDS,
    rank_command_words,
)
from modules.commands.command_help import (
    HELP_INDEX_WORDS,
    HIDDEN_HELP_COMMAND_WORDS,
    command_help_message as _command_help_message,
    detect_command_help_key,
    detect_missing_param_help_key as _detect_missing_param_help_key,
)
from modules.task_runtime import (
    check_rate_limit,
    cleanup_rate_limiter_tracking,
    TaskOutcome,
    discard_queued,
    summarize_task_activity,
    execute_task,
    queue_worker,
    track_queued,
)
from modules.api.song_api import song_api
from modules.api.image_api import configure_image_api, image_api
from modules.api.record_transfer_api import record_transfer_api
from modules.api.developer_api import cleanup_api_sync_locks, configure_developer_api, developer_api
from modules.api.score_api import create_score_api
from modules.api.admin_api import CSRF_EXEMPT_ENDPOINTS, admin_api, configure_admin_api
from modules.commands.mention_parser import (
    clean_message_text,
    has_non_bot_mention,
    registered_mentioned_user_id as extract_single_mention,
    should_ignore_mentions as check_mention_filter,
)
from modules.record_selector import select_records
from modules.image_orchestrator import (
    _compose_user_images,
    _download_line_message_content,
    _get_user_bg_filter,
    _missing_record_error,
    _record_user_or_error,
    _upload_image_message,
    generate_friend_record,
    generate_level_rank_progress,
    generate_level_records,
    generate_plate_rcd,
    generate_profile,
    generate_records,
    generate_version_songs,
    get_song_record,
    get_song_record_by_id,
    login_rate_limit_message,
    random_song,
    search_song,
    search_song_by_id,
)
from modules.query_handlers import (
    calc_by_id,
    get_ranking,
    get_rc,
    get_user_info,
    handle_export_command,
    handle_rc_command,
    search_by_artist,
    search_by_bpm,
    search_by_designer,
    _private_chat_warning,
)
from modules.commands.handlers import (
    _account_action_url,
    _can_open_settings,
    _check_private_or_warn,
    _has_full_account,
    cmd_artist,
    cmd_b_records,
    cmd_bind,
    cmd_bpm,
    cmd_calc_notes,
    cmd_designer,
    cmd_export,
    cmd_level_rank_list,
    cmd_level_rank_progress,
    cmd_level_records,
    cmd_plate,
    cmd_profile,
    cmd_random_song,
    cmd_ranking,
    cmd_rc,
    cmd_rebind,
    cmd_refresh_menu,
    cmd_settings,
    cmd_song_info,
    cmd_unbind_prompt,
    cmd_version_songs,
)

# Module aliases for specific use cases
import modules.user_manager as user_manager_module

from modules.storelist_generator import generate_store_buttons

# ==================== 常量定义 ====================

# 队列配置
MAX_QUEUE_SIZE = 10
MAX_CONCURRENT_IMAGE_TASKS = 5  # 图片生成并发数
IMAGE_QUERY_MAX_CONCURRENT_TASKS = int(os.getenv("IMAGE_QUERY_MAX_CONCURRENT_TASKS", "1"))  # 图片查询/识别并发数
WEB_MAX_CONCURRENT_TASKS = 2    # 网络任务并发数
TASK_TIMEOUT_SECONDS = 120

SCORE_RECOGNITION_API_MAX_IMAGE_BYTES = int(
    os.getenv("SCORE_RECOGNITION_API_MAX_IMAGE_BYTES", 20 * 1024 * 1024)
)
ALLOWED_BACKGROUND_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".heic", ".heif"}
MAX_BACKGROUND_BYTES = 5 * 1024 * 1024

# ==================== 日志配置 ====================

logger = configure_logging(LOG_FILE, __name__)

app = Flask(__name__, static_folder='assets', static_url_path='/static')
app.secret_key = load_session_key()
register_web_i18n(app)

# 启用 CSRF 保护
csrf = CSRFProtect(app)
csrf.exempt(song_api)
app.register_blueprint(song_api)
csrf.exempt(image_api)
app.register_blueprint(image_api)
csrf.exempt(record_transfer_api)
app.register_blueprint(record_transfer_api)
csrf.exempt(developer_api)
app.register_blueprint(developer_api)
score_api = create_score_api(SCORE_RECOGNITION_API_MAX_IMAGE_BYTES)
csrf.exempt(score_api)
app.register_blueprint(score_api)
app.register_blueprint(admin_api)
for endpoint in CSRF_EXEMPT_ENDPOINTS:
    csrf.exempt(app.view_functions[f"admin_api.{endpoint}"])

# 配置安全响应头
@app.after_request
def set_security_headers(response):
    """设置安全响应头 + 内存清理"""
    # 防止 XSS 攻击
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'

    # Content Security Policy. The LIFF bootstrap alone may load LINE's SDK
    # and contact LINE endpoints; keep every other page on the stricter policy.
    if request.path.rstrip('/') == '/linebot/liff':
        script_src = "'self' 'unsafe-inline' https://static.line-scdn.net"
        connect_src = "'self' https://*.line.me https://*.line-scdn.net"
    else:
        script_src = "'self' 'unsafe-inline'"
        connect_src = "'self'"
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        f"script-src {script_src}; "
        f"connect-src {connect_src}; "
        "img-src 'self' data: blob: https:; "
        "font-src 'self' data:;"
    )

    # Strict Transport Security (如果使用 HTTPS)
    # response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

    return response

# 记录服务启动时间和统计
SERVICE_START_TIME = datetime.now()

# 使用字典存储统计数据,避免 global 变量问题
STATS = {
    'tasks_processed': 0,
    'tasks_failed': 0,
    'tasks_timed_out': 0,
}
stats_lock = threading.Lock()  # 保护统计数据的线程锁

# ==================== 任务队列系统 ====================

# 图片生成任务队列 (处理图片生成任务，如 b50 等)
image_queue = queue.Queue(maxsize=MAX_QUEUE_SIZE)
image_concurrency_limit = threading.Semaphore(MAX_CONCURRENT_IMAGE_TASKS)

# 图片查询任务队列 (处理成绩图 OCR / 裁切预览等)
image_query_queue = queue.Queue(maxsize=MAX_QUEUE_SIZE)
image_query_concurrency_limit = threading.Semaphore(IMAGE_QUERY_MAX_CONCURRENT_TASKS)

# Web任务队列 (处理耗时的网络请求，如 maimai_update 等)
webtask_queue = queue.Queue(maxsize=MAX_QUEUE_SIZE)
webtask_concurrency_limit = threading.Semaphore(WEB_MAX_CONCURRENT_TASKS)


def _handle_task_error(func, error, context, traceback_text):
    is_maimai_service_timeout = isinstance(error, MaimaiServiceTimeout)
    if not is_maimai_service_timeout:
        notify_admins_error(
            error_title=f"Task Execution Failed: {func.__name__}",
            error_details=f"{type(error).__name__}: {error}\n\n{traceback_text}",
            context={"Task": func.__name__, "Error Type": type(error).__name__},
            user_id=context.user_id,
        )
    if context.user_id and context.reply_token:
        try:
            reply = (
                generate_status_flex(
                    language_catalog("main.query_failed_title"),
                    language_catalog("main.maimai_service_busy_body"),
                    context.user_id,
                    tone="danger",
                )
                if is_maimai_service_timeout
                else system_error(context.user_id)
            )
            smart_reply(
                context.user_id,
                context.reply_token,
                reply,
                configuration,
                addition=False,
                source_type=context.source_type,
            )
        except Exception as exc:
            logger.warning("[Task] Error reply failed: user_id=%s error=%s", context.user_id, exc)


def _complete_task(func, outcome: TaskOutcome):
    with stats_lock:
        STATS["tasks_processed"] += 1
        if outcome.status == "failed":
            STATS["tasks_failed"] += 1
        elif outcome.status == "timed_out":
            STATS["tasks_timed_out"] += 1
        logger.info(
            "[Task] Finished: function=%s, status=%s, duration=%.3fs, total=%s",
            func.__name__,
            outcome.status,
            outcome.duration,
            STATS["tasks_processed"],
        )


def _execute_queued_task(item, semaphore):
    func, args, task_id = item if len(item) == 3 else (*item, None)
    execute_task(
        func,
        args,
        semaphore,
        task_id=task_id,
        tracking=task_tracking,
        tracking_lock=task_tracking_lock,
        max_completed=MAX_COMPLETED_TASKS,
        timeout=TASK_TIMEOUT_SECONDS,
        logger=logger,
        on_error=_handle_task_error,
        on_complete=_complete_task,
    )


@notify_on_error("Image Task Worker Error", context={"Worker": "image_worker"}, reraise=False)
def _run_image_task(item):
    _execute_queued_task(item, image_concurrency_limit)


def image_worker() -> None:
    queue_worker(image_queue, _run_image_task)


@notify_on_error("Image Query Worker Error", context={"Worker": "image_query_worker"}, reraise=False)
def _run_image_query_task(item):
    _execute_queued_task(item, image_query_concurrency_limit)


def image_query_worker() -> None:
    queue_worker(image_query_queue, _run_image_query_task)


@notify_on_error("Web Task Worker Error", context={"Worker": "webtask_worker"}, reraise=False)
def _run_webtask(item):
    _execute_queued_task(item, webtask_concurrency_limit)


def webtask_worker() -> None:
    queue_worker(webtask_queue, _run_webtask)

configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# ==================== Flask 路由 ====================

@app.route("/linebot/webhook", methods=['POST'])
@csrf.exempt
def linebot_reply():
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)

    try:
        json_data = json.loads(body)
        destination = json_data.get("destination")
        request.destination = destination
        handler.handle(body, signature)
        # 签名校验通过后再追踪（避免把无效请求计入指标）
        for event_data in json_data.get("events", []):
            source = event_data.get("source", {})
            track_event("line_webhook", user_id=source.get("userId"),
                        metadata={"type": event_data.get("type")})

    except Exception as e:
        is_bad_request = isinstance(e, (json.JSONDecodeError, InvalidSignatureError))
        logger.error(f"[Webhook] ✗ {'Bad request' if is_bad_request else 'Handling error'}: error={e}", exc_info=not is_bad_request)

        # 尝试回复用户错误消息（非坏请求时，json_data 已解析成功）
        if not is_bad_request:
            try:
                events = json_data.get('events', [])
                if events:
                    ev = events[0]
                    reply_token = ev.get('replyToken')
                    uid = ev.get('source', {}).get('userId')
                    if reply_token and uid:
                        smart_reply(uid, reply_token, system_error(uid), configuration, addition=False)
            except Exception as reply_error:
                logger.warning("[Webhook] Error reply failed: %s", reply_error)

        events = json_data.get("events", []) if not is_bad_request else []
        first_event = events[0] if events and isinstance(events[0], dict) else {}
        event_source = first_event.get("source", {})
        notification_user_id = event_source.get("userId") if isinstance(event_source, dict) else None
        notify_admins_error(
            error_title="Webhook Error",
            error_details=f"{type(e).__name__}: {str(e)}\n\n{traceback.format_exc()}",
            context={"Error": type(e).__name__, "Detail": str(e)[:200]},
            user_id=notification_user_id,
        )

    return 'OK', 200

@app.route("/static/admin-icon.png")
def admin_pwa_icon():
    """Serve the cached HTML-rendered PWA icon."""
    from modules.images.composition import admin_icon_png
    website_logo = os.path.join(app.root_path, "assets", "pics", "logo.png")
    return send_file(BytesIO(admin_icon_png(website_logo)), mimetype='image/png')


@app.route("/sw.js")
def service_worker():
    """提供 Service Worker 文件（必须从根路径提供以控制 /admin/ 范围）"""
    response = app.send_static_file('sw.js')
    response.headers['Content-Type'] = 'application/javascript'
    response.headers['Service-Worker-Allowed'] = '/admin/'
    return response


@app.route("/linebot/adding", methods=["GET"])
@app.route("/linebot/add", methods=["GET"])
def line_add_page():
    """重定向到LINE添加好友页面"""
    return redirect(LINE_ADDING_URL)


@app.route("/linebot/img/<image_id>", methods=["GET"])
def serve_image(image_id):
    # 验证image_id格式（防止路径穿越攻击）
    if not image_id.replace('-', '').replace('_', '').isalnum():
        logger.warning(f"[ImageHost] ⚠ Invalid image_id format: id={image_id}")
        return send_from_directory('assets/pics', '404.png', mimetype='image/png'), 404

    filename = next(
        (name for name in (f"{image_id}.jpg", f"{image_id}.png") if os.path.exists(os.path.join(IMG_DIR, name))),
        None,
    )
    if not filename:
        logger.warning(f"[ImageHost] ⚠ Image not found: id={image_id}")
        return send_from_directory('assets/pics', '404.png', mimetype='image/png'), 404

    return send_from_directory(IMG_DIR, filename, mimetype='image/jpeg' if filename.endswith(".jpg") else 'image/png')


@app.route("/linebot/export/<file_id>/<friendly_name>", methods=["GET"])
def serve_export(file_id, friendly_name):
    # 防路径穿越：id 只允许 token_urlsafe 字符集（字母数字 + _ -）
    if not file_id.replace('-', '').replace('_', '').isalnum():
        logger.warning(f"[Export] ⚠ Invalid file_id: {file_id}")
        return ("Not Found", 404)

    # friendly_name 由 Flask 自动 url-decode；校验扩展名 + 无路径穿越字符
    if '/' in friendly_name or '\\' in friendly_name or '..' in friendly_name:
        return ("Bad Request", 400)
    _, _, ext = friendly_name.rpartition('.')
    if ext not in ('json', 'xml'):
        logger.warning(f"[Export] ⚠ Unsupported ext: {friendly_name}")
        return ("Not Found", 404)

    disk_name = f"{file_id}.{ext}"
    if not os.path.exists(os.path.join(EXPORT_DIR, disk_name)):
        logger.warning(f"[Export] ⚠ Export not found / expired: {disk_name}")
        return ("Gone", 410)

    mimetype = 'application/json' if ext == 'json' else 'application/xml'
    # download_name 走 friendly_name，浏览器另存为时直接是这个名字（含 CJK）
    return send_from_directory(
        EXPORT_DIR, disk_name, mimetype=mimetype,
        as_attachment=True, download_name=friendly_name,
    )


def _parse_int(value, default, minimum=None, maximum=None):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    if minimum is not None:
        parsed = max(minimum, parsed)
    return min(maximum, parsed) if maximum is not None else parsed


@app.route("/linebot/liff", methods=["GET"])
def website_liff_entry():
    """LIFF primary redirect endpoint; existing handlers remain secondary URLs."""
    if not LIFF_ENABLED:
        return ("LIFF is not configured", 404)
    return render_template("liff_bootstrap.html", liff_id=LIFF_ID)


@app.route("/linebot/liff/session", methods=["POST"])
@csrf.exempt
def website_liff_session():
    """Exchange a verified LIFF identity for the existing short-lived action URL."""
    trace_id = secrets.token_hex(4)
    data = request.get_json(silent=True) or {}
    action = str(data.get("action", ""))
    logger.info(
        "[LIFF] session start trace=%s action=%s has_id_token=%s",
        trace_id,
        action or "-",
        bool(data.get("id_token")),
    )

    if not LIFF_ENABLED or not LIFF_CHANNEL_ID:
        logger.error("[LIFF] session config missing trace=%s", trace_id)
        return jsonify({"error": "LIFF is not configured", "code": "SERVER_CONFIG"}), 503

    if action not in {"bind", "rebind", "settings", "unbind"}:
        logger.warning("[LIFF] invalid action trace=%s action=%s", trace_id, action or "-")
        return jsonify({"error": "Invalid action", "code": "INVALID_ACTION"}), 400

    try:
        user_id = verify_liff_id_token(str(data.get("id_token", "")), LIFF_CHANNEL_ID)
    except (ValueError, OSError) as error:
        logger.warning("[LIFF] verification failed trace=%s error=%s", trace_id, error)
        return jsonify({"error": "LIFF authentication failed", "code": "TOKEN_VERIFY"}), 401

    logger.info("[LIFF] identity verified trace=%s user_suffix=%s", trace_id, user_id[-6:])

    if action == "bind":
        if not user_exists(user_id):
            add_user(user_id)
        path = "/linebot/sega_bind"
        params = {"token": generate_bind_token(user_id)}
    else:
        user_data = get_user(user_id) or {}
        if action == "rebind":
            if not _has_full_account(user_data):
                logger.warning("[LIFF] rebind denied trace=%s reason=not_bound", trace_id)
                return jsonify({"error": "No linked SEGA account", "code": "NOT_BOUND"}), 403
            path = "/linebot/sega_bind"
            params = {"token": generate_bind_token(user_id), "mode": "rebind"}
        elif action == "settings":
            if not _can_open_settings(user_data):
                logger.warning("[LIFF] settings denied trace=%s reason=not_bound", trace_id)
                return jsonify({"error": "No linked account", "code": "NOT_BOUND"}), 403
            path = "/linebot/settings"
            params = {"token": generate_settings_token(user_id)}
        else:
            if not _can_open_settings(user_data):
                logger.warning("[LIFF] unbind denied trace=%s reason=not_bound", trace_id)
                return jsonify({"error": "No linked account", "code": "NOT_BOUND"}), 403
            path = "/linebot/unbind"
            params = {"token": generate_unbind_token(user_id)}

    redirect_url = f"{path}?{urlencode(params)}"
    logger.info("[LIFF] session issued trace=%s action=%s path=%s", trace_id, action, path)
    return jsonify({"redirect": redirect_url})


@app.route("/linebot/liff/client-log", methods=["POST"])
@csrf.exempt
def website_liff_client_log():
    """Record LIFF bootstrap failures that happen before session exchange."""
    data = request.get_json(silent=True) or {}
    stage = str(data.get("stage", "UNKNOWN"))[:40]
    code = str(data.get("code", "UNKNOWN"))[:80]
    message = str(data.get("message", ""))[:300].replace("\n", " ")
    logger.warning(
        "[LIFF] client failure stage=%s code=%s message=%s ua=%s",
        stage,
        code,
        message or "-",
        request.user_agent.string[:200],
    )
    return ("", 204)


@app.route("/linebot/sega_bind", methods=["GET", "POST"])
def website_segaid_bind():
    token = request.args.get("token")
    mode = request.args.get("mode", "bind")
    if not token:
        # Token 未提供的错误消息（此时还没有 user_id，三语同时显示）
        token_missing_message = language_catalog("main.token_missing")
        return _error_page(token_missing_message)

    try:
        user_id = get_user_id_from_token(token)
        if not user_exists(user_id):
            token_invalid_message = language_catalog("main.token_invalid")
            return _error_page(token_invalid_message)
        
    except Exception as e:
        logger.error(f"[Auth] ✗ Token verification failed: error={e}")
        token_invalid_message = language_catalog("main.token_invalid")
        return _error_page(token_invalid_message)

    if request.method == "POST":
        bind_type = request.form.get("bind_type", "sega")
        segaid = request.form.get("segaid")
        password = request.form.get("password")
        user_version = request.form.get("ver", "jp")
        if user_version not in ("jp", "intl"):
            user_version = "jp"
        aime = request.form.get("aime", "0")

        # 获取用户数据
        user_data = get_user(user_id) or {}

        if mode == "rebind":
            # rebind 模式下保持现有 timezone 和 language 不变
            user_timezone = str(user_data.get("timezone", 9))
            user_language = normalize_language(user_data.get("language"), DEFAULT_WEB_LANGUAGE)
        else:
            user_timezone = request.form.get("timezone", "9")
            user_language = normalize_language(
                request.form.get("language", user_data.get("language")),
                DEFAULT_WEB_LANGUAGE,
            )

        # 检查用户是否已经绑定账号（仅在 bind 模式下检查）
        has_account = all(key in user_data for key in ['sega_id', 'sega_pwd', 'version'])

        if mode == "bind" and has_account:
            error_messages = language_catalog("main.account_already_bound")
            return _error_page(error_messages, user_language)

        if mode == "bind" and bind_type == "import_token":
            timezone_int = _parse_int(user_timezone, 9)

            if user_version not in ("jp", "intl"):
                user_version = "jp"

            user_data.update({
                "language": user_language,
                "timezone": timezone_int,
                "version": user_version,
                "auth_type": "import_token",
                "import_only": True,
                "import_only_created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })
            for key in ("sega_id", "sega_pwd", "aime"):
                user_data.pop(key, None)
            save_user(user_id, user_data)

            token_result = create_import_token(user_id, note="bookmarklet")
            if not token_result:
                return _error_page("Failed to create import token.", user_language, 500)

            track_event('user_bind', user_id=user_id, metadata={'version': user_version, 'import_only': True})
            link_bound_rich_menu(user_id, user_data)
            return render_template(
                "success.html",
                language=user_language,
                mode="import_token",
                import_token=token_result["token"],
                import_token_id=token_result["token_id"],
            )

        # 在 rebind 模式下，验证 segaid 必须与现有的一致
        if mode == "rebind":
            if not has_account:
                error_messages = language_catalog("main.account_not_linked")
                return _error_page(error_messages, user_language)

            if segaid != user_data.get('sega_id'):
                error_messages = language_catalog("main.sega_id_immutable")
                return _error_page(error_messages, user_language)

        if not segaid or not password:
            missing_fields_messages = language_catalog("main.fields_required")
            return _error_page(missing_fields_messages, user_language)

        if request.form.get("aime_preview") == "1":
            try:
                async def _fetch_all_aime_candidates():
                    results = await asyncio.gather(
                        get_aime_candidates(segaid, password, "jp"),
                        get_aime_candidates(segaid, password, "intl"),
                        return_exceptions=True,
                    )
                    merged = []
                    maintenance_count = 0
                    if any(result == "RATE_LIMITED" for result in results):
                        return "RATE_LIMITED"
                    for version, result in zip(("jp", "intl"), results):
                        if isinstance(result, Exception):
                            logger.warning(
                                f"[Auth] ⚠ Failed to fetch Aime candidates for {version}: "
                                f"user_id={user_id}, error={result}"
                            )
                            continue
                        if result == "MAINTENANCE":
                            maintenance_count += 1
                            continue
                        if not result:
                            continue
                        for candidate in result:
                            candidate = dict(candidate)
                            candidate["ver"] = version
                            candidate["version_label"] = "🇯🇵" if version == "jp" else "🇺🇳"
                            merged.append(candidate)
                    if merged:
                        return merged
                    if maintenance_count == 2:
                        return "MAINTENANCE"
                    return None

                candidates = asyncio.run(_fetch_all_aime_candidates())
            except Exception as e:
                logger.error(f"[Auth] ✗ Failed to fetch Aime candidates: user_id={user_id}, error={e}", exc_info=True)
                message = language_catalog("main.candidates_failed")
                return jsonify({"success": False, "message": select_text(message, language=user_language, default_language=DEFAULT_WEB_LANGUAGE)}), 500

            if candidates == "RATE_LIMITED":
                message = language_catalog("main.login_rate_limited")
                return jsonify({"success": False, "message": select_text(message, language=user_language, default_language=DEFAULT_WEB_LANGUAGE)}), 429

            if candidates == "MAINTENANCE":
                message = language_catalog("main.maintenance")
                return jsonify({"success": False, "message": select_text(message, language=user_language, default_language=DEFAULT_WEB_LANGUAGE)}), 503

            if not candidates:
                message = language_catalog("main.invalid_credentials")
                return jsonify({"success": False, "message": select_text(message, language=user_language, default_language=DEFAULT_WEB_LANGUAGE)}), 401

            return jsonify({"success": True, "candidates": candidates})

        timezone_int = _parse_int(user_timezone, 9)
        aime_int = _parse_int(aime, 0)

        result = asyncio.run(process_sega_credentials(user_id, segaid, password, user_version, user_language, timezone_int, aime_int, (mode == "rebind")))
        if result == "RATE_LIMITED":
            return _error_page(language_catalog("main.login_rate_limited"), user_language, 429)
        if result == "MAINTENANCE":
            maintenance_messages = language_catalog("main.maintenance")
            return _error_page(maintenance_messages, user_language, 503)
        elif result:
            via_token = "registered_via_token" in (get_user(user_id) or {})
            if mode == "bind":
                track_event('user_bind', user_id=user_id, metadata={'version': user_version, 'via_token': via_token})
                link_bound_rich_menu(user_id, get_user(user_id))
            else:
                track_event('user_rebind', user_id=user_id, metadata={'version': user_version, 'via_token': via_token})
                link_bound_rich_menu(user_id, get_user(user_id))
                if not via_token:
                    try:
                        smart_push(user_id, rebind_msg(user_id), configuration)
                    except Exception as e:
                        logger.error(f"[Rebind] ⚠ Failed to push: {e}")
            return render_template("success.html", language=user_language, mode=mode)
        else:
            invalid_credentials_messages = language_catalog("main.invalid_credentials")
            return _error_page(invalid_credentials_messages, user_language, 500)

    # GET 请求时，从用户数据中获取语言设置和其他信息
    user_data = get_user(user_id) or {}
    stored_language = user_data.get("language")
    if stored_language:
        user_language = normalize_language(stored_language, DEFAULT_LANGUAGE)
    else:
        # 首次绑定时，尝试从 LINE profile 自动检测语言
        try:
            with ApiClient(configuration) as api_client:
                profile = MessagingApi(api_client).get_profile(user_id)
                user_language = normalize_language(
                    getattr(profile, "language", None), DEFAULT_LANGUAGE
                )
        except Exception:
            user_language = DEFAULT_LANGUAGE

    # 在 rebind 模式下，传递现有账号数据到模板（不含 timezone/language/权限）
    if mode == "rebind":
        return render_template(
            "bind_form.html",
            user_language=user_language,
            mode="rebind",
            segaid=user_data.get('sega_id', ''),
            password=user_data.get('sega_pwd', ''),
            version=user_data.get('version', 'jp'),
            aime=user_data.get('aime', 0),
        )
    else:
        return render_template("bind_form.html", user_language=user_language, mode="bind")


@app.route("/linebot/unbind", methods=["GET", "POST"])
@csrf.exempt
def website_unbind():
    token = request.args.get("token") or request.form.get("token")
    if not token:
        return _error_page(language_catalog("main.token_missing"))

    try:
        user_id = get_user_id_from_unbind_token(token)
    except Exception as e:
        logger.error(f"[Unbind] ✗ Token verification failed: error={e}")
        return _error_page(language_catalog("main.unbind_token_invalid"))

    user_data = get_user(user_id) or {}
    user_language = normalize_language(user_data.get("language"), DEFAULT_WEB_LANGUAGE)
    if not _can_open_settings(user_data):
        return _error_page(language_catalog("main.no_linked_account"), user_language)

    if request.method == "POST":
        delete_user(user_id)
        link_unbound_rich_menu(user_id)
        track_event('user_unbind', user_id=user_id, metadata={'source': 'web'})
        return render_template("success.html", language=user_language, mode="unbind")

    return render_template(
        "unbind_form.html",
        language=user_language,
        token=token,
        version=user_data.get("version", "-"),
        segaid=user_data.get("sega_id", ""),
        import_only=bool(user_data.get("import_only") or user_data.get("auth_type") == "import_token"),
    )


@app.route("/linebot/settings", methods=["GET", "POST"])
def website_settings():
    token = request.args.get("token")
    if not token:
        token_missing_message = language_catalog("main.token_missing")
        return _error_page(token_missing_message)

    try:
        user_id = get_user_id_from_settings_token(token)
        if not user_exists(user_id):
            token_invalid_message = language_catalog("main.token_invalid")
            return _error_page(token_invalid_message)
    except Exception as e:
        logger.error(f"[Auth] ✗ Settings token verification failed: error={e}")
        token_invalid_message = language_catalog("main.token_invalid")
        return _error_page(token_invalid_message)

    user_data = get_user(user_id) or {}

    # 检查用户是否已绑定账号
    has_account = all(key in user_data for key in ['sega_id', 'sega_pwd', 'version'])
    has_import_only_access = bool(user_data.get("import_only") or user_data.get("auth_type") == "import_token" or user_data.get("import_tokens"))
    if not has_account and not has_import_only_access:
        error_messages = language_catalog("main.account_not_linked")
        user_language = normalize_language(user_data.get("language"), DEFAULT_WEB_LANGUAGE)
        return _error_page(error_messages, user_language)

    custom_bg_filenames = [
        f"jietnguser_{user_id}.webp",
        f"jietnguser_{user_id}_2.webp",
    ]

    if request.method == "POST":
        user_language = normalize_language(
            request.form.get("language", user_data.get("language")),
            DEFAULT_WEB_LANGUAGE,
        )
        user_timezone = request.form.get("timezone", "9")
        bg_files_str = request.form.get("bg_files", "")
        bg_blur_raw = request.form.get("bg_blur", user_data.get("bg_blur", 20))
        bg_overlay_raw = request.form.get("bg_overlay", user_data.get("bg_overlay", 40))
        participate_global_ranking = request.form.get("participate_global_ranking") == "1"
        allow_mention_score_query = request.form.get("allow_mention_score_query") == "1"

        timezone_int = _parse_int(user_timezone, 9)

        # 解析背景图列表
        if bg_files_str.strip():
            bg_files_list = [f.strip() for f in bg_files_str.split(",") if f.strip()]
        else:
            bg_files_list = []

        # 处理背景图开关
        bg_enabled = request.form.get("bg_enabled_hidden", "0") == "1"

        bg_blur = _parse_int(bg_blur_raw, 20, 0, 40)
        bg_overlay = _parse_int(bg_overlay_raw, 40, 0, 120)

        image_skin = normalize_skin(request.form.get("image_skin", user_data.get("image_skin", DEFAULT_USER_SKIN)))

        # 保存设置
        edit_user_value(user_id, "image_skin", image_skin)
        edit_user_value(user_id, "language", user_language)
        edit_user_value(user_id, "timezone", timezone_int)
        edit_user_value(user_id, "bg_files", bg_files_list)
        edit_user_value(user_id, "bg_enabled", bg_enabled)
        edit_user_value(user_id, "bg_blur", bg_blur)
        edit_user_value(user_id, "bg_overlay", bg_overlay)
        edit_user_value(user_id, "participate_global_ranking", participate_global_ranking)
        edit_user_value(user_id, "allow_mention_score_query", allow_mention_score_query)
        link_bound_rich_menu(user_id, get_user(user_id))

        return render_template("success.html", language=user_language, mode="settings")

    # GET: 准备数据
    user_language = normalize_language(user_data.get("language"), DEFAULT_WEB_LANGUAGE)

    # 扫描背景图目录
    try:
        other_bg_files = sorted([
            f for f in os.listdir(BG_DIR)
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))
            and not f.startswith('jietnguser_')
        ])
        existing_custom_bg_files = [
            filename for filename in custom_bg_filenames
            if os.path.exists(os.path.join(BG_DIR, filename))
        ]
        all_bg_files = existing_custom_bg_files + other_bg_files
    except OSError:
        logger.exception("[Settings] Failed to scan background directory")
        all_bg_files = []
        existing_custom_bg_files = []

    user_bg_files = user_data.get("bg_files", [])
    bg_enabled = user_data.get("bg_enabled", False)
    bg_blur = _parse_int(user_data.get("bg_blur"), 20, 0, 40)
    bg_overlay = _parse_int(user_data.get("bg_overlay"), 40, 0, 120)

    # 权限列表
    dev_tokens = load_dev_tokens()
    owner_token_id = user_data.get('registered_via_token', '')
    perm_list = []
    if owner_token_id and owner_token_id in dev_tokens:
        perm_list.append({
            'token_id': owner_token_id,
            'note': dev_tokens[owner_token_id].get('note', owner_token_id),
            'is_owner': True,
        })
    for tid, tdata in dev_tokens.items():
        if user_id in tdata.get('allowed_users', []):
            perm_list.append({
                'token_id': tid,
                'note': tdata.get('note', tid),
                'is_owner': False,
            })

    return render_template(
        "settings.html",
        user_language=user_language,
        image_skins=available_skins(),
        image_skin=normalize_skin(user_data.get("image_skin", DEFAULT_USER_SKIN)),
        timezone=user_data.get('timezone', 9),
        bg_files=all_bg_files,
        user_bg_files=user_bg_files,
        bg_enabled=bg_enabled,
        bg_blur=bg_blur,
        bg_overlay=bg_overlay,
        participate_global_ranking=user_data.get("participate_global_ranking", True) is not False,
        allow_mention_score_query=user_data.get("allow_mention_score_query", True) is not False,
        custom_bg_filenames=existing_custom_bg_files,
        perm_token=generate_perm_token(user_id),
        perm_list=perm_list,
        import_tokens=list_import_tokens(user_id) or [],
    )


def _settings_user_id_from_request():
    token = request.args.get("token")
    if not token:
        data = request.get_json(silent=True) or {}
        token = data.get("settings_token") or data.get("token")
    if not token:
        return None
    try:
        user_id = get_user_id_from_settings_token(token)
        return user_id if user_exists(user_id) else None
    except ValueError:
        return None


@app.route("/linebot/settings/import_tokens", methods=["POST", "DELETE"])
@csrf.exempt
def manage_import_tokens():
    """settings 页面用：生成或撤销用户成绩导入 token。"""
    user_id = _settings_user_id_from_request()
    if not user_id:
        return jsonify({"error": "Invalid token", "message": "Settings token is invalid"}), 401

    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        note = str(data.get("title") or data.get("note") or "").strip()[:120] or "custom"
        result = create_import_token(user_id, note=note)
        if not result:
            return jsonify({"error": "User not found"}), 404
        return jsonify({
            "success": True,
            "user_id": user_id,
            "token_id": result["token_id"],
            "token": result["token"],
            "note": result["note"],
            "created_at": result["created_at"],
            "message": "Import token generated. This token is shown only once.",
        }), 201

    data = request.get_json(silent=True) or {}
    token_id = data.get("token_id")
    if not token_id:
        return jsonify({"error": "Missing parameter", "message": "token_id is required"}), 400
    if data.get("action") == "delete":
        deleted = delete_revoked_import_token(user_id, token_id)
        if not deleted:
            return jsonify({"error": "Token not found", "message": "Only revoked import tokens can be deleted"}), 404
        return jsonify({"success": True, "user_id": user_id, "token_id": token_id, "deleted": True})
    revoked = revoke_import_token(user_id, token_id=token_id)
    if not revoked:
        return jsonify({"error": "Token not found", "message": "No active import token was revoked"}), 404
    return jsonify({"success": True, "user_id": user_id, "token_id": token_id, "revoked": revoked})


@app.route("/linebot/settings/custom_bg", methods=["POST", "DELETE"])
@csrf.exempt
def manage_custom_bg():
    """上传或删除用户自定义背景图"""
    token = request.args.get("token")
    if not token:
        return jsonify({"success": False, "message": "Token not provided"}), 400

    try:
        user_id = get_user_id_from_settings_token(token)
        if not user_exists(user_id):
            return jsonify({"success": False, "message": "Invalid token"}), 400
    except ValueError:
        return jsonify({"success": False, "message": "Invalid token"}), 400

    custom_bg_filenames = [
        f"jietnguser_{user_id}.webp",
        f"jietnguser_{user_id}_2.webp",
    ]

    if request.method == "DELETE":
        delete_all = request.args.get("all") == "1"
        requested_filename = request.args.get("filename")
        if requested_filename and requested_filename not in custom_bg_filenames:
            return jsonify({"success": False, "message": "Invalid filename"}), 400
        delete_filenames = custom_bg_filenames if delete_all else [
            requested_filename or next(
                (filename for filename in custom_bg_filenames if os.path.exists(os.path.join(BG_DIR, filename))),
                custom_bg_filenames[0],
            )
        ]
        for custom_bg_filename in delete_filenames:
            try:
                os.remove(os.path.join(BG_DIR, custom_bg_filename))
                logger.info("[Settings] Deleted custom bg: user_id=%s", user_id)
            except FileNotFoundError:
                pass
            except OSError:
                logger.exception("[Settings] Failed to delete custom bg: user_id=%s", user_id)
                return jsonify({"success": False, "message": "Failed to delete"}), 500

        bg_files = get_user_field(user_id, "bg_files", [])
        updated_bg_files = [filename for filename in bg_files if filename not in delete_filenames]
        if updated_bg_files != bg_files:
            bg_files = updated_bg_files
            edit_user_value(user_id, "bg_files", bg_files)

        return jsonify({"success": True}), 200

    # POST: 上传（接收 base64 JSON）
    custom_bg_filename = next(
        (filename for filename in custom_bg_filenames if not os.path.exists(os.path.join(BG_DIR, filename))),
        None,
    )
    if not custom_bg_filename:
        return jsonify({"success": False, "message": "Maximum of 2 images reached"}), 409
    custom_bg_path = os.path.join(BG_DIR, custom_bg_filename)

    body = request.get_json(silent=True)
    if not body or 'data' not in body or 'filename' not in body:
        return jsonify({"success": False, "message": "No file provided"}), 400

    original_ext = os.path.splitext(body['filename'])[1].lower()
    if original_ext not in ALLOWED_BACKGROUND_EXTENSIONS:
        return jsonify({"success": False, "message": "Unsupported format"}), 400

    try:
        file_data = b64mod.b64decode(body["data"], validate=True)
    except (ValueError, binascii.Error):
        return jsonify({"success": False, "message": "Invalid data"}), 400

    if len(file_data) > MAX_BACKGROUND_BYTES:
        return jsonify({"success": False, "message": "File too large"}), 400

    try:
        from PIL import Image as PILImage, ImageOps
        from io import BytesIO as BIO
        try:
            from pillow_heif import register_heif_opener
            register_heif_opener()
        except ImportError:
            pass
        with PILImage.open(BIO(file_data)) as source_img:
            source_img.load()
            img = ImageOps.exif_transpose(source_img).convert("RGB")
        img.save(custom_bg_path, "WEBP", quality=85)
        logger.info("[Settings] Uploaded custom bg: user_id=%s ext=%s size=%s",
                    user_id, original_ext, len(file_data))
    except (OSError, ValueError):
        logger.exception("[Settings] Invalid custom bg: user_id=%s ext=%s", user_id, original_ext)
        return jsonify({"success": False, "message": "Invalid image"}), 400

    return jsonify({"success": True, "filename": custom_bg_filename}), 201


@app.route("/linebot/perms/revoke", methods=["POST"])
@csrf.exempt
def linebot_perms_revoke():
    data = request.form.to_dict() or request.get_json(force=True, silent=True) or {}
    perm_token = data.get('perm_token', '')
    token_id_to_revoke = data.get('token_id', '')

    try:
        user_id = get_user_id_from_perm_token(perm_token)
    except ValueError:
        return jsonify({"error": "Invalid or expired token"}), 401

    _udata = get_user(user_id)
    if not _udata:
        return jsonify({"error": "User not found"}), 404

    if _udata.get('registered_via_token') == token_id_to_revoke:
        edit_user_value(user_id, "registered_via_token", None, operation=4)
        logger.info(f"[Permission] Web revoke owner: token_id={token_id_to_revoke}, user_id={user_id}")
        return jsonify({"success": True, "revoked_owner": True})

    dev_tokens = load_dev_tokens()
    if token_id_to_revoke not in dev_tokens:
        return jsonify({"error": "Token not found"}), 404

    allowed_users = dev_tokens[token_id_to_revoke].get('allowed_users', [])
    if user_id not in allowed_users:
        return jsonify({"error": "Permission not found"}), 404

    allowed_users.remove(user_id)
    dev_tokens[token_id_to_revoke]['allowed_users'] = allowed_users
    save_dev_tokens(dev_tokens)

    logger.info(f"[Permission] Web revoke: token_id={token_id_to_revoke}, user_id={user_id}")
    return jsonify({"success": True})


DEMO_CORS_DEFAULT_ORIGINS = {
    "https://jietng.matsuk1.com",
    "https://my-aime-webpage.pages.dev",
    "https://maiscore.matsuk1.com",
}
DEMO_CORS_ORIGIN = ",".join(sorted(DEMO_CORS_DEFAULT_ORIGINS))
DEMO_CORS_ORIGINS = {
    origin.strip()
    for origin in os.getenv("DEMO_CORS_ORIGINS", DEMO_CORS_ORIGIN).split(",")
    if origin.strip()
}

def _demo_cors(response):
    origin = request.headers.get("Origin")
    if "*" in DEMO_CORS_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = "*"
    elif origin in DEMO_CORS_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Vary"] = "Origin"
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


def _normalize_session_profile(profile: dict, ver: str) -> dict:
    base = "https://maimaidx-eng.com/maimai-mobile" if ver == "intl" else "https://maimaidx.jp/maimai-mobile"
    rating = str(profile.get("rating", "0")).strip() or "0"
    try:
        rating_int = int(rating)
    except (TypeError, ValueError):
        rating_int = 0

    return {
        "name": str(profile.get("name", "NAME_ERROR")).strip()[:64] or "NAME_ERROR",
        "rating": rating,
        "rating_block_path": get_rating_image_path(rating_int),
        "cource_rank_url": profile.get("cource_rank_url") or profile.get("course_rank_url") or "N/A",
        "class_rank_url": profile.get("class_rank_url") or "N/A",
        "icon_url": profile.get("icon_url") or "N/A",
        "nameplate_url": profile.get("nameplate_url") or "N/A",
        "trophy_url": profile.get("trophy_url") or f"{base}/img/trophy_rainbow.png",
        "trophy_content": str(profile.get("trophy_content", "N/A")).strip()[:80] or "N/A",
    }

def _normalize_session_records(records: list) -> list:
    valid_difficulties = {"basic", "advanced", "expert", "master", "remaster"}
    valid_types = {"std", "dx", "utage"}
    normalized = []

    for record in records[:3000]:
        if not isinstance(record, dict):
            continue
        name = str(record.get("name", "")).strip()
        score = str(record.get("score", "")).strip()
        difficulty = str(record.get("difficulty", "")).strip().lower()
        music_type = str(record.get("type", "")).strip().lower()
        if not name or not score or difficulty not in valid_difficulties or music_type not in valid_types:
            continue

        normalized.append({
            "name": name[:160],
            "difficulty": difficulty,
            "type": music_type,
            "score": score if score.endswith("%") else f"{score}%",
            "dx_score": str(record.get("dx_score", "N/A")).replace(",", "").strip(),
            "score_icon": str(record.get("score_icon", "")).strip().lower(),
            "combo_icon": str(record.get("combo_icon", "")).strip().lower(),
            "sync_icon": str(record.get("sync_icon", "")).strip().lower(),
        })

    return normalized

def _generate_session_image_from_payload(data: dict):
    ver = data.get("version", "jp")
    if ver not in ("jp", "intl"):
        raise ValueError("Invalid version")

    cmd_type = str(data.get("cmd_type", data.get("type", "best50"))).strip().lower()
    valid_cmd_types = {"best50", "best40", "best35", "best15", "allb35", "allb50", "apb50", "fdxb50", "idlb50", "sun50"}
    if cmd_type not in valid_cmd_types:
        cmd_type = "best50"

    command = str(data.get("command", "")).strip()
    try:
        timezone_offset = int(data.get("timezone", 9))
        timezone_offset = max(-12, min(14, timezone_offset))
    except (TypeError, ValueError):
        timezone_offset = 9

    profile = data.get("profile")
    records_payload = data.get("records", {})
    raw_records = records_payload.get("best") if isinstance(records_payload, dict) else None
    if not isinstance(profile, dict) or not isinstance(raw_records, list):
        raise ValueError("Missing profile or records.best")

    records = _normalize_session_records(raw_records)
    if not records:
        raise ValueError("No valid records")

    user_info = _normalize_session_profile(profile, ver)
    song_record = get_detailed_info(records, ver=ver, recent_type=(cmd_type == "best40"))
    up_songs, down_songs, details = select_records(song_record, type=cmd_type, command=command, ver=ver)
    if not up_songs and not down_songs:
        raise ValueError("No records matched")

    matched_count = sum(1 for record in song_record if record.get("version") != "UNKNOWN")
    new_count = sum(1 for record in song_record if record.get("new_song") is True)
    old_count = sum(1 for record in song_record if record.get("new_song") is False)
    logger.info(
        "[SessionImage] Records selected: ver=%s, type=%s, raw=%s, normalized=%s, matched=%s, old=%s, new=%s, up=%s, down=%s",
        ver, cmd_type, len(raw_records), len(records), matched_count, old_count, new_count, len(up_songs), len(down_songs)
    )

    profile_img = generate_profile(user_info)
    records_img = generate_records_picture(
        up_songs,
        down_songs,
        title=cmd_type.upper(),
        ver=ver,
        details=details,
    )
    result = compose_generated_images(
        [profile_img, records_img],
        timezone_offset=timezone_offset,
    )
    filename = f"jietng_{ver}_{cmd_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    return result, filename

@app.route("/api/web/session-image", methods=["POST", "OPTIONS"])
@csrf.exempt
def api_web_session_image():
    if request.method == "OPTIONS":
        return _maimai_session_cors(app.make_response(("", 204)))

    data = request.get_json(silent=True) or {}
    try:
        result, filename = _generate_session_image_from_payload(data)
        with result:
            buf = BytesIO(_encode_jpeg(result))
        response = send_file(buf, mimetype="image/jpeg", as_attachment=False, download_name=filename)
        return _maimai_session_cors(response)
    except ValueError as e:
        return _maimai_session_cors(jsonify({"error": str(e)})), 400
    except Exception as e:
        logger.error(f"[SessionImage] ✗ Failed to generate image: {e}", exc_info=True)
        return _maimai_session_cors(jsonify({"error": "Failed to generate image"})), 500

@app.route("/linebot/demo", methods=["POST", "OPTIONS"])
@csrf.exempt
def demo_page():
    if request.method == "OPTIONS":
        return _demo_cors(app.make_response(("", 204)))

    segaid = request.form.get("segaid", "").strip()
    password = request.form.get("password", "").strip()
    ver = request.form.get("ver", "jp")
    cmd_type = request.form.get("cmd_type", "best50").strip()
    params = request.form.get("params", "").strip()
    try:
        tz = int(request.form.get("timezone", "9"))
        tz = max(-12, min(14, tz))
    except (ValueError, TypeError):
        tz = 9
    try:
        aime = int(request.form.get("aime", "0"))
        aime = max(0, min(2, aime))
    except (ValueError, TypeError):
        aime = 0

    if not segaid or not password:
        return _demo_cors(jsonify({"error": "Please fill in SEGA ID and password."})), 400
    if ver not in ("jp", "intl"):
        return _demo_cors(jsonify({"error": "Invalid version."})), 400

    _VALID_CMD_TYPES = {"best50", "best40", "best35", "best15", "allb35", "allb50", "apb50", "fdxb50", "idlb50", "sun50"}
    if cmd_type not in _VALID_CMD_TYPES:
        cmd_type = "best50"
    title = cmd_type.upper()

    async def _pipeline():
        cookies = await login_to_maimai(segaid, password, ver=ver, aime=aime)
        if not cookies or cookies in ("MAINTENANCE", "RATE_LIMITED"):
            return cookies
        user_info, raw_records = await asyncio.gather(
            get_maimai_info(cookies, ver=ver),
            get_maimai_records(cookies, ver=ver)
        )
        if not raw_records:
            raise ValueError("No records found for this Aime card.")
        song_record = get_detailed_info(raw_records, ver=ver)
        up_songs, down_songs, details = select_records(song_record, type=cmd_type, command=params, ver=ver)
        if not up_songs and not down_songs:
            raise ValueError("No records matched the selected filters.")
        profile_img = generate_profile(user_info)
        records_img = generate_records_picture(
            up_songs,
            down_songs,
            title=title,
            ver=ver,
            details=details,
        )
        if not records_img:
            raise ValueError("No records matched the selected filters.")
        return compose_generated_images(
            [profile_img, records_img],
            timezone_offset=tz,
        )

    try:
        result = asyncio.run(_pipeline())
        if result == "RATE_LIMITED":
            return _demo_cors(jsonify({"error": "The JP login rate limit was reached. Please try again later."})), 429
        if result == "MAINTENANCE":
            return _demo_cors(jsonify({"error": "The official website is under maintenance. Please try again later."})), 503
        if not result:
            return _demo_cors(jsonify({"error": "Login failed. Please check your SEGA ID and password."})), 401
        with result:
            buf = BytesIO(_encode_jpeg(result))
        return _demo_cors(send_file(buf, mimetype="image/jpeg"))
    except ValueError as e:
        return _demo_cors(jsonify({"error": str(e)})), 400
    except Exception as e:
        logger.error(f"[Demo] Pipeline error: {e}", exc_info=True)
        return _demo_cors(jsonify({"error": "An error occurred while generating your score card."})), 500


async def process_sega_credentials(
    user_id,
    segaid,
    password,
    ver="jp",
    language=DEFAULT_WEB_LANGUAGE,
    timezone=9,
    aime=0,
    rebind=False,
):
    base = (
        "https://maimaidx-eng.com/maimai-mobile"
        if ver == "intl"
        else "https://maimaidx.jp/maimai-mobile"
    )

    cookies = await login_to_maimai(segaid, password, ver=ver, aime=aime)
    if cookies in ("MAINTENANCE", "RATE_LIMITED"):
        return cookies
    if not cookies:
        logger.warning(f"[Auth] ⚠ Login failed for user_id={user_id}")
        return False

    # 验证登录是否成功
    connector = aiohttp.TCPConnector(ssl=False, limit=10)
    timeout = aiohttp.ClientTimeout(total=30, connect=10)
    async with aiohttp.ClientSession(cookies=cookies, connector=connector, timeout=timeout) as session:
        dom = await fetch_dom(session, f"{base}/home/", ver)

        if dom == "MAINTENANCE":
            return "MAINTENANCE"
        if dom is None:
            return False

    edit_user_value(user_id, 'sega_id', segaid)
    edit_user_value(user_id, 'sega_pwd', password)
    edit_user_value(user_id, 'version', ver)
    edit_user_value(user_id, 'aime', aime)
    edit_user_value(user_id, 'language', language)
    edit_user_value(user_id, 'timezone', timezone)

    return True


# ==================== 异步任务处理函数 ====================

def async_maimai_update_task(ctx):
    """异步maimai更新任务 - 在webtask_queue中执行"""
    user_id = ctx.user_id
    reply_token = ctx.reply_token
    source_type = ctx.source_type

    # 获取用户版本
    ver = ctx.mai_ver

    try:
        reply_msg = asyncio.run(maimai_update(user_id, ver))
        track_event('sync_task', user_id=user_id, metadata={'success': True, 'trigger': 'user'})
    except Exception as e:
        track_event('sync_task', user_id=user_id, metadata={'success': False, 'trigger': 'user', 'error': str(e)[:200]})
        raise
    if reply_token:
        smart_reply(user_id, reply_token, reply_msg, configuration, source_type=source_type)

def async_get_friend_list_task(ctx):
    """异步获取好友列表任务 - 在webtask_queue中执行，实时登录SEGA抓取"""
    user_id = ctx.user_id
    reply_token = ctx.reply_token

    source_type = ctx.source_type
    if source_type != 'user':
        smart_reply(
            user_id,
            reply_token,
            generate_status_flex(
                language_catalog("main.private_chat_title"),
                language_catalog("messages.friend_rcd_group_warning_text"),
                user_id,
                tone="warning",
            ),
            configuration,
            addition=False,
        )
        return

    _udata = get_user(user_id)
    if not _udata or 'sega_id' not in _udata:
        smart_reply(user_id, reply_token, segaid_error(user_id), configuration, source_type=source_type)
        return

    sega_id = _udata.get('sega_id')
    sega_pwd = _udata.get('sega_pwd')
    ver = _udata.get('version', 'jp')
    aime = _udata.get('aime', 0)

    try:
        cookies = asyncio.run(login_to_maimai(sega_id, sega_pwd, ver=ver, aime=aime))
        if cookies == "RATE_LIMITED":
            smart_reply(user_id, reply_token, login_rate_limit_message(user_id), configuration, source_type=source_type)
            return
        if cookies is None:
            smart_reply(user_id, reply_token, segaid_error(user_id), configuration, source_type=source_type)
            return
        if cookies == "MAINTENANCE":
            smart_reply(user_id, reply_token, maintenance_error(user_id), configuration, source_type=source_type)
            return

        friend_list = asyncio.run(get_friends_list(cookies, ver))
        if friend_list == "MAINTENANCE":
            smart_reply(user_id, reply_token, maintenance_error(user_id), configuration, source_type=source_type)
            return
        if not friend_list:
            smart_reply(user_id, reply_token, friend_error(user_id), configuration, source_type=source_type)
            return

        friend_num = len(friend_list)
        if friend_num <= 10:
            group_size = 10
        elif 14 < friend_num <= 16:
            group_size = 8
        elif 17 <= friend_num <= 18:
            group_size = 9
        else:
            group_size = 7

        reply_msg = generate_friend_buttons(user_id, get_friend_list_alt_text(user_id), friend_list, group_size)
        smart_reply(user_id, reply_token, reply_msg, configuration, source_type=source_type)

    except Exception as e:
        logger.error(f"[FriendList] ✗ Failed to get friend list: user_id={user_id}, error={e}", exc_info=True)
        smart_reply(user_id, reply_token, friend_error(user_id), configuration, source_type=source_type)

def async_generate_friend_record_task(ctx):
    """异步生成好友成绩任务 - 在webtask_queue中执行"""
    user_message = ctx.text
    user_id = ctx.user_id
    reply_token = ctx.reply_token

    # 检查是否在群聊中发送
    source_type = ctx.source_type
    if source_type != 'user':
        reply_message = generate_status_flex(
            language_catalog("main.private_chat_title"),
            language_catalog("messages.friend_rcd_group_warning_text"),
            user_id,
            tone="warning",
        )
        return smart_reply(user_id, reply_token, reply_message, configuration, addition=False)

    # 只拆分前两个空格，剩余内容作为 command
    parts = user_message.replace("friend-rcd ", "").strip().split(maxsplit=2)
    friend_code = parts[0] if len(parts) > 0 else ""
    record_type = parts[1] if len(parts) > 1 else "best50"
    command = parts[2] if len(parts) > 2 else ""

    # 转换 record_type 为标准格式
    std = False
    for aliases, standard_type in RANK_COMMANDS.items():
        if record_type.lower() in aliases:
            record_type = standard_type
            std = True
            break
    if not std:
        record_type = "best50"

    # 获取用户版本
    ver = ctx.mai_ver

    track_event("image_gen", user_id=user_id,
                metadata={"command": "friend-rcd", "source": "line"})

    # 直接通过网页爬取获取好友信息
    reply_msg = asyncio.run(generate_friend_record(user_id, friend_code, record_type, command, ver))

    smart_reply(user_id, reply_token, reply_msg, configuration, source_type=source_type)

def async_get_song_record_task(ctx):
    """Query using the command context resolved before queueing."""
    text = ctx.text.strip()
    acronym = "" if text.lower() == "record" else re.sub(
        r"\s+record$", "", text, flags=re.IGNORECASE
    ).strip()
    track_event("image_gen", user_id=ctx.user_id,
                metadata={"command": "record", "source": "line"})
    reply_msg = asyncio.run(get_song_record(ctx.user_id, ctx.id_use, acronym, ctx.mai_ver_use))
    smart_reply(ctx.user_id, ctx.reply_token, reply_msg, configuration, source_type=ctx.source_type)

def async_admin_maimai_update_task(event):
    """管理员触发的maimai更新任务 - 在webtask_queue中执行"""
    user_id = event.source.user_id

    ver = "jp"
    _ver = get_user_field(user_id, 'version')
    if _ver is not None:
        ver = _ver

    try:
        asyncio.run(maimai_update(user_id, ver))
        track_event('sync_task', user_id=user_id, metadata={'success': True, 'trigger': 'admin'})
    except Exception as e:
        track_event('sync_task', user_id=user_id, metadata={'success': False, 'trigger': 'admin', 'error': str(e)[:200]})
        raise


# ==================== 主程序入口 ====================

@limit_maimai_operation_duration("login and score fetch operation")
async def _sync_maimai_user_data(user_id, ver="jp"):
    start_time = time.time()
    func_status = {
        "User Info": True,
        "Best Records": True,
        "Recent Records": True,
    }

    def failure(error, message, status_code):
        return {
            "success": False, "error": error, "message": message,
            "status_code": status_code, "user_id": user_id, "version": ver,
            "func_status": func_status, "elapsed_time": time.time() - start_time,
        }

    _udata = get_user(user_id)
    if not _udata or 'sega_id' not in _udata or 'sega_pwd' not in _udata:
        return failure("Account not bound", f"User {user_id} has not bound a SEGA account", 400)

    sega_id = _udata.get('sega_id')
    sega_pwd = _udata.get('sega_pwd')
    aime = _udata.get('aime', 0)

    cookies = await login_to_maimai(sega_id, sega_pwd, ver=ver, aime=aime)
    if cookies is None:
        logger.warning(f"[User] ⚠ Login failed: user_id={user_id}")
        return failure("Authentication failed", "Invalid SEGA ID or password.", 401)
    if cookies == "RATE_LIMITED":
        return failure("Rate limited", "The JP login rate limit was reached. Please try again later.", 429)
    if cookies == "MAINTENANCE":
        return failure("Maintenance", "The official website is under maintenance. Please try again later.", 503)

    user_info, maimai_records, recent_records = await asyncio.gather(
        get_maimai_info(cookies, ver),
        get_maimai_records(cookies, ver),
        get_recent_records(cookies, ver),
    )

    if (user_info == "MAINTENANCE" or
        maimai_records == "MAINTENANCE" or
        recent_records == "MAINTENANCE"):
        return failure("Maintenance", "The official website is under maintenance. Please try again later.", 503)

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

    # 计算耗时
    elapsed_time = time.time() - start_time

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if not error:
        edit_user_value(user_id, "last_update", current_time)

    user_data = get_user(user_id) or {}
    username = user_data.get('personal_info', {}).get('name', 'N/A')
    rating = user_data.get('personal_info', {}).get('rating', 'N/A')

    return {
        "success": not error,
        "error": None if not error else "Data fetch incomplete",
        "message": "Sync completed successfully." if not error else "Sync completed with incomplete data.",
        "status_code": 200 if not error else 502,
        "user_id": user_id,
        "version": ver,
        "username": username,
        "rating": rating,
        "last_update": current_time if not error else user_data.get("last_update"),
        "elapsed_time": elapsed_time,
        "func_status": func_status,
        "best_count": len(maimai_records) if maimai_records else 0,
        "recent_count": len(recent_records) if recent_records else 0,
    }


async def maimai_update(user_id, ver="jp"):
    previous_rating = ((get_user(user_id) or {}).get("personal_info") or {}).get("rating")
    result = await _sync_maimai_user_data(user_id, ver)

    if result.get("error") == "Account not bound" or result.get("error") == "Authentication failed":
        return segaid_error(user_id)
    if result.get("error") == "Rate limited":
        return login_rate_limit_message(user_id)
    if result.get("error") == "Maintenance":
        return maintenance_error(user_id)

    extra_messages = []

    if (result.get("func_status", {}).get("Best Records")
            and result.get("func_status", {}).get("User Info")
            and result.get("rating") is not None
            and str(result["rating"]) != str(previous_rating)):
        b50_message = await generate_records(user_id, user_id, ver=ver)
        if b50_message is not None:
            extra_messages.append(b50_message)

    messages = [
        generate_update_result_flex(
            user_id=user_id,
            update_time=result.get("last_update") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            elapsed_time=result.get("elapsed_time", 0),
            func_status=result.get("func_status", {}),
            success=bool(result.get("success")),
        )
    ]

    messages.extend(extra_messages)

    return messages

def get_bot_status(user_id):
    # 运行时长
    uptime = datetime.now() - SERVICE_START_TIME
    days = uptime.days
    hours, remainder = divmod(uptime.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    uptime_str = f"{days}d {hours}h {minutes}m"

    # 用户版本（影响读哪份 dxdata）
    ver = get_user_field(user_id, "version", "jp") if user_id else "jp"

    # 楽曲データ：曲数 + 文件 mtime
    try:
        songs, _ = read_dxdata(ver)
        song_count = len(songs)
    except Exception:
        song_count = 0
    try:
        dxdata_date = datetime.fromtimestamp(os.path.getmtime(DXDATA_FILE)).strftime("%Y-%m-%d")
    except Exception:
        dxdata_date = "N/A"

    # 今日任务数 = image_gen + sync_cmd（复用 business_stats 30s 缓存）
    bs = get_business_stats()
    tasks_today = bs.get("today_image_calls", 0) + bs.get("today_sync_cmd_calls", 0)

    return generate_bot_status_flex(
        uptime_str=uptime_str,
        image_queue_size=image_queue.qsize() + image_query_queue.qsize(),
        web_queue_size=webtask_queue.qsize(),
        tasks_today=tasks_today,
        song_count=song_count,
        dxdata_date=dxdata_date,
        user_id=user_id,
    )


# ==================== 消息处理 ====================

# Web任务路由规则 (需要网络请求的耗时任务)
def handle_accept_perm_request(user_id: str, request_id: str) -> TextMessage:

    result = accept_perm_request(user_id, request_id)

    if result['success']:
        text = get_multilingual_text(language_catalog("messages.perm_request_accept_success_text"), user_id).format(
            token_id=result['token_id'],
            requester_name=result.get('requester_name', result['token_id'])
        )
    elif result.get('error') == 'Request not found':
        text = get_multilingual_text(language_catalog("messages.perm_request_already_processed_text"), user_id)
    else:
        notify_admins_error(
            error_title="Permission Request Accept Error",
            error_details=f"Error: {result['error']}\nMessage: {result['message']}\nRequest ID: {request_id}",
            context={
                "Request ID": request_id,
                "Error Type": result['error']
            },
            user_id=user_id
        )
        text = get_multilingual_text(system_error_text, user_id)

    return TextMessage(text=text)


def handle_reject_perm_request(user_id: str, request_id: str) -> TextMessage:

    result = reject_perm_request(user_id, request_id)

    if result['success']:
        text = get_multilingual_text(language_catalog("messages.perm_request_reject_success_text"), user_id).format(
            token_id=result['token_id'],
            requester_name=result.get('requester_name', result['token_id'])
        )
    elif result.get('error') == 'Request not found':
        text = get_multilingual_text(language_catalog("messages.perm_request_already_processed_text"), user_id)
    else:
        notify_admins_error(
            error_title="Permission Request Reject Error",
            error_details=f"Error: {result['error']}\nMessage: {result['message']}\nRequest ID: {request_id}",
            context={
                "Request ID": request_id,
                "Error Type": result['error']
            },
            user_id=user_id
        )
        text = get_multilingual_text(system_error_text, user_id)

    return TextMessage(text=text)


def mark_message_as_read(mark_as_read_token: str, user_id: str = None):
    if not mark_as_read_token:
        logger.debug(f"[MarkAsRead] ⊘ No token provided: user_id={user_id}")
        return

    try:
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            mark_request = MarkMessagesAsReadByTokenRequest(
                mark_as_read_token=mark_as_read_token
            )
            line_bot_api.mark_messages_as_read_by_token(mark_request)
            logger.debug(f"[MarkAsRead] ✓ Marked messages as read: user_id={user_id}")
    except Exception as e:
        logger.error(f"[MarkAsRead] ✗ Failed to mark as read: user_id={user_id}, error={e}")


# ============================================================
# 命令派发 / Command Dispatch
# 替代散落在 main.py 的 6 个分发表：WEB_TASK_ROUTES / IMAGE_TASK_ROUTES /
# RANK_COMMANDS（仍保留为数据）/ COMMAND_MAP / SPECIAL_RULES / 内联 if-block
# 设计：modules/commands/command_router.py
# ============================================================

def show_loading(user_id):
    """在私聊中显示加载动画（队列任务入队前调用）"""
    try:
        with ApiClient(configuration) as api_client:
            MessagingApi(api_client).show_loading_animation(
                ShowLoadingAnimationRequest(chatId=user_id, loadingSeconds=20)
            )
    except Exception as exc:
        logger.debug("[LoadingAnimation] Request failed: user_id=%s error=%s", user_id, exc)


def _build_command_context(event, cleaned_text):
    """从 event + 已清洗文本构造 CommandContext"""
    user_id = event.source.user_id
    source_type = getattr(event.source, 'type', 'user')
    mentioned_user_id = extract_single_mention(event, user_id)
    has_other = has_non_bot_mention(event)

    _cur_user = get_user(user_id)
    if _cur_user:
        mai_ver = _cur_user.get("version", "jp")
        id_use = mentioned_user_id if mentioned_user_id else user_id
        _target_user = get_user(id_use) if id_use != user_id else _cur_user
        mai_ver_use = _target_user.get("version", "jp") if _target_user else mai_ver
    else:
        id_use = user_id
        mai_ver = "jp"
        mai_ver_use = "jp"
        _target_user = None

    return CommandContext(
        event=event, text=cleaned_text, user_id=user_id,
        source_type=source_type, reply_token=event.reply_token,
        mentioned_user_id=mentioned_user_id,
        has_other_mention=has_other, id_use=id_use,
        mai_ver=mai_ver, mai_ver_use=mai_ver_use,
        target_user=_target_user,
    )


def _handle_fix_record_command(event, command_text: str) -> bool:
    try:
        parsed_command = parse_fix_record_command(command_text)
    except ValueError:
        parsed_command = False
    if parsed_command is None:
        return False

    user_id = event.source.user_id
    source_type = getattr(event.source, "type", "user")
    if parsed_command is False:
        message = generate_status_flex(
            language_catalog("main.correction_format_title"),
            language_catalog("main.correction_format_body"),
            user_id,
            tone="warning",
        )
    else:
        show_loading(user_id)
        title, achievement, judgement = parsed_command
        result = {
            "source": "manual",
            "parsed": {
                "title": title,
                "achievement": achievement,
                "sub_judgement": judgement,
                "raw": {},
            },
        }
        ver = get_user_field(user_id, "version", "jp") or "jp"
        result = validate_recognized_judgement(
            result,
            ver=ver,
            allow_ocr_alignment=False,
            preserve_input=True,
        )
        if score_recognition_needs_manual_fix(result):
            message = generate_score_recognition_flex(result, user_id)
        else:
            result_img = generate_score_recognition_picture(
                result,
                skin=user_skin(user_id),
                ver=ver,
                timezone_offset=get_user_timezone(user_id),
                bg_filter=_get_user_bg_filter(user_id),
            )
            original_url, preview_url = asyncio.run(
                upload_generated_image(result_img, user_id)
            )
            if not original_url or not preview_url:
                raise RuntimeError("Score recognition image upload failed")
            message = ImageMessage(
                            original_content_url=original_url,
                            preview_image_url=preview_url,
                      )

    smart_reply(
        user_id,
        event.reply_token,
        message,
        configuration,
        addition=False,
        source_type=source_type,
    )
    return True


def _score_recognition_queue_task(event, command: str, quoted_message_id: str, force_flex: bool = False) -> None:
    user_id = event.source.user_id
    source_type = getattr(event.source, 'type', 'user')
    request_started_at = time.perf_counter()
    try:
        logger.info(
            "[Recognize] → OCR started: command=%s user_id=%s quoted_message_id=%s",
            command,
            user_id,
            quoted_message_id,
        )
        download_started_at = time.perf_counter()
        image_bytes = _download_line_message_content(quoted_message_id)
        download_seconds = time.perf_counter() - download_started_at
        if command == "crop":
            crop_img = build_score_crop_preview_image(
                image_bytes, skin=user_skin(user_id),
                ver=get_user_field(user_id, 'version') or 'jp',
                timezone_offset=get_user_timezone(user_id),
                bg_filter=_get_user_bg_filter(user_id),
            )
            original_url, preview_url = asyncio.run(
                upload_generated_image(crop_img, user_id)
            )
            if not original_url or not preview_url:
                raise RuntimeError("Score crop preview upload failed")
            reply_messages = [
                ImageMessage(
                    original_content_url=original_url,
                    preview_image_url=preview_url,
                )
            ]
            logger.info(
                "[Recognize] ✓ Crop completed: command=%s user_id=%s download=%.3fs "
                "total_before_reply=%.3fs",
                command,
                user_id,
                download_seconds,
                time.perf_counter() - request_started_at,
            )
        else:
            ver = get_user_field(user_id, "version", "jp") or "jp"
            if command == "ai-rec":
                result = recognize_score_with_ai(image_bytes, ver=ver)
            else:
                result = recognize_score_image_bytes(image_bytes, ver=ver)
                result = validate_recognized_judgement(result, ver=ver)
            result_variants = expand_score_recognition_calc_variants(result)
            if force_flex or (
                len(result_variants) == 1
                and score_recognition_needs_manual_fix(result_variants[0])
            ):
                reply_messages = [
                    generate_score_recognition_flex(
                        result_variants,
                        user_id,
                    )
                ]
            else:
                reply_messages = []
                for result_variant in result_variants:
                    result_img = generate_score_recognition_picture(
                        result_variant,
                        skin=user_skin(user_id),
                        ver=ver,
                        timezone_offset=get_user_timezone(user_id),
                        bg_filter=_get_user_bg_filter(user_id),
                    )
                    original_url, preview_url = asyncio.run(
                        upload_generated_image(result_img, user_id)
                    )
                    if not original_url or not preview_url:
                        raise RuntimeError("Score recognition image upload failed")
                    reply_messages.append(
                        ImageMessage(
                            original_content_url=original_url,
                            preview_image_url=preview_url,
                        )
                    )
            logger.info(
                "[Recognize] ✓ OCR completed: command=%s user_id=%s download=%.3fs "
                "total_before_reply=%.3fs title=%s validation=%s",
                command,
                user_id,
                download_seconds,
                time.perf_counter() - request_started_at,
                (result.get("parsed") or {}).get("title"),
                result.get("validation"),
            )
    except Exception as e:
        logger.error("[Recognize] ✗ OCR failed: user_id=%s error=%s", user_id, e, exc_info=True)
        notify_admins_error(
            error_title="Score Recognition Failed",
            error_details=f"{type(e).__name__}: {str(e)}\n\n{traceback.format_exc()}",
            context={"Task": "recognize", "QuotedMessageId": quoted_message_id},
            user_id=user_id,
        )
        reply_messages = [generate_status_flex(
            language_catalog("main.recognition_failed_title"),
            language_catalog("main.recognition_failed_body"),
            user_id,
            tone="danger",
        )]

    try:
        reply_started_at = time.perf_counter()
        smart_reply(
            user_id,
            event.reply_token,
            reply_messages,
            configuration,
            addition=False,
            source_type=source_type,
        )
        logger.info(
            "[Recognize] ✓ Reply completed: command=%s user_id=%s reply=%.3fs total=%.3fs",
            command,
            user_id,
            time.perf_counter() - reply_started_at,
            time.perf_counter() - request_started_at,
        )
    except Exception as e:
        logger.error("[Recognize] ✗ Reply failed: user_id=%s error=%s", user_id, e, exc_info=True)
        notify_admins_error(
            error_title="Score Recognition Reply Failed",
            error_details=f"{type(e).__name__}: {str(e)}\n\n{traceback.format_exc()}",
            context={"Task": "recognize_reply", "QuotedMessageId": quoted_message_id},
            user_id=user_id,
        )


def _enqueue_score_recognition_task(event, command: str, quoted_message_id: str, force_flex: bool = False) -> None:
    user_id = event.source.user_id
    source_type = getattr(event.source, 'type', 'user')
    task_id = f"image_query_{user_id}_{datetime.now().timestamp()}"
    nickname = get_user_nickname_wrapper(user_id, use_cache=True)
    track_queued(task_tracking, task_tracking_lock, {
        'id': task_id,
        'function': f"score_{command}",
        'queue_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'user_id': user_id,
        'nickname': nickname,
    })
    try:
        show_loading(user_id)
        image_query_queue.put_nowait((
            _score_recognition_queue_task,
            (event, command, quoted_message_id, force_flex),
            task_id,
        ))
    except queue.Full:
        discard_queued(task_tracking, task_tracking_lock, task_id)
        smart_reply(
            user_id,
            event.reply_token,
            access_error(user_id),
            configuration,
            source_type=source_type,
        )


def _handle_recognize_command(event, cleaned_text: str) -> bool:
    command_text = cleaned_text.strip().lower()
    command_match = re.fullmatch(r"(?P<command>ai-rec|rec|crop)(?:\s+(?P<suffix>-flex))?", command_text)
    if not command_match:
        return False
    command = command_match.group("command")
    force_flex = bool(command_match.group("suffix"))
    if force_flex and command not in {"rec", "ai-rec"}:
        return False

    user_id = event.source.user_id
    source_type = getattr(event.source, 'type', 'user')
    quoted_message_id = getattr(event.message, 'quoted_message_id', None)

    if not quoted_message_id:
        smart_reply(
            user_id,
            event.reply_token,
            generate_status_flex(
                language_catalog("main.score_image_required_title"),
                format_catalog(
                    "main.score_image_required_body",
                    command_text=command_text,
                ),
                user_id,
                tone="warning",
            ),
            configuration,
            addition=False,
            source_type=source_type,
        )
        return True

    from modules.commands.command_config import require_command_access
    try:
        require_command_access(user_id, command)
    except PermissionError:
        smart_reply(
            user_id, event.reply_token, access_error(user_id), configuration,
            addition=False, source_type=source_type,
        )
        return True

    _enqueue_score_recognition_task(event, command, quoted_message_id, force_flex=force_flex)
    return True


def _bump_stats():
    with stats_lock:
        STATS['tasks_processed'] += 1


def _run_sync_handler(cmd, ctx, *, count_completion=True):
    if cmd.queue == QUEUE_SYNC:
        track_event("sync_cmd", user_id=ctx.user_id,
                    metadata={"command": cmd.name, "source": "line"})
    reply = cmd.handler(ctx)
    if reply is not None:
        if count_completion:
            _bump_stats()
        smart_reply(
            ctx.user_id,
            ctx.reply_token,
            reply,
            configuration,
            cmd.addition,
            source_type=ctx.source_type,
        )


def _image_worker_task(cmd, ctx):
    track_event("image_gen", user_id=ctx.user_id,
                metadata={"command": cmd.name, "source": "line"})
    _run_sync_handler(cmd, ctx, count_completion=False)


def _enqueue_task(cmd, ctx, target_queue, lane_name, payload):
    """通用入队 + task_tracking + show_loading + queue.Full 回退"""
    try:
        task_id = f"{lane_name}_{ctx.user_id}_{datetime.now().timestamp()}"
        nickname = get_user_nickname_wrapper(ctx.user_id, use_cache=True)
        track_queued(task_tracking, task_tracking_lock, {
            'id': task_id,
            'function': cmd.name or cmd.handler.__name__,
            'queue_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'user_id': ctx.user_id,
            'nickname': nickname,
        })
        show_loading(ctx.user_id)
        target_queue.put_nowait((*payload, task_id))
    except queue.Full:
        discard_queued(task_tracking, task_tracking_lock, task_id)
        smart_reply(
            ctx.user_id,
            ctx.reply_token,
            access_error(ctx.user_id),
            configuration,
            source_type=ctx.source_type,
        )


def _detect_command_help_key(text):
    return detect_command_help_key(
        text,
        b_command_words=HELP_B_COMMAND_WORDS,
        progress_rank_pattern=PROGRESS_RANK_PATTERN,
    )


def _reply_command_help_if_needed(ctx):
    if ctx.text.strip().lower() in HELP_INDEX_WORDS:
        _bump_stats()
        smart_reply(ctx.user_id, ctx.reply_token, _command_help_message("help_index", ctx.user_id),
                    configuration, addition=False, source_type=ctx.source_type)
        return True

    help_match = re.match(r"^(?P<body>.*?)\s*-help\s*$", ctx.text, re.IGNORECASE)
    if help_match:
        help_key = _detect_command_help_key(help_match.group("body"))
        reply = _command_help_message(help_key, ctx.user_id)
        if reply is None:
            reply = input_error(ctx.user_id)
        _bump_stats()
        smart_reply(ctx.user_id, ctx.reply_token, reply, configuration,
                    addition=False, source_type=ctx.source_type)
        return True

    help_key = _detect_missing_param_help_key(ctx.text)
    if help_key:
        if (
            help_key == "song_info"
            and getattr(ctx.event.message, "quoted_message_id", None)
        ):
            return False
        reply = _command_help_message(help_key, ctx.user_id)
        _bump_stats()
        smart_reply(ctx.user_id, ctx.reply_token, reply, configuration,
                    addition=False, source_type=ctx.source_type)
        return True

    return False


def dispatch_command(ctx):
    """扫 COMMANDS 表，找到第一个命中的命令并按 queue 派发。"""
    if _reply_command_help_if_needed(ctx):
        return True

    for cmd in COMMANDS:
        m = cmd.try_match(ctx.text)
        if m is None:
            continue
        ctx.match = m

        from modules.commands.command_config import require_command_access
        try:
            require_command_access(ctx.user_id, cmd.name)
        except PermissionError:
            smart_reply(ctx.user_id, ctx.reply_token, access_error(ctx.user_id),
                        configuration, addition=False, source_type=ctx.source_type)
            return True

        # 拦截 1：@ 别人但用了仅限本人的命令
        if cmd.self_only and ctx.has_other_mention:
            _bump_stats()
            smart_reply(ctx.user_id, ctx.reply_token,
                        cannot_do_for_others(ctx.user_id), configuration,
                        source_type=ctx.source_type)
            return True

        # 拦截 2：mention_queryable 命令 + @ 了未注册用户
        if (cmd.mention_queryable and ctx.has_other_mention
                and ctx.mentioned_user_id is None):
            _bump_stats()
            smart_reply(ctx.user_id, ctx.reply_token,
                        mention_error(ctx.user_id), configuration,
                        source_type=ctx.source_type)
            return True

        # 拦截 3：目标用户关闭了被 @ 查询成绩
        if cmd.mention_queryable and ctx.is_mention:
            if (ctx.target_user or {}).get("allow_mention_score_query", True) is False:
                _bump_stats()
                smart_reply(ctx.user_id, ctx.reply_token,
                            mention_not_allowed(ctx.user_id), configuration,
                            source_type=ctx.source_type)
                return True

        # 频率限制
        if cmd.rate_limit_key is not None:
            if check_rate_limit(ctx.user_id, cmd.rate_limit_key):
                smart_reply(ctx.user_id, ctx.reply_token,
                            rate_limit_msg(ctx.user_id), configuration,
                            source_type=ctx.source_type)
                return True

        # 派发
        if cmd.queue == QUEUE_SYNC:
            _run_sync_handler(cmd, ctx)
        elif cmd.queue == QUEUE_IMAGE:
            _enqueue_task(cmd, ctx, image_queue, "image",
                          (_image_worker_task, (cmd, ctx)))
        elif cmd.queue == QUEUE_WEB:
            # web handler 签名 (event) → 兼容现有 async_*_task
            _enqueue_task(cmd, ctx, webtask_queue, "web",
                          (cmd.handler, (ctx,)))
        return True
    return False


# ---- B 系列命令的 first-word 集合（从 RANK_COMMANDS 自动展开）----
_B_COMMAND_WORDS = rank_command_words()
HELP_B_COMMAND_WORDS = rank_command_words(hidden=HIDDEN_HELP_COMMAND_WORDS)


def cmd_status(ctx):
    return get_bot_status(ctx.user_id)


# ---- 命令注册表 ----
# 顺序：web > image > sync。同一文本不应被多个命令命中，命中即停。
# self_only=True 集合与旧 _SELF_ONLY_EXACT_COMMANDS 保持一致（preserves prior behavior）。
COMMANDS = [
    # ============ Web tasks ============
    Command(Exact("maimai update", "update"),
            async_maimai_update_task, queue=QUEUE_WEB,
            self_only=True, rate_limit_key="async_maimai_update_task",
            name="maimai_update"),
    Command(Exact("friend list", "friends"),
            async_get_friend_list_task, queue=QUEUE_WEB,
            rate_limit_key="async_get_friend_list_task",
            name="friend_list"),
    Command(Prefix("friend-rcd "),
            async_generate_friend_record_task, queue=QUEUE_WEB,
            rate_limit_key="async_generate_friend_record_task",
            name="friend_rcd"),
    Command(Regex(r"^(?:record|.+\s+record)$", re.IGNORECASE),
            async_get_song_record_task, queue=QUEUE_WEB,
            mention_queryable=True,
            rate_limit_key="async_get_song_record_task",
            name="song_record"),

    # ============ Image tasks ============
    Command(Regex(r"^.+\s+records[ 　]*\d*$", re.IGNORECASE),
            cmd_level_records, queue=QUEUE_IMAGE, mention_queryable=True,
            name="level_records"),
    Command(Regex(
        fr"^.+\s*{PROGRESS_RANK_PATTERN}\s*prog\s*(?:-(uc|up|c))?\s*$",
        re.IGNORECASE),
            cmd_level_rank_progress, queue=QUEUE_IMAGE, mention_queryable=True,
            name="level_rank_progress"),
    Command(Regex(r"^(?:info|.+(?:\s+info|ってどんな曲))$", re.IGNORECASE),
            cmd_song_info, queue=QUEUE_IMAGE,
            name="song_info"),
    Command(Regex(r"^.+\s+plate(\s*-(uc|up|c))?\s*$", re.IGNORECASE),
            cmd_plate, queue=QUEUE_IMAGE, mention_queryable=True,
            name="plate"),
    Command(Regex(r"^.+\s+ver$", re.IGNORECASE),
            cmd_version_songs, queue=QUEUE_IMAGE,
            name="version_songs"),
    Command(Regex(r"^.+\s+levels$", re.IGNORECASE),
            cmd_level_rank_list, queue=QUEUE_IMAGE,
            name="level_rank_list"),
    Command(FirstWord(*_B_COMMAND_WORDS),
            cmd_b_records, queue=QUEUE_IMAGE, mention_queryable=True,
            rate_limit_key="image:b_series",
            name="b_records"),
    Command(Prefix("random"),
            cmd_random_song, queue=QUEUE_IMAGE,
            name="random_song"),

    # ============ Sync commands ============
    Command(Exact("unbind"), cmd_unbind_prompt,
            self_only=True, addition=False, name="unbind_prompt"),
    Command(Exact("bind"), cmd_bind,
            self_only=True, addition=False, name="bind"),
    Command(Exact("rebind"), cmd_rebind,
            self_only=True, addition=False, name="rebind"),
    Command(Exact("settings"), cmd_settings,
            self_only=True, addition=False, name="settings"),

    Command(Exact("profile", "getme"), cmd_profile, name="profile"),
    Command(Exact("status"), cmd_status, name="status"),
    Command(Exact("refreshmenu"), cmd_refresh_menu,
            self_only=True, addition=False, name="refreshmenu"),

    Command(Regex(r"^(rank|ranking)(\s+(jp|intl))?$"),
            cmd_ranking, mention_queryable=True, name="ranking"),
    Command(Prefix("artist "), cmd_artist, name="search_by_artist"),
    Command(Prefix("designer "), cmd_designer, name="search_by_designer"),
    Command(Prefix("bpm "), cmd_bpm, name="search_by_bpm"),
    Command(Prefix("rc "), cmd_rc, name="rc"),

    Command(Regex(r"^(成績エクスポート|成绩导出|export)\s+(json|xml)\s*$",
                  re.IGNORECASE),
            cmd_export, self_only=True, name="export"),

    Command(Prefix("calc "), cmd_calc_notes, name="calc_notes"),
]

_plugin_commands = load_plugin_commands(PLUGIN_CONFIG)
COMMANDS = [
    *_plugin_commands.before_core,
    *COMMANDS,
    *_plugin_commands.after_core,
]


@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event):
    mark_message_as_read(getattr(event.message, 'mark_as_read_token', None),
                         event.source.user_id)

    # @ALL / 3+ mention → 忽略
    if check_mention_filter(event):
        return
    original_text = event.message.text
    cleaned_text, cleaned_multiline_text = clean_message_text(event)
    event.message.text = cleaned_text  # 兼容下游 async_*_task 读 event.message.text

    if original_text != cleaned_text:
        logger.debug(f"[TextCleaning] Cleaned mention: original='{original_text}', cleaned='{cleaned_text}'")

    if _handle_fix_record_command(event, cleaned_multiline_text):
        return

    if _handle_recognize_command(event, cleaned_text):
        return

    ctx = _build_command_context(event, cleaned_text)
    plugin_session_reply = dispatch_plugin_session(ctx)
    if plugin_session_reply is not None:
        _bump_stats()
        smart_reply(
            ctx.user_id,
            ctx.reply_token,
            plugin_session_reply,
            configuration,
            source_type=ctx.source_type,
        )
        return

    if ctx.text.startswith("/"):
        ctx.text = ctx.text[1:].lstrip()
        event.message.text = ctx.text

    dispatch_command(ctx)

# ==================== 任务处理函数 ====================

@handler.add(MessageEvent, message=LocationMessageContent)
def handle_location_message(event):
    """
    位置消息处理 - 异步获取附近机厅
    """
    # 标记消息为已读（使用 webhook 提供的 token）
    mark_as_read_token = getattr(event.message, 'mark_as_read_token', None)
    mark_message_as_read(mark_as_read_token, event.source.user_id)

    lat = event.message.latitude
    lng = event.message.longitude
    user_id = event.source.user_id

    stores = asyncio.run(get_nearby_maimai_stores(lat, lng))

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
        source_type=getattr(event.source, 'type', 'user')
    )


def handle_postback_command(event, text):
    """Handle button-only commands before falling back to text dispatch."""
    user_id = event.source.user_id
    source_type = getattr(event.source, 'type', 'user')
    cleaned = re.sub(r"\s+", " ", text.strip())

    help_match = re.fullmatch(r"help\s+([A-Za-z0-9_]+)", cleaned, re.IGNORECASE)
    if help_match:
        reply_msg = _command_help_message(help_match.group(1), user_id)
        if reply_msg is None:
            reply_msg = input_error(user_id)
        smart_reply(user_id, event.reply_token, reply_msg, configuration,
                    addition=False, source_type=source_type)
        return True

    accept_match = re.fullmatch(r"accept-perm-request\s+(\S+)", cleaned, re.IGNORECASE)
    if accept_match:
        reply_msg = handle_accept_perm_request(user_id, accept_match.group(1))
        smart_reply(user_id, event.reply_token, reply_msg, configuration,
                    source_type=source_type)
        return True

    reject_match = re.fullmatch(r"reject-perm-request\s+(\S+)", cleaned, re.IGNORECASE)
    if reject_match:
        reply_msg = handle_reject_perm_request(user_id, reject_match.group(1))
        smart_reply(user_id, event.reply_token, reply_msg, configuration,
                    source_type=source_type)
        return True

    search_match = re.fullmatch(r"search-song\s+(\S{6})", cleaned, re.IGNORECASE)
    if search_match:
        if source_type == "user":
            show_loading(user_id)
        ver = get_user_field(user_id, 'version') or "jp"
        reply_msg = asyncio.run(search_song_by_id(user_id, search_match.group(1), ver))
        smart_reply(user_id, event.reply_token, reply_msg, configuration,
                    addition=False, source_type=source_type)
        return True

    calc_match = re.fullmatch(r"calc-song\s+(\S{6})", cleaned, re.IGNORECASE)
    if calc_match:
        ver = get_user_field(user_id, 'version') or "jp"
        reply_msg = calc_by_id(user_id, calc_match.group(1), ver)
        smart_reply(user_id, event.reply_token, reply_msg, configuration,
                    addition=False, source_type=source_type)
        return True

    record_match = re.fullmatch(r"search-record\s+(\S{6})(?:&id_use=(\S+))?", cleaned, re.IGNORECASE)
    if record_match:
        if source_type == "user":
            show_loading(user_id)
        ver = get_user_field(user_id, 'version') or "jp"
        id_use = record_match.group(2) or user_id
        reply_msg = asyncio.run(get_song_record_by_id(user_id, id_use, record_match.group(1), ver))
        smart_reply(user_id, event.reply_token, reply_msg, configuration,
                    source_type=source_type)
        return True

    return False


# Postback 事件处理
@handler.add(PostbackEvent)
def handle_postback(event):
    user_id = event.source.user_id
    postback_data = event.postback.data

    logger.debug(f"[Postback] user_id={user_id}, data={postback_data}")

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
                    lang = get_user_language(user_id)

                    total_votes = stats['support_count'] + stats['oppose_count']
                    vote_success_text = format_catalog(
                        "main.vote_success",
                        support_count=stats['support_count'],
                        support_percent=stats['support_count'] / total_votes * 100 if total_votes else 0,
                        oppose_count=stats['oppose_count'],
                        oppose_percent=stats['oppose_count'] / total_votes * 100 if total_votes else 0,
                    )

                    reply_message = TextMessage(text=select_text(vote_success_text, language=lang, default_language=DEFAULT_WEB_LANGUAGE))

                    # 发送回复
                    smart_reply(user_id, event.reply_token, reply_message, configuration, addition=False)

                    logger.info(f"[Notice] ✓ Vote processed: user_id={user_id}, notice_id={notice_id}, vote={vote_type}")
                    return
                else:
                    logger.error(f"[Notice] ✗ Vote failed: user_id={user_id}, notice_id={notice_id}")
                    return

        if handle_postback_command(event, postback_data):
            return

        mock_event = SimpleNamespace(
            source=event.source,
            reply_token=event.reply_token,
            message=SimpleNamespace(text=postback_data, type='text'),
        )
        dispatch_command(_build_command_context(mock_event, postback_data))

    except Exception as e:
        logger.error(f"[Postback] ✗ Error processing postback: user_id={user_id}, data={postback_data}, error={e}")
        logger.debug("[Postback] traceback:\n%s", traceback.format_exc())


# Follow 事件处理
@handler.add(FollowEvent)
def handle_follow(event):
    user_id = event.source.user_id
    reply_token = event.reply_token

    add_user(user_id)
    link_rich_menu_for_state(user_id, get_user(user_id))
        
    bind_url = _account_action_url(
        "bind",
        "sega_bind",
        token=generate_bind_token(user_id),
    )
    reply_message = generate_welcome_flex(user_id, bind_url=bind_url)

    return smart_reply(user_id, reply_token, reply_message, configuration, False)


# Unfollow 事件处理
@handler.add(UnfollowEvent)
def handle_unfollow(event):
    user_id = event.source.user_id
    logger.info(f"[UnfollowEvent] {user_id} left")
    unlink_rich_menu(user_id)
    track_event("user_unbind", user_id=user_id, metadata={"source": "line_unfollow"})
    return delete_user(user_id)


# Join 事件处理
@handler.add(JoinEvent)
def handle_join(event):
    reply_token = event.reply_token
    group_id = event.source.group_id
    logger.info(f"[JoinEvent] Joined {group_id}")
    reply_msg = generate_welcome_flex(group=True)
    return smart_reply(None, reply_token, reply_msg, configuration, False)


# MemberJoined 事件处理
@handler.add(MemberJoinedEvent)
def handle_member_joined(event):
    reply_token = event.reply_token
    logger.info(f"[MemberJoinedEvent] New Member(s) Joined")
    reply_msg = generate_welcome_flex(group=True)
    return smart_reply(None, reply_token, reply_msg, configuration, False)


# Default 事件处理 - 未匹配的事件类型，已读并忽略
@handler.default()
def handle_default(event):
    logger.debug(f"[DefaultHandler] Unhandled event: {event.__class__.__name__}")
    mark_as_read_token = getattr(getattr(event, 'message', None), 'mark_as_read_token', None)
    mark_message_as_read(mark_as_read_token)


# ==================== 管理后台路由 ====================

# 任务队列追踪
task_tracking = {
    'running': [],
    'queued': [],
    'completed': []  # 存储已完成的任务 (最多保留20个)
}
task_tracking_lock = threading.Lock()
MAX_COMPLETED_TASKS = 20  # 最多保留20个已完成任务
def _fallback_user_nickname(user_id):
    return f"User {user_id[:8]}..."


def get_user_nickname_wrapper(user_id, use_cache=True):
    stored_nick = get_user_field(user_id, 'nickname')
    if use_cache and stored_nick:
        return stored_nick

    nickname = None

    # 尝试从LINE API获取昵称
    try:
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            nickname = get_user_nickname(user_id, line_bot_api, use_cache)

            # 检查是否为错误消息
            if nickname and ("Unknown" in nickname or "API Error" in nickname or "Blocked" in nickname):
                nickname = None
            elif nickname:
                edit_user_value(user_id, 'nickname', nickname)
    except Exception as e:
        logger.debug(f"[User] Failed to get LINE nickname: user_id={user_id}, error={e}")
        nickname = None

    # 如果LINE API失败,尝试从用户数据获取
    if not nickname and stored_nick:
        nickname = stored_nick

    return nickname if nickname else _fallback_user_nickname(user_id)


def _build_admin_overview_stats(force_refresh=False):
    """Build compact metrics for the admin console overview."""
    all_users = load_all_users()
    total_users = len(all_users)
    jp_users = sum(1 for user in all_users.values() if user.get("version") == "jp")
    intl_users = sum(1 for user in all_users.values() if user.get("version") == "intl")

    uptime = datetime.now() - SERVICE_START_TIME
    days = uptime.days
    hours, remainder = divmod(uptime.seconds, 3600)
    minutes, _seconds = divmod(remainder, 60)
    uptime_str = f"{days}d {hours}h {minutes}m"

    cpu_percent = round(psutil.cpu_percent(interval=0.1), 1)
    cpu_count = psutil.cpu_count()
    memory = psutil.virtual_memory()
    process_memory_stats = get_process_memory_stats()

    with stats_lock:
        task_stats = dict(STATS)

    stats = {
        'total_users': total_users,
        'jp_users': jp_users,
        'intl_users': intl_users,
        'cpu_percent': cpu_percent,
        'cpu_count_total': cpu_count,
        'memory_percent': round(memory.percent, 1),
        'memory_used_gb': round(memory.used / (1024**3), 1),
        'total_memory': round(memory.total / (1024**3), 1),
        **process_memory_stats,
        'uptime': uptime_str,
        'python_version': platform.python_version(),
        'platform': f"{platform.system()} {platform.release()}",
        'hostname': socket.gethostname(),
        'port': PORT,
        'image_queue_size': image_queue.qsize(),
        'image_query_queue_size': image_query_queue.qsize(),
        'web_queue_size': webtask_queue.qsize(),
        'max_queue_size': MAX_QUEUE_SIZE,
        'thread_count': threading.active_count(),
        'total_tasks_processed': task_stats['tasks_processed'],
        'total_tasks_failed': task_stats['tasks_failed'],
        'total_tasks_timed_out': task_stats['tasks_timed_out'],
        **summarize_task_activity(task_tracking, task_tracking_lock),
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    stats.update(get_business_stats(force_refresh=force_refresh))
    return stats


configure_admin_api(
    overview=_build_admin_overview_stats,
    nickname=get_user_nickname_wrapper,
    fallback_nickname=_fallback_user_nickname,
    update_task=async_admin_maimai_update_task,
    task_queue=webtask_queue,
    task_tracking=task_tracking,
    task_tracking_lock=task_tracking_lock,
)
configure_developer_api(
    configuration=configuration,
    nickname=get_user_nickname_wrapper,
    process_credentials=process_sega_credentials,
    sync_user_data=_sync_maimai_user_data,
    sync_timeout=TASK_TIMEOUT_SECONDS,
)
configure_image_api(
    background_filter=_get_user_bg_filter,
    generate_profile=generate_profile,
    select_records=select_records,
)


_runtime_started = False
_runtime_lock = threading.Lock()
_runtime_atexit_registered = False
_runtime_shutdown = False


def _shutdown_runtime():
    global _runtime_shutdown

    with _runtime_lock:
        if _runtime_shutdown:
            return
        _runtime_shutdown = True

    save_dev_tokens(force=True)
    shutdown_event_tracker()
    shutdown_export_cleanup()
    memory_manager.stop()
    close_pool()
    logger.info("[System] Runtime resources stopped")


def start_runtime():
    """启动数据库初始化、后台队列 worker 和定期任务。"""
    global _runtime_started, _runtime_atexit_registered

    with _runtime_lock:
        if _runtime_started:
            return
        _runtime_started = True

    # ==================== 系统启动自检 ====================
    # 在启动 worker 线程之前执行系统自检
    logger.info("[System] → Starting JiETNG Maimai DX LINE Bot...")

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

    try:
        logger.info("[Recognize] → Initializing OCR engine...")
        initialize_score_recognizer()
        logger.info("[Recognize] ✓ OCR engine initialized")
    except Exception as e:
        logger.error("[Recognize] ✗ OCR engine initialization failed: error=%s", e, exc_info=True)
        notify_admins_error(
            error_title="Score OCR Initialization Failed",
            error_details=f"{type(e).__name__}: {str(e)}\n\n{traceback.format_exc()}",
            context={"Task": "recognize_startup"},
        )
        logger.info("[Recognize] → Continuing startup; recognize command will fail until OCR is fixed")

    try:
        from modules.score_recognition.cropper import warm_cropper_models

        warm_cropper_models()
        logger.info('[Recognize] YOLO models warmed up')
    except Exception:
        logger.exception('[Recognize] YOLO startup warmup failed')

    try:
        from modules.images.renderer import warm_renderer

        warm_renderer()
        logger.info('[Renderer] Browser warmed up')
    except Exception:
        logger.exception('[Renderer] Startup warmup failed; next render will retry')

    # 启动 worker 线程
    for i in range(MAX_CONCURRENT_IMAGE_TASKS):
        threading.Thread(target=image_worker, daemon=True, name=f"ImageWorker-{i+1}").start()

    for i in range(IMAGE_QUERY_MAX_CONCURRENT_TASKS):
        threading.Thread(target=image_query_worker, daemon=True, name=f"ImageQueryWorker-{i+1}").start()

    for i in range(WEB_MAX_CONCURRENT_TASKS):
        threading.Thread(target=webtask_worker, daemon=True, name=f"WebTaskWorker-{i+1}").start()

    logger.info(
        "[System] ✓ Workers started: image=%s, image_query=%s, web=%s",
        MAX_CONCURRENT_IMAGE_TASKS,
        IMAGE_QUERY_MAX_CONCURRENT_TASKS,
        WEB_MAX_CONCURRENT_TASKS,
    )

    # 启动定期清理线程（图床 + 成绩导出）
    _start_periodic_cleanup()
    start_export_cleanup()

    # 启动 dxdata 每周日 22:00 自动更新（服务器本地时间）
    start_dxdata_weekly_update(DXDATA_URL, DXDATA_FILE)

    def custom_cleanup():
        """自定义清理函数"""
        try:
            # 清理用户昵称缓存
            cleaned_nicknames = cleanup_user_caches(user_manager_module)

            # 清理频率限制追踪数据
            cleaned_rate_limits = cleanup_rate_limiter_tracking()

            # 清理空闲的 API 同步锁
            cleaned_api_sync_locks = cleanup_api_sync_locks()

            cleaned_score_ocr = cleanup_score_recognizer_memory()

            # 清理未绑定的用户（没有 sega_id 或 sega_pwd）
            cleanup_result = clean_unbound_users()
            cleaned_unbound_users = cleanup_result.get('deleted_count', 0)

            # 刷新 dev tokens 缓存到磁盘
            flush_dev_tokens()

            logger.info(f"[System] ✓ Custom cleanup completed: nicknames={cleaned_nicknames}, rate_limits={cleaned_rate_limits}, api_sync_locks={cleaned_api_sync_locks}, score_ocr={cleaned_score_ocr}, unbound_users={cleaned_unbound_users}")
        except Exception as e:
            logger.error(f"[System] ✗ Custom cleanup error: error={e}", exc_info=True)

    memory_manager.register_cleanup(custom_cleanup)
    memory_manager.start()
    logger.info("[System] ✓ Memory manager started")

    if not _runtime_atexit_registered:
        atexit.register(_shutdown_runtime)
        _runtime_atexit_registered = True


start_runtime()


if __name__ == "__main__":
    try:
        app.run(host=HOST, port=PORT, threaded=True)

    finally:
        _shutdown_runtime()
