"""
JiETNG Maimai DX LINE Bot 主程序
"""

import os
import random
import requests
import json
import re
import traceback
import threading
import queue
import psutil
import platform
import socket
import secrets
import asyncio
import aiohttp
import atexit
import time
import gc
import math
import base64 as b64mod

from datetime import datetime
from types import SimpleNamespace

from PIL import Image, ImageDraw
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
from modules.song_generator import (
    generate_version_list,
    song_info_generate,
)
from modules.record_generator import (
    generate_cover,
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
from modules.notice_manager import get_notice_by_id
from modules.notice_stats import calculate_notice_stats
from modules.tip_ad_manager import load_tip_ad_data
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
    login_to_maimai,
    parse_level_value,
)
from modules.score_calculator import get_note_score
from modules.dxdata_manager import start_weekly_update_scheduler as start_dxdata_weekly_update
from modules.record_manager import (
    achievement_value,
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
    LOGO_FILE,
    LOG_FILE,
    MAIMAI_VERSION,
    PLUGIN_CONFIG,
    PORT,
    TEMP_VERSION,
    load_user,
    read_dxdata,
)

from modules.message_manager import (
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
    generate_score_recognition_flex,
    generate_search_results_flex,
    generate_song_info_flex,
    generate_song_list_flex,
    generate_status_flex,
    generate_update_result_flex,
    generate_user_info_flex,
    generate_welcome_flex,
    get_friend_list_alt_text,
    get_multilingual_text,
    get_nearby_stores_alt_text,
    get_user_language,
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

# Image processing
from modules.image_uploader import upload_generated_image, _start_periodic_cleanup
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
from modules.api.api_auth import (
    maimai_session_cors as _maimai_session_cors,
)
from modules.logging_config import configure_logging
from modules.web_i18n import (
    error_page as _error_page,
    register_web_i18n,
)
from modules.commands.command_router import (
    Exact, Prefix, Regex, FirstWord,
    Command, CommandContext,
    QUEUE_SYNC, QUEUE_IMAGE, QUEUE_WEB,
)
from modules.plugin_manager import dispatch_plugin_session, load_plugin_commands
from modules.commands.command_parsers import (
    format_bpm_number,
    parse_bpm_number,
    parse_bpm_query,
    parse_filter_mode,
    parse_level_records_query,
    parse_note_counts,
    parse_paginated_keyword,
    parse_plate_query,
)
from modules.dbpool_manager import close_pool
from modules.image_manager import (
    compose_generated_images,
    font_profile,
    font_trophy,
    round_corner,
    truncate_text,
)

# System utilities
from modules.system_checker import run_system_check, clean_unbound_users
from modules.event_tracker import (
    get_business_stats,
    shutdown_event_tracker,
    track_event,
)
from modules.rate_limiter import check_rate_limit
from modules.line_messenger import smart_reply, smart_push, notify_admins_error, notify_on_error
from modules.rich_menu_manager import (
    link_bound_rich_menu,
    link_rich_menu_for_state,
    link_unbound_rich_menu,
    unlink_rich_menu,
)
from modules.song_matcher import find_matching_songs, normalize_text
from modules.memory_manager import memory_manager, cleanup_user_caches, cleanup_rate_limiter_tracking
from modules.i18n import (
    DEFAULT_LANGUAGE,
    DEFAULT_WEB_LANGUAGE,
    format_catalog,
    language_catalog,
    normalize_language,
    select_text,
)
from modules.score_result_recognizer import (
    InvalidScoreImageError,
    build_score_crop_preview_image,
    cleanup_score_recognizer_memory,
    expand_score_recognition_calc_variants,
    initialize_score_recognizer,
    parse_fix_record_command,
    recognize_score_image_bytes,
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
from modules.commands.progress_parser import (
    PROGRESS_RANK_PATTERN,
    parse_level_rank_progress as _parse_level_rank_progress_text,
    resolve_progress_category as _resolve_progress_category,
)
from modules.task_runtime import (
    TaskOutcome,
    discard_queued,
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

# Module aliases for specific use cases
import modules.user_manager as user_manager_module
import modules.rate_limiter as rate_limiter_module

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

# ==================== 日志配置 ====================

logger = configure_logging(LOG_FILE, __name__)

app = Flask(__name__, static_folder='assets', static_url_path='/static')
app.secret_key = secrets.token_hex(32)  # 用于session加密
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

    # Content Security Policy
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "script-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob: https:; "
        "font-src 'self' data:;"
    )

    # Strict Transport Security (如果使用 HTTPS)
    # response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

    # 每次请求后执行快速垃圾回收（generation 0）
    gc.collect(0)

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
    notify_admins_error(
        error_title=f"Task Execution Failed: {func.__name__}",
        error_details=f"{type(error).__name__}: {error}\n\n{traceback_text}",
        context={"Task": func.__name__, "Error Type": type(error).__name__},
        user_id=context.user_id,
    )
    if context.user_id and context.reply_token:
        try:
            smart_reply(
                context.user_id,
                context.reply_token,
                system_error(context.user_id),
                configuration,
                source_type=context.source_type,
            )
        except Exception:
            pass


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
        try:
            for _ev in json_data.get('events', []):
                _uid = _ev.get('source', {}).get('userId')
                track_event('line_webhook', user_id=_uid, metadata={'type': _ev.get('type')})
        except Exception:
            pass

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
            except Exception:
                pass

        _notif_uid = None
        if not is_bad_request:
            try:
                _notif_uid = json_data.get('events', [{}])[0].get('source', {}).get('userId')
            except Exception:
                pass
        notify_admins_error(
            error_title="Webhook Error",
            error_details=f"{type(e).__name__}: {str(e)}\n\n{traceback.format_exc()}",
            context={"Error": type(e).__name__, "Detail": str(e)[:200]},
            user_id=_notif_uid
        )

    return 'OK', 200

@app.route("/static/admin-icon.png")
def admin_pwa_icon():
    """动态生成带背景和留白的 PWA 图标"""
    size = 512
    padding = int(size * 0.18)  # 18% 留白
    logo_size = size - padding * 2

    bg_color = (22, 33, 62, 255)  # 深蓝背景，与 admin panel 风格一致

    canvas = Image.new('RGBA', (size, size), bg_color)

    with Image.open(LOGO_FILE) as logo:
        logo = logo.convert('RGBA')
        logo = logo.resize((logo_size, logo_size), Image.LANCZOS)
        canvas.paste(logo, (padding, padding), logo)

    buf = BytesIO()
    canvas.convert('RGB').save(buf, 'PNG')
    buf.seek(0)
    return send_file(buf, mimetype='image/png')


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
            try:
                timezone_int = int(user_timezone)
            except (ValueError, TypeError):
                timezone_int = 9

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

            if candidates == "MAINTENANCE":
                message = language_catalog("main.maintenance")
                return jsonify({"success": False, "message": select_text(message, language=user_language, default_language=DEFAULT_WEB_LANGUAGE)}), 503

            if not candidates:
                message = language_catalog("main.invalid_credentials")
                return jsonify({"success": False, "message": select_text(message, language=user_language, default_language=DEFAULT_WEB_LANGUAGE)}), 401

            return jsonify({"success": True, "candidates": candidates})

        # 转换时区为整数
        try:
            timezone_int = int(user_timezone)
        except (ValueError, TypeError):
            timezone_int = 9  # 默认 UTC+9

        # 转换 aime 为整数
        try:
            aime_int = int(aime)
        except (ValueError, TypeError):
            aime_int = 0  # 默认 0

        result = asyncio.run(process_sega_credentials(user_id, segaid, password, user_version, user_language, timezone_int, aime_int, (mode == "rebind")))
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

        # 转换时区为整数
        try:
            timezone_int = int(user_timezone)
        except (ValueError, TypeError):
            timezone_int = 9

        # 解析背景图列表
        if bg_files_str.strip():
            bg_files_list = [f.strip() for f in bg_files_str.split(",") if f.strip()]
        else:
            bg_files_list = []

        # 处理背景图开关
        bg_enabled = request.form.get("bg_enabled_hidden", "0") == "1"

        try:
            bg_blur = int(bg_blur_raw)
        except (ValueError, TypeError):
            bg_blur = 20
        bg_blur = max(0, min(40, bg_blur))

        try:
            bg_overlay = int(bg_overlay_raw)
        except (ValueError, TypeError):
            bg_overlay = 40
        bg_overlay = max(0, min(120, bg_overlay))

        # 保存设置
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
    except Exception:
        all_bg_files = []
        existing_custom_bg_files = []

    user_bg_files = user_data.get("bg_files", [])
    bg_enabled = user_data.get("bg_enabled", False)
    try:
        bg_blur = int(user_data.get("bg_blur", 20))
    except (ValueError, TypeError):
        bg_blur = 20
    bg_blur = max(0, min(40, bg_blur))
    try:
        bg_overlay = int(user_data.get("bg_overlay", 40))
    except (ValueError, TypeError):
        bg_overlay = 40
    bg_overlay = max(0, min(120, bg_overlay))

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
    except Exception:
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
    except Exception:
        return jsonify({"success": False, "message": "Invalid token"}), 400

    ALLOWED_BG_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.heic', '.heif'}
    MAX_BG_SIZE = 5 * 1024 * 1024
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
                logger.info(f"[Settings] ✓ Deleted custom bg: user_id={user_id}")
            except FileNotFoundError:
                pass
            except Exception as e:
                logger.error(f"[Settings] ✗ Failed to delete custom bg: user_id={user_id}, error={e}")
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
    if original_ext not in ALLOWED_BG_EXTENSIONS:
        return jsonify({"success": False, "message": "Unsupported format"}), 400

    try:
        file_data = b64mod.b64decode(body['data'])
    except Exception:
        return jsonify({"success": False, "message": "Invalid data"}), 400

    if len(file_data) > MAX_BG_SIZE:
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
        logger.info(f"[Settings] ✓ Uploaded custom bg: user_id={user_id}, ext={original_ext}, size={len(file_data)}")
    except Exception as e:
        logger.error(f"[Settings] ✗ Failed to process uploaded bg: user_id={user_id}, ext={original_ext}, error={e}")
        return jsonify({"success": False, "message": "Invalid image"}), 400

    return jsonify({"success": True, "filename": custom_bg_filename}), 201


def _get_user_bg_filter(user_id):
    udata = get_user(user_id) or {}
    if not udata.get('bg_enabled', False):
        return None
    bg_files = udata.get('bg_files', [])
    try:
        bg_blur = int(udata.get('bg_blur', 20))
    except (ValueError, TypeError):
        bg_blur = 20
    try:
        bg_overlay = int(udata.get('bg_overlay', 40))
    except (ValueError, TypeError):
        bg_overlay = 40
    return {
        "files": bg_files,
        "blur": max(0, min(40, bg_blur)),
        "overlay": max(0, min(120, bg_overlay)),
    }


def _compose_user_images(images, user_id):
    return compose_generated_images(
        images,
        timezone_offset=get_user_timezone(user_id),
        bg_filter=_get_user_bg_filter(user_id),
    )


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
        buf = BytesIO()
        if result.mode == "RGBA":
            result = Image.alpha_composite(Image.new("RGBA", result.size, (255, 255, 255, 255)), result)
        result.convert("RGB").save(buf, "JPEG", quality=88, optimize=True, progressive=True)
        buf.seek(0)
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
        if not cookies or cookies == "MAINTENANCE":
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
        if result == "MAINTENANCE":
            return _demo_cors(jsonify({"error": "The official website is under maintenance. Please try again later."})), 503
        if not result:
            return _demo_cors(jsonify({"error": "Login failed. Please check your SEGA ID and password."})), 401
        buf = BytesIO()
        if result.mode == "RGBA":
            result = Image.alpha_composite(Image.new("RGBA", result.size, (255, 255, 255, 255)), result)
        result.convert("RGB").save(buf, "JPEG", quality=88, optimize=True, progressive=True)
        buf.seek(0)
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
    if cookies == "MAINTENANCE":
        return "MAINTENANCE"
    if not cookies:
        logger.warning(f"[Auth] ⚠ Login failed for user_id={user_id}")
        return False

    # 验证登录是否成功
    connector = aiohttp.TCPConnector(ssl=False, limit=10)
    timeout = aiohttp.ClientTimeout(total=30, connect=10)
    async with aiohttp.ClientSession(cookies=cookies, connector=connector, timeout=timeout) as session:
        dom = await fetch_dom(session, f"{base}/home/", ver)

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

def async_maimai_update_task(event):
    """异步maimai更新任务 - 在webtask_queue中执行"""
    user_id = event.source.user_id
    reply_token = event.reply_token
    source_type = getattr(event.source, 'type', 'user')

    # 获取用户版本
    ver = "jp"
    _ver = get_user_field(user_id, 'version')
    if _ver is not None:
        ver = _ver

    try:
        reply_msg = asyncio.run(maimai_update(user_id, ver))
        track_event('sync_task', user_id=user_id, metadata={'success': True, 'trigger': 'user'})
    except Exception as e:
        track_event('sync_task', user_id=user_id, metadata={'success': False, 'trigger': 'user', 'error': str(e)[:200]})
        raise
    if reply_token:
        smart_reply(user_id, reply_token, reply_msg, configuration, source_type=source_type)

def async_get_friend_list_task(event):
    """异步获取好友列表任务 - 在webtask_queue中执行，实时登录SEGA抓取"""
    user_id = event.source.user_id
    reply_token = event.reply_token

    source_type = getattr(event.source, 'type', 'user')
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

def async_generate_friend_record_task(event):
    """异步生成好友成绩任务 - 在webtask_queue中执行"""
    user_message = event.message.text.strip()
    user_id = event.source.user_id
    reply_token = event.reply_token

    # 检查是否在群聊中发送
    source_type = getattr(event.source, 'type', 'user')
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
    ver = "jp"
    _ver = get_user_field(user_id, 'version')
    if _ver is not None:
        ver = _ver

    try:
        track_event('image_gen', user_id=user_id, metadata={'command': 'friend-rcd', 'source': 'line'})
    except Exception: pass

    # 直接通过网页爬取获取好友信息
    reply_msg = asyncio.run(generate_friend_record(user_id, friend_code, record_type, command, ver))

    smart_reply(user_id, reply_token, reply_msg, configuration, source_type=source_type)

def async_get_song_record_task(event):
    """异步歌曲成绩查询任务 - 在webtask_queue中执行"""
    user_message = event.message.text.strip()
    user_id = event.source.user_id
    reply_token = event.reply_token
    source_type = getattr(event.source, 'type', 'user')

    # 检查 @ mention（提取被提到的用户 ID）
    mentioned_user_id = extract_single_mention(event, user_id)

    # 初始化用户版本和目标用户
    _cur_user = get_user(user_id)
    if _cur_user:
        mai_ver = _cur_user.get("version", "jp")
        # 只有当 mentioned_user_id 存在且已注册时才使用
        id_use = mentioned_user_id if mentioned_user_id else user_id
        _target_user = get_user(id_use) if id_use != user_id else _cur_user
        mai_ver_use = _target_user.get("version", "jp") if _target_user else mai_ver
    else:
        id_use = user_id
        mai_ver = "jp"
        mai_ver_use = "jp"

    # 提取歌曲名称（移除命令后缀）
    acronym = re.sub(r"\s+record$", "", user_message, flags=re.IGNORECASE).strip()

    try:
        track_event('image_gen', user_id=user_id, metadata={'command': 'record', 'source': 'line'})
    except Exception: pass

    # 调用实际的查询函数
    reply_msg = asyncio.run(get_song_record(user_id, id_use, acronym, mai_ver_use))

    smart_reply(user_id, reply_token, reply_msg, configuration, source_type=source_type)

def async_get_song_record_by_id_task(event):
    """异步歌曲成绩查询任务（通过ID）- 在webtask_queue中执行"""
    user_message = event.message.text.strip()
    user_id = event.source.user_id
    reply_token = event.reply_token
    source_type = getattr(event.source, 'type', 'user')

    # 验证命令格式
    parts = user_message.split()
    if len(parts) < 2:
        smart_reply(user_id, reply_token, song_error(user_id), configuration, source_type=source_type)
        return

    # 提取歌曲ID并验证长度
    song_id = parts[1].split("&", 1)[0]
    if len(song_id) != 6:
        smart_reply(user_id, reply_token, song_error(user_id), configuration, source_type=source_type)
        return

    # 获取用户版本
    ver = "jp"
    id_use = user_id

    _ver = get_user_field(user_id, 'version')
    if _ver is not None:
        ver = _ver

    # 提取id_use参数
    if "id_use=" in user_message:
        id_use = user_message.split("id_use=", 1)[1]

    try:
        track_event('image_gen', user_id=user_id, metadata={'command': 'search-record', 'source': 'line'})
    except Exception: pass

    # 调用实际的查询函数
    reply_msg = asyncio.run(get_song_record_by_id(user_id, id_use, song_id, ver))

    smart_reply(user_id, reply_token, reply_msg, configuration, source_type=source_type)

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

async def _sync_maimai_user_data(user_id, ver="jp"):
    # 记录开始时间
    start_time = time.time()

    func_status = {
        "User Info": True,
        "Best Records": True,
        "Recent Records": True,
    }

    _udata = get_user(user_id)
    if not _udata or 'sega_id' not in _udata or 'sega_pwd' not in _udata:
        return {
            "success": False,
            "error": "Account not bound",
            "message": f"User {user_id} has not bound a SEGA account",
            "status_code": 400,
            "user_id": user_id,
            "version": ver,
            "func_status": func_status,
            "elapsed_time": time.time() - start_time,
        }

    sega_id = _udata.get('sega_id')
    sega_pwd = _udata.get('sega_pwd')
    aime = _udata.get('aime', 0)

    # 定义数据获取函数（在重试循环外定义一次）
    async def fetch_all_data(cookies):
        return await asyncio.gather(
            get_maimai_info(cookies, ver),
            get_maimai_records(cookies, ver),
            get_recent_records(cookies, ver),
        )

    user_info = maimai_records = recent_records = None

    cookies = await login_to_maimai(sega_id, sega_pwd, ver=ver, aime=aime)
    if cookies is None:
        logger.warning(f"[User] ⚠ Login failed: user_id={user_id}")
        return {
            "success": False,
            "error": "Authentication failed",
            "message": "Invalid SEGA ID or password.",
            "status_code": 401,
            "user_id": user_id,
            "version": ver,
            "func_status": func_status,
            "elapsed_time": time.time() - start_time,
        }
    if cookies == "MAINTENANCE":
        return {
            "success": False,
            "error": "Maintenance",
            "message": "The official website is under maintenance. Please try again later.",
            "status_code": 503,
            "user_id": user_id,
            "version": ver,
            "func_status": func_status,
            "elapsed_time": time.time() - start_time,
        }

    # 使用异步函数并发获取所有数据
    user_info, maimai_records, recent_records = await fetch_all_data(cookies)

    if (user_info == "MAINTENANCE" or
        maimai_records == "MAINTENANCE" or
        recent_records == "MAINTENANCE"):
        return {
            "success": False,
            "error": "Maintenance",
            "message": "The official website is under maintenance. Please try again later.",
            "status_code": 503,
            "user_id": user_id,
            "version": ver,
            "func_status": func_status,
            "elapsed_time": time.time() - start_time,
        }

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
    result = await _sync_maimai_user_data(user_id, ver)

    if result.get("error") == "Account not bound" or result.get("error") == "Authentication failed":
        return segaid_error(user_id)
    if result.get("error") == "Maintenance":
        return maintenance_error(user_id)

    extra_messages = []

    if result.get("func_status", {}).get("Best Records"):
        b50_message = await generate_records(user_id, user_id, ver=ver)
        if isinstance(b50_message, ImageMessage):
            extra_messages.append(b50_message)
        elif b50_message is not None:
            extra_messages.append(b50_message)

    messages = [
        generate_update_result_flex(
            user_id=user_id,
            username=result.get("username", "N/A"),
            rating=result.get("rating", "N/A"),
            update_time=result.get("last_update") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            elapsed_time=result.get("elapsed_time", 0),
            func_status=result.get("func_status", {}),
            success=bool(result.get("success")),
        )
    ]

    messages.extend(extra_messages)

    return messages

def handle_export_command(user_id: str, fmt: str):
    try:
        meta = export_records(user_id, fmt)
    except Exception as e:
        logger.error(f"[Export] ✗ Handler error: user_id={user_id}, fmt={fmt}, error={e}", exc_info=True)
        return TextMessage(text=get_multilingual_text(language_catalog("messages.export_failed_text"), user_id))

    status = meta.get("status")
    if status == "empty":
        return TextMessage(text=get_multilingual_text(language_catalog("messages.export_empty_text"), user_id))
    if status != "ok":
        return TextMessage(text=get_multilingual_text(language_catalog("messages.export_failed_text"), user_id))

    logger.info(f"[Export] ✓ Export delivered: user_id={user_id}, fmt={fmt}, "
                f"size={meta['size']}, best={meta['best_count']}, recent={meta['recent_count']}")
    return generate_export_flex(user_id, meta)


def handle_rc_command(msg: str, user_id: str):
    # 提取数字
    level_str = re.sub(r"^rc\b[ 　]*", "", msg, flags=re.IGNORECASE).strip()

    # 尝试转换为浮点数
    try:
        level = float(level_str)
    except ValueError:
        language = get_user_language(user_id)
        error_texts = language_catalog("main.invalid_constant")
        return TextMessage(text=select_text(error_texts, language=language, default_language=DEFAULT_WEB_LANGUAGE))

    # 验证范围：1.0 到 15.0
    if level < 1.0 or level > 15.0:
        language = get_user_language(user_id)
        error_texts = format_catalog("main.constant_out_of_range", level=level)
        return TextMessage(text=select_text(error_texts, language=language, default_language=DEFAULT_WEB_LANGUAGE))

    # 验证小数位数：最多一位
    if round(level, 1) != level:
        language = get_user_language(user_id)
        error_texts = format_catalog("main.constant_precision", level=level)
        return TextMessage(text=select_text(error_texts, language=language, default_language=DEFAULT_WEB_LANGUAGE))

    return get_rc(level, user_id)


def get_rc(level: float, user_id=None):
    rc_data = []
    last_ra = 0

    for i in range(970000, 1005001):
        score = i / 10000
        ra = get_single_ra(level, score)
        if ra != last_ra:
            rc_data.append((score, ra))
            last_ra = ra

    return generate_rc_flex(level, rc_data, user_id)

async def random_song(user_id, key="", ver="jp"):
    songs, _ = read_dxdata(ver)
    valid_songs = []

    if key:
        level_values = parse_level_value(key)
        if not level_values:
            return song_error(user_id)

    for song in songs:
        for sheet in song['sheets']:
            if sheet['regions'][ver]:
                if not key or sheet['internalLevelValue'] in level_values:
                    valid_songs.append(song)
                    break

    if not valid_songs:
        return song_error(user_id)

    song = random.choice(valid_songs)
    song_id = song.get('id')

    user_tz = get_user_timezone(user_id)
    song_img = song_info_generate(
        song,
        timezone_offset=user_tz,
        ver=ver,
        bg_filter=_get_user_bg_filter(user_id),
    )
    img_w, img_h = song_img.size
    original_url, preview_url = await upload_generated_image(song_img, user_id)
    return generate_song_info_flex(song_id, original_url, img_w, img_h, user_id, mode='info')

async def search_song(user_id, acronym, ver="jp"):
    songs, _ = read_dxdata(ver)

    # 使用优化的歌曲匹配函数
    matching_songs = find_matching_songs(acronym, songs, max_results=MAX_SEARCH_RESULTS, )

    # 没有匹配结果
    if not matching_songs:
        return song_error(user_id)

    # 返回搜索结果列表
    if len(matching_songs) > 1:
        return generate_search_results_flex(user_id, matching_songs, 'song')
    
    # 单个结果，调用 search_song_by_id
    song = matching_songs[0]
    song_id = song.get('id')
    return await search_song_by_id(user_id, song_id, ver)


async def search_song_by_id(user_id, song_id, ver="jp"):
    songs, _ = read_dxdata(ver)

    matching_song = None
    for song in songs:
        if song.get('id') == song_id:
            matching_song = song
            break

    # 没有匹配结果
    if not matching_song:
        return song_error(user_id)

    user_tz = get_user_timezone(user_id)
    song_img = song_info_generate(
        matching_song,
        timezone_offset=user_tz,
        ver=ver,
        bg_filter=_get_user_bg_filter(user_id),
    )
    img_w, img_h = song_img.size
    original_url, preview_url = await upload_generated_image(song_img, user_id)
    return generate_song_info_flex(song_id, original_url, img_w, img_h, user_id, mode='info')

def get_ranking(user_id, id_use, ver=None):
    user_ver = ver or (get_user(id_use) or {}).get('version', 'jp')

    # 收集同版本且有 rating 的用户
    ranked_users = []
    for uid, data in load_all_users().items():
        if data.get('version', 'jp') != user_ver:
            continue
        if data.get("participate_global_ranking", True) is False:
            continue
        info = data.get('personal_info')
        if info and info.get('rating') and info['rating'] != 'ERROR':
            try:
                rating_val = int(info['rating'])
            except (ValueError, TypeError):
                continue
            ranked_users.append({
                "user_id": uid,
                "name": info.get('name', 'N/A'),
                "rating_int": rating_val,
                "rating": info['rating']
            })

    if not ranked_users:
        return TextMessage(text=get_multilingual_text(language_catalog("messages.ranking_no_data_text"), user_id))

    # 按 rating 降序排序
    ranked_users.sort(key=lambda x: x["rating_int"], reverse=True)

    # 分配排名（相同 rating 同排名）
    for i, u in enumerate(ranked_users):
        if i == 0:
            u["rank"] = 1
        elif u["rating_int"] == ranked_users[i - 1]["rating_int"]:
            u["rank"] = ranked_users[i - 1]["rank"]
        else:
            u["rank"] = i + 1

    # 指定版本时直接显示前15名，不做个人区域
    if ver is not None:
        top15 = []
        for u in ranked_users[:15]:
            top15.append({"rank": u["rank"], "name": u["name"], "rating": u["rating"]})
        return generate_ranking_flex(
            user_id, top15, nearby_entries=None, ver=user_ver,
        )

    # 找到当前用户在排名列表中的索引
    user_idx = None
    for i, u in enumerate(ranked_users):
        if u["user_id"] == id_use:
            user_idx = i
            break

    # 前5名
    top5 = []
    for u in ranked_users[:5]:
        entry = {"rank": u["rank"], "name": u["name"], "rating": u["rating"]}
        if u["user_id"] == id_use:
            entry["is_user"] = True
        top5.append(entry)

    # 用户在前5名内，不需要附近区域
    user_in_top5 = user_idx is not None and user_idx < 5

    # 用户不在前5时，构建以用户为中心的附近名单（前后各3名）
    nearby_entries = None
    if not user_in_top5 and user_idx is not None:
        # 避免与前5名重叠，附近区域从索引5开始
        nearby_start = max(5, user_idx - 3)
        nearby_end = min(len(ranked_users), user_idx + 4)
        nearby_entries = []
        for u in ranked_users[nearby_start:nearby_end]:
            entry = {"rank": u["rank"], "name": u["name"], "rating": u["rating"]}
            if u["user_id"] == id_use:
                entry["is_user"] = True
            nearby_entries.append(entry)

    return generate_ranking_flex(
        user_id, top5, nearby_entries=nearby_entries, ver=user_ver,
    )


def search_by_artist(user_id, artist_query, ver="jp", page=1, source_type="user"):
    if source_type != 'user':
        return generate_status_flex(
            language_catalog("main.private_chat_title"),
            language_catalog("messages.search_group_warning_text"),
            user_id,
            tone="warning",
        )

    songs, _ = read_dxdata(ver)

    matching_songs = []
    query_lower = artist_query.lower()
    for song in songs:
        artist = song.get('artist') or ''
        if query_lower in artist.lower():
            matching_songs.append(song)

    if not matching_songs:
        return song_error(user_id)

    title = f"Artist: {artist_query}"
    return generate_song_list_flex(user_id, title, matching_songs, page, "artist", artist_query)

def search_by_designer(user_id, designer_query, ver="jp", page=1, source_type="user"):
    if source_type != 'user':
        return generate_status_flex(
            language_catalog("main.private_chat_title"),
            language_catalog("messages.search_group_warning_text"),
            user_id,
            tone="warning",
        )

    songs, _ = read_dxdata(ver)

    matching_songs = []
    matched_sheets_map = {}
    query_lower = designer_query.lower()

    for song in songs:
        matched_sheets = []
        for sheet in song.get('sheets', []):
            designer = sheet.get('noteDesigner', '')
            if designer and query_lower in designer.lower():
                matched_sheets.append(sheet)
        if matched_sheets:
            matching_songs.append(song)
            matched_sheets_map[song.get('id', '')] = matched_sheets

    if not matching_songs:
        return song_error(user_id)

    title = f"Designer: {designer_query}"
    return generate_song_list_flex(user_id, title, matching_songs, page, "designer", designer_query, matched_sheets_map)

def search_by_bpm(user_id, bpm_min, bpm_max=None, ver="jp", page=1, source_type="user"):
    if source_type != 'user':
        return generate_status_flex(
            language_catalog("main.private_chat_title"),
            language_catalog("messages.search_group_warning_text"),
            user_id,
            tone="warning",
        )

    songs, _ = read_dxdata(ver)
    exact_match = bpm_max is None
    bpm_max = bpm_min if bpm_max is None else bpm_max
    if bpm_min > bpm_max:
        bpm_min, bpm_max = bpm_max, bpm_min

    matching_songs = []
    for song in songs:
        song_bpm = parse_bpm_number(song.get('bpm'))
        if song_bpm is None:
            continue
        if bpm_min <= song_bpm <= bpm_max:
            matching_songs.append(song)

    if not matching_songs:
        return song_error(user_id)

    matching_songs.sort(key=lambda song: (
        parse_bpm_number(song.get('bpm')) or 0,
        song.get('title') or '',
        song.get('type') or ''
    ))

    if exact_match:
        query = format_bpm_number(bpm_min)
        title = f"BPM: {query}"
    else:
        query = f"{format_bpm_number(bpm_min)}-{format_bpm_number(bpm_max)}"
        title = f"BPM: {query}"

    return generate_song_list_flex(user_id, title, matching_songs, page, "bpm", query)

def calc_by_id(user_id, song_id, ver="jp"):
    songs, _ = read_dxdata(ver)

    matching_song = None
    for song in songs:
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

    calc_carousel = generate_calc_carousel(calc_data, user_id)
    return calc_carousel

def get_user_info(user_id, source_type):
    if source_type != 'user':
        return generate_status_flex(
            language_catalog("main.private_chat_title"),
            language_catalog("messages.private_info_group_warning_text"),
            user_id,
            tone="warning",
        )

    return generate_user_info_flex(user_id)

def get_bot_status(user_id):
    # 运行时长
    uptime = datetime.now() - SERVICE_START_TIME
    days = uptime.days
    hours, remainder = divmod(uptime.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    uptime_str = f"{days}d {hours}h {minutes}m"

    # 用户版本（影响读哪份 dxdata）
    ver = get_user_field(user_id, 'version', 'jp') if user_id else 'jp'

    # 楽曲データ：曲数 + 文件 mtime
    try:
        songs, _ = read_dxdata(ver)
        song_count = len(songs)
    except Exception:
        song_count = 0
    try:
        dxdata_date = datetime.fromtimestamp(os.path.getmtime(DXDATA_FILE)).strftime('%Y-%m-%d')
    except Exception:
        dxdata_date = "N/A"

    # 今日任务数 = image_gen + sync_cmd（复用 business_stats 30s 缓存）
    bs = get_business_stats()
    tasks_today = bs.get('today_image_calls', 0) + bs.get('today_sync_cmd_calls', 0)

    return generate_bot_status_flex(
        uptime_str=uptime_str,
        image_queue_size=image_queue.qsize() + image_query_queue.qsize(),
        web_queue_size=webtask_queue.qsize(),
        tasks_today=tasks_today,
        song_count=song_count,
        dxdata_date=dxdata_date,
        user_id=user_id
    )

async def get_song_record(user_id, id_use, acronym, ver="jp"):
    _id_use_data = get_user(id_use)
    if not _id_use_data:
        return mention_error(user_id) if id_use != user_id else segaid_error(user_id)

    if "personal_info" not in _id_use_data:
        return mention_error(user_id) if id_use != user_id else info_error(user_id)
    
    song_record = read_record(id_use, ver=ver)

    if not len(song_record):
        return mention_record_error(user_id) if id_use != user_id else record_error(user_id)
        
    # 使用优化的歌曲匹配函数
    songs, _ = read_dxdata(ver)
    matching_songs = find_matching_songs(acronym, songs, max_results=MAX_SEARCH_RESULTS, )

    if not matching_songs:
        return song_error(user_id)

    # 过滤出有游玩记录的歌曲
    songs_with_records = []
    for song in matching_songs:
        has_record = False
        for rcd in song_record:
            if rcd['cover_name'] == song['cover_name'] and rcd['type'] == song['type']:
                has_record = True
                break
        if has_record:
            songs_with_records.append(song)

    # 没有找到任何有记录的歌曲
    if len(songs_with_records) == 0:
        return song_error(user_id)

    # 返回搜索结果列表
    if len(songs_with_records) > 1:
        return generate_search_results_flex(user_id, matching_songs, 'record', id_use)

    # 单个结果，调用 get_song_record_by_id
    song = songs_with_records[0]
    song_id = song.get('id')
    return await get_song_record_by_id(user_id, id_use, song_id, ver)

async def get_song_record_by_id(user_id, id_use, song_id, ver="jp"):
    _id_use_data = get_user(id_use)
    if not _id_use_data:
        return mention_error(user_id) if id_use != user_id else segaid_error(user_id)

    if "personal_info" not in _id_use_data:
        return mention_error(user_id) if id_use != user_id else info_error(user_id)

    song_record = read_record(id_use, ver=ver)

    if not len(song_record):
        return mention_record_error(user_id) if id_use != user_id else record_error(user_id)

    matching_song = None
    songs, _ = read_dxdata(ver)
    for song in songs:
        if song.get('id') == song_id:
            matching_song = song
            break

    # 没有匹配结果
    if not matching_song:
        return song_error(user_id)

    # 查找用户的游玩记录
    played_data = []
    for rcd in song_record:
        if rcd['cover_name'] == matching_song['cover_name'] and rcd['type'] == matching_song['type']:
            played_data.append(rcd)
            song_name = rcd['name']

    # 如果该歌曲没有游玩记录
    if not played_data:
        return song_error(user_id)

    # 尝试使用新函数获取更详细的成绩（包含游玩次数和最后游玩时间）
    try:
        _id_use_data = get_user(id_use) if user_id == id_use else None
        if _id_use_data and 'sega_id' in _id_use_data and 'sega_pwd' in _id_use_data:
            sega_id = _id_use_data['sega_id']
            sega_pwd = _id_use_data['sega_pwd']
            aime = _id_use_data.get('aime', 0)
            cookies = await login_to_maimai(sega_id, sega_pwd, ver=ver, aime=aime)
            if cookies is None:
                logger.warning(f"[Song Record] ⚠ Login failed: user_id={user_id}")

            if cookies:
                detailed_records = await get_single_record(song_name, matching_song['type'], cookies, ver=ver)

                if detailed_records and detailed_records != "MAINTENANCE":
                    # 用详细成绩更新 played_data
                    for rcd in played_data:
                        # 找到对应难度的详细成绩
                        for detail in detailed_records:
                            if detail['difficulty'] == rcd['difficulty']:
                                # 更新现有字段
                                rcd['score'] = detail['score']
                                rcd['dx_score'] = detail['dx_score']
                                rcd['score_icon'] = detail['score_icon']
                                rcd['combo_icon'] = detail['combo_icon']
                                rcd['sync_icon'] = detail['sync_icon']
                                # 添加新字段
                                rcd['play_count'] = detail['play_count']
                                rcd['last_play_time'] = detail['last_play_time']
                                rcd = get_detailed_info([rcd], ver)[0]
                                break
    except Exception as e:
        # 如果获取详细成绩失败，继续使用原成绩
        logger.exception(f"[Song Record] Failed to get detailed record for {matching_song.get('title', 'unknown')}: {e}")

    # 生成歌曲信息图片
    user_tz = get_user_timezone(user_id)
    song_img = song_info_generate(
        matching_song,
        played_data,
        timezone_offset=user_tz,
        ver=ver,
        bg_filter=_get_user_bg_filter(user_id),
    )
    img_w, img_h = song_img.size
    original_url, preview_url = await upload_generated_image(song_img, user_id)
    return generate_song_info_flex(song_id, original_url, img_w, img_h, user_id, mode='record')

async def generate_plate_rcd(user_id, id_use, title, ver="jp", filter_mode=None):
    _id_use_data = get_user(id_use)
    if not _id_use_data:
        return mention_error(user_id) if id_use != user_id else segaid_error(user_id)

    if "personal_info" not in _id_use_data:
        return mention_error(user_id) if id_use != user_id else info_error(user_id)

    if not (len(title) == 2 or len(title) == 3):
        return plate_error(user_id)

    song_record = read_record(id_use, ver=ver)

    if not len(song_record):
        return mention_record_error(user_id) if id_use != user_id else record_error(user_id)

    title = title.replace("晓", "暁").replace("极", "極")

    version_name = title[0]
    plate_type = title[1:]

    songs, versions = read_dxdata(ver)

    target_version = []
    target_icon = []
    target_type = ""

    if version_name in TEMP_VERSION["abbr"]:
        target_version.append(TEMP_VERSION["title"])

    for version in versions:
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

    for song in songs:
        if song['version'] not in target_version or song['type'] == 'utage':
            continue

        for sheet in song['sheets']:
            if not sheet['regions'][ver] or sheet["difficulty"] not in target_num:
                continue

            icon = "back"
            achieved = False
            achievement_rate = 0.0
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
                # 获取达成率
                score_str = rcd.get('score', '0.0000%')
                achievement_rate = float(score_str[:-1]) if score_str.endswith('%') else 0.0
                if icon in target_icon:
                    target_num[difficulty]['clear'] += 1
                    achieved = True
            else:
                # 尝试标准化匹配
                normalized_title = normalize_text(song_title)
                key2 = (normalized_title, difficulty, song_type)
                if key2 in rcd_map:
                    rcd = rcd_map[key2]
                    icon = rcd[f'{target_type}_icon']
                    # 获取达成率
                    score_str = rcd.get('score', '0.0000%')
                    achievement_rate = float(score_str[:-1]) if score_str.endswith('%') else 0.0
                    if icon in target_icon:
                        target_num[difficulty]['clear'] += 1
                        achieved = True

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
                    "img": generate_cover(song['cover_url'], song_type, icon, target_type, cover_name=song.get('cover_name'), complete_info=complete_info, achieved=achieved),
                    "level": sheet['level'],
                    "achieved": achieved,
                    "achievement_rate": achievement_rate
                })

    # 按 filter_mode 过滤数据
    if filter_mode == "uncleared":
        target_data = [d for d in target_data if not d["achieved"]]
    elif filter_mode == "unplayed":
        target_data = [d for d in target_data if d["achievement_rate"] == 0.0 and not d["achieved"]]
    elif filter_mode == "cleared":
        target_data = [d for d in target_data if d["achieved"]]

    if not target_data:
        return mention_no_matching_data(user_id) if id_use != user_id else no_matching_data(user_id)

    plate_img = generate_plate_image(target_data, title, headers = target_num)

    # 清理 target_data 中的封面图片对象
    for entry in target_data:
        entry.pop("img").close()

    # 获取用户信息并创建用户信息图片
    user_info = _id_use_data.get('personal_info')
    profile_img = generate_profile(user_info, user_id=id_use)
    img = _compose_user_images([profile_img, plate_img], user_id)

    original_url, preview_url = await upload_generated_image(img, user_id)

    # 检查上传是否成功
    if not original_url or not preview_url:
        logger.error(f"[Image] ✗ Upload failed")
        return system_error(user_id)

    message = ImageMessage(original_content_url=original_url, preview_image_url=preview_url)

    return message


async def generate_level_rank_progress(user_id, id_use, level, rank=None, ver="jp", filter_mode=None):

    _id_use_data = get_user(id_use)
    if not _id_use_data:
        return mention_error(user_id) if id_use != user_id else segaid_error(user_id)

    if "personal_info" not in _id_use_data:
        return mention_error(user_id) if id_use != user_id else info_error(user_id)

    supported_levels = ["11", "11+", "12", "12+", "13", "13+", "14", "14+", "15"]
    songs, _ = read_dxdata(ver)
    target_category = None
    is_level_target = level in supported_levels
    if not is_level_target:
        target_category = _resolve_progress_category(level)
        if not target_category:
            return level_not_supported(user_id)

    # 评级映射：用户输入 -> 内部标识
    rank_mapping = {
        "s": ("score", ["s", "sp", "ss", "ssp", "sss", "sssp"]),
        "s+": ("score", ["sp", "ss", "ssp", "sss", "sssp"]),
        "ss": ("score", ["ss", "ssp", "sss", "sssp"]),
        "ss+": ("score", ["ssp", "sss", "sssp"]),
        "sss": ("score", ["sss", "sssp"]),
        "sss+": ("score", ["sssp"]),
        "fc": ("combo", ["fc", "fcp", "ap", "app"]),
        "fc+": ("combo", ["fcp", "ap", "app"]),
        "ap": ("combo", ["ap", "app"]),
        "ap+": ("combo", ["app"]),
        "fdx": ("sync", ["fdx", "fdxp"]),
        "fdx+": ("sync", ["fdxp"])
    }

    if rank is not None and rank not in rank_mapping:
        return song_error(user_id)

    target_type, target_icons = rank_mapping[rank] if rank else (None, None)
    song_record = read_record(id_use, ver=ver)

    if not len(song_record):
        return mention_record_error(user_id) if id_use != user_id else record_error(user_id)

    region_key = ver

    # 构建用户记录的哈希表
    rcd_map = {}
    for rcd in song_record:
        name = rcd['name']
        difficulty = rcd['difficulty']
        type = rcd['type']

        # 精确匹配
        key1 = (name, difficulty, type)
        rcd_map[key1] = rcd

    # 收集数据并统计
    target_data = []
    total_charts = 0  # 总谱面数
    achieved_count = 0  # 已达成
    unachieved_count = 0  # 未达成（有记录但未达标）
    unplayed_count = 0  # 未游玩
    
    for song in songs:
        if song['type'] == 'utage':
            continue
        if target_category and song.get("category") != target_category:
            continue

        for sheet in song['sheets']:
            if not sheet['regions'].get(region_key, False):
                continue

            if is_level_target:
                # 14+ 包含 14+ 和 15 级别
                if level == "14+":
                    if sheet['level'] not in ["14+", "15"]:
                        continue
                else:
                    if sheet['level'] != level:
                        continue

            difficulty = sheet['difficulty']
            total_charts += 1

            # 查找用户记录
            song_title = song['title']
            song_type = song['type']
            icon = "back"
            achieved = False
            has_record = False
            achievement_rate = 0.0  # 达成率

            # 尝试精确匹配
            key1 = (song_title, difficulty, song_type)
            if key1 in rcd_map:
                rcd = rcd_map[key1]
                has_record = True
                # 获取达成率
                score_str = rcd.get('score', '0.0000%')
                achievement_rate = float(score_str[:-1]) if score_str.endswith('%') else 0.0

                if rank is not None:
                    # 如果指定了评级，检查是否达成
                    user_icon = rcd.get(f'{target_type}_icon', "back")
                    icon = user_icon  # 始终显示用户实际达到的评级
                    if user_icon in target_icons:
                        achieved = True
                        achieved_count += 1
                    else:
                        unachieved_count += 1
                else:
                    # 如果没有指定评级，所有有记录的都算已达成
                    achieved = True
                    achieved_count += 1
            else:
                # 尝试标准化匹配
                normalized_title = normalize_text(song_title)
                key2 = (normalized_title, difficulty, song_type)
                if key2 in rcd_map:
                    rcd = rcd_map[key2]
                    has_record = True
                    # 获取达成率
                    score_str = rcd.get('score', '0.0000%')
                    achievement_rate = float(score_str[:-1]) if score_str.endswith('%') else 0.0

                    if rank is not None:
                        # 如果指定了评级，检查是否达成
                        user_icon = rcd.get(f'{target_type}_icon', "back")
                        icon = user_icon  # 始终显示用户实际达到的评级
                        if user_icon in target_icons:
                            achieved = True
                            achieved_count += 1
                        else:
                            unachieved_count += 1
                    else:
                        # 如果没有指定评级，所有有记录的都算已达成
                        achieved = True
                        achieved_count += 1

            # 如果没有记录，算作未游玩
            if not has_record:
                unplayed_count += 1

            # 生成所有难度的封面
            target_data.append({
                "img": generate_cover(song['cover_url'], song_type, icon if rank else None, target_type if rank else None, cover_name=song.get('cover_name'), difficulty=difficulty, achieved=achieved if rank else None, song_title=song_title),
                "level": sheet["level"],
                "internal_level": sheet['internalLevelValue'],
                "achieved": achieved,
                "difficulty": difficulty,
                "achievement_rate": achievement_rate
            })

    if not target_data:
        return mention_no_matching_data(user_id) if id_use != user_id else no_matching_data(user_id)

    # 按 filter_mode 过滤数据
    if filter_mode == "uncleared":
        target_data = [d for d in target_data if not d["achieved"]]
    elif filter_mode == "unplayed":
        target_data = [d for d in target_data if d["achievement_rate"] == 0.0 and not d["achieved"]]
    elif filter_mode == "cleared":
        target_data = [d for d in target_data if d["achieved"]]

    if not target_data:
        return mention_no_matching_data(user_id) if id_use != user_id else no_matching_data(user_id)

    # 生成标题
    level_display = level.replace("+", "⁺") if is_level_target else target_category
    rank_display = rank.upper().replace("+", "⁺") if rank else ""

    # 总体统计数据
    stats = {
        "achieved": achieved_count,
        "unachieved": unachieved_count,
        "unplayed": unplayed_count,
        "total": total_charts
    }

    # 生成图片（定数列表+统计卡片）
    record_img = generate_level_rank_progress_image(
        target_data,
        level_display,
        rank_display,
        stats,
        group_by="internal_level" if is_level_target else "level",
        show_progress_suffix=is_level_target,
        ver=ver,
    )

    # 清理 target_data 中的封面图片对象
    for entry in target_data:
        entry.pop("img").close()

    # 获取用户信息并创建用户信息图片
    user_info = _id_use_data.get('personal_info')
    profile_img = generate_profile(user_info, scale=1.5, user_id=id_use)
    img = _compose_user_images([profile_img, record_img], user_id)

    original_url, preview_url = await upload_generated_image(img, user_id)
    message = ImageMessage(original_content_url=original_url, preview_image_url=preview_url)

    return message


def generate_profile(user_info, scale=1, user_id=None):

    img_width = 1363
    img_height = 218
    info_img = Image.new("RGBA", (img_width, img_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(info_img)

    def paste_image(key, position, size, round=False, use_alpha=True):
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

                with requests.get(url, headers=headers, verify=False) as response:
                    response.raise_for_status()
                    with Image.open(BytesIO(response.content)) as source_img:
                        img = source_img.copy()
                if use_alpha and img.mode != "RGBA":
                    img = img.convert("RGBA")
                elif not use_alpha and img.mode != "RGB":
                    img = img.convert("RGB")
                img_resized = img.resize(size, Image.LANCZOS)
                if round:
                    img_resized = round_corner(img_resized, radius=10)
                if use_alpha:
                    info_img.paste(img_resized, position, img_resized)
                else:
                    info_img.paste(img_resized, position)
                return True

            except Exception as e:
                logger.error(f"[Image] ✗ Failed to load image: url={user_info[key]}, error={e}")
                return None
        return None

    paste_image("nameplate_url", (0, 0), (1363, 218), use_alpha=False)

    # icon_url 为默认值时，尝试使用 LINE 头像
    default_icon = [
        "https://maimaidx.jp/maimai-mobile/img/Icon/",
        "https://maimaidx.jp/maimai-mobile/img/Icon/c22d52b387e3f829.png",
        "https://maimaidx-eng.com/maimai-mobile/img/Icon/",
        "https://maimaidx-eng.com/maimai-mobile/img/Icon/c22d52b387e3f829.png"
    ]
    icon_url = user_info.get("icon_url", "")
    round = False
    if icon_url in default_icon and user_id:
        try:
            with ApiClient(configuration) as api_client:
                profile = MessagingApi(api_client).get_profile(user_id)
                if profile.picture_url:
                    user_info = {**user_info, "icon_url": profile.picture_url}
                    round = True
        except Exception as e:
            logger.error(f"[Image] ✗ Failed to load user profile image: {e}")

    paste_image("icon_url", (26, 24), (170, 170), round)

    # rating block: 优先使用本地图片，兼容旧版 URL
    if "rating_block_path" in user_info and user_info["rating_block_path"]:
        try:
            with Image.open(user_info["rating_block_path"]) as _rb:
                rb_img = _rb.convert("RGBA")
            rb_img = rb_img.resize((296, 58), Image.LANCZOS)
            info_img.paste(rb_img, (219, 24), rb_img)
        except Exception as e:
            logger.error(f"[Image] ✗ Failed to load rating block: {e}")
    else:
        paste_image("rating_block_url", (219, 24), (223, 58))

    # 使用等宽方式绘制 rating 数字
    rating_text = user_info['rating'].rjust(5)
    char_width = 23  # 每个字符的固定宽度
    start_x = 359
    for i, char in enumerate(rating_text):
        # 计算字符的实际宽度
        char_bbox = draw.textbbox((0, 0), char, font=font_profile)
        actual_char_width = char_bbox[2] - char_bbox[0]
        # 在固定宽度区域内居中
        offset = (char_width - actual_char_width) / 2
        draw.text((start_x + i * char_width + offset, 28), char, fill=(255, 255, 255), font=font_profile)

    # 绘制昵称
    draw.rounded_rectangle([219, 89, 671, 145], radius=10, fill=(255, 255, 255), outline=(180, 180, 180), width=2)
    draw.text((235, 94), user_info['name'], fill=(0, 0, 0), font=font_profile)

    paste_image("class_rank_url", (530, 6), (148, 85))
    paste_image("cource_rank_url", (550, 93), (117, 48))
    paste_image("trophy_url", (219, 158), (452, 36))

    trophy_content = truncate_text(draw, user_info['trophy_content'], font_trophy, 430)
    bbox = draw.textbbox((0, 0), trophy_content, font=font_trophy)
    text_width = bbox[2] - bbox[0]
    rect_width = 452
    center_x = 219 + (rect_width - text_width) // 2
    draw.text((center_x, 157), trophy_content, fill=(255, 255, 255), font=font_trophy, stroke_width=2, stroke_fill=(0, 0, 0))

    info_img = info_img.resize((int(img_width * scale), int(img_height * scale)), Image.Resampling.LANCZOS)
    return info_img

def _record_level_value(record):
    try:
        return float(record.get("internalLevelValue", 0) or 0)
    except (TypeError, ValueError):
        return 0.0


def _parse_level_filter_values(raw_level):
    values = parse_level_value(str(raw_level).strip())
    if not values:
        return []
    return [float(v) for v in values]


def _filter_records_by_level(song_record, parts):
    if not parts:
        return song_record, None

    if len(parts) == 1:
        level_values = _parse_level_filter_values(parts[0])
        if not level_values:
            return song_record, None
        value_set = {round(v, 1) for v in level_values}
        filtered = [
            x for x in song_record
            if round(_record_level_value(x), 1) in value_set
        ]
        return filtered, str(parts[0])

    start_values = _parse_level_filter_values(parts[0])
    stop_values = _parse_level_filter_values(parts[1])
    if not start_values or not stop_values:
        return song_record, None

    lv_start = min(start_values)
    lv_stop = max(stop_values)
    if lv_start > lv_stop:
        lv_start, lv_stop = lv_stop, lv_start

    filtered = [
        x for x in song_record
        if lv_start <= _record_level_value(x) <= lv_stop
    ]
    return filtered, f'{parts[0]} ~ {parts[1]}'


def select_records(song_record, type="best50", command="", ver="jp"):
    page = 1
    times = 1
    sort_rule = lambda x: (x["ra"], float(x["score"][:-1]))
    filter_rules = [
        (lambda x: x['new_song'] == False),
        (lambda x: x['new_song'] == True)
    ]
    details = {}
    if not command == "":
        cmds = re.findall(r"-(\w+)(?:\s+([^-]+))?", command)
        for cmd, cmd_num in cmds:
            if cmd in ["diff", "difficulty"]:
                diff_map = {
                    'bas': 'basic',
                    'adv': 'advanced',
                    'exp': 'expert',
                    'mas': 'master',
                    'rem': 'remaster'
                }
                raw_diffs = cmd_num.split()
                difficulties = []
                for d in raw_diffs:
                    d_lower = d.strip().lower()
                    if d_lower:
                        if d_lower in diff_map:
                            difficulties.append(diff_map[d_lower])
                        elif d_lower in ['basic', 'advanced', 'expert', 'master', 'remaster']:
                            difficulties.append(d_lower)
                if difficulties:
                    song_record = list(filter(lambda x: x.get('difficulty', '').lower() in difficulties, song_record))
                    details['Diff'] = ' '.join(d for d in difficulties)
            elif cmd in ["lv", "level"]:
                parts = cmd_num.split()
                filtered_records, detail = _filter_records_by_level(song_record, parts)
                song_record = filtered_records
                if detail:
                    details['Lv'] = detail
            elif cmd in ["next", "nxt"]:
                filter_rules = [
                    (lambda x: x['version'] != MAIMAI_VERSION[ver][-1]),
                    (lambda x: x['version'] == MAIMAI_VERSION[ver][-1])
                ]
                details['NextVer'] = 'ON'
            elif cmd in ["ra", "rating"]:
                parts = cmd_num.split()
                if len(parts) == 1:
                    ra = int(parts[0])
                    song_record = list(filter(lambda x: x['ra'] == ra, song_record))
                    details['RA'] = f'{ra}'
                else:
                    ra_start, ra_stop = map(int, parts[:2])
                    song_record = list(filter(lambda x: ra_start <= x['ra'] <= ra_stop, song_record))
                    details['RA'] = f'{ra_start} ~ {ra_stop}'
            elif cmd in ["dx", "dxscore"]:
                parts = cmd_num.split()
                if not len(parts):
                    sort_rule = lambda x: (x["dx_percentage"], float(x["score"][:-1]))
                    details['Sort'] = 'DX Score'
                elif len(parts) == 1:
                    dx_percentage = int(re.sub(r"\D", "", parts[0]))
                    song_record = list(filter(lambda x: x['dx_percentage'] * 100 >= dx_percentage, song_record))
                    details['DxScr'] = f'≧ {dx_percentage}%'
                else:
                    dx_start = int(re.sub(r"\D", "", parts[0]))
                    dx_stop = int(re.sub(r"\D", "", parts[1]))
                    song_record = list(filter(lambda x: dx_start <= x['dx_percentage'] * 100 <= dx_stop, song_record))
                    details['DxScr'] = f'{dx_start}% ~ {dx_stop}%'
            elif cmd in ["dxstar", "star"]:
                parts = cmd_num.split()
                if len(parts) == 1:
                    dx_star = int(re.sub(r"\D", "", parts[0]))
                    song_record = list(filter(lambda x: x['dx_star'] == dx_star, song_record))
                    details['Star'] = f'{dx_star}'
                else:
                    dx_start = int(re.sub(r"\D", "", parts[0]))
                    dx_stop = int(re.sub(r"\D", "", parts[1]))
                    song_record = list(filter(lambda x: dx_start <= x['dx_star'] <= dx_stop, song_record))
                    details['Star'] = f'{dx_start} ~ {dx_stop}'
            elif cmd in ["score", "scr"]:
                parts = cmd_num.split()
                if len(parts) == 1:
                    score = float(re.sub(r"[^0-9.]", "", parts[0]))
                    song_record = list(filter(lambda x: float(x['score'].replace("%", "")) >= score, song_record))
                    details['Scr'] = f'≧ {score:.4f}%'
                else:
                    scr_start = float(re.sub(r"[^0-9.]", "", parts[0]))
                    scr_stop = float(re.sub(r"[^0-9.]", "", parts[1]))
                    song_record = list(filter(lambda x: scr_start <= float(x['score'].replace("%", "")) <= scr_stop, song_record))
                    details['Scr'] = f'{scr_start}% ~ {scr_stop}%'
            elif cmd in ["ver", "version"]:
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
                details['Ver'] = ""
                for version in versions:
                    plus = False
                    if "plus" in version:
                        plus = True
                    details['Ver'] += version.lower().replace("maimaiでらっくす", "dx").replace("plus", "")[:3].strip()
                    if plus:
                        details['Ver'] += "+"
                    details['Ver'] += " "
            elif cmd in ["type", "tp"]:
                # 处理谱面类型筛选：-type dx / -type std
                raw_types = [t.strip().lower() for t in cmd_num.split() if t.strip()]
                valid_types = []
                for t in raw_types:
                    if t in ('dx', 'std'):
                        valid_types.append(t)
                if valid_types:
                    song_record = list(filter(lambda x: x.get('type', '').lower() in valid_types, song_record))
                    details['Type'] = ' / '.join(t.upper() for t in valid_types)
            elif cmd in ["page", "pg"]:
                try:
                    page = max(1, int(cmd_num.strip()))
                    if page > 1:
                        details['Page'] = str(page)
                except ValueError:
                    pass
            elif cmd in ["times", "tm"]:
                parts = cmd_num.split()
                times = min(float(parts[0]), 2.5)
                if times > 0:
                    details['Times'] = times
                else:
                    times = 1

    up_songs = down_songs = []

    up_songs_data = list(filter(filter_rules[0], song_record))
    down_songs_data = list(filter(filter_rules[1], song_record))

    num_50 = math.ceil(50 * times / 5) * 5
    num_35 = math.ceil(35 * times / 5) * 5
    num_25 = math.ceil(25 * times / 5) * 5
    num_15 = math.ceil(15 * times / 5) * 5

    if type == "idlb50":
        for rcd in up_songs_data + down_songs_data:
            ideal_score, score_icon = get_ideal_score(float(rcd['score'][:-1]))
            rcd['score'] = f"{ideal_score:.4f}%"
            if score_icon:
                rcd['score_icon'] = score_icon
            if ideal_score == 101:
                rcd['combo_icon'] = "app"
            rcd['ra'] = get_single_ra(rcd['internalLevelValue'], ideal_score, ideal_score == 101)

    selection_type = "best50" if type == "idlb50" else type
    selection_rules = {
        "best50": (("up", num_35, None, None), ("down", num_15, None, None)),
        "best40": (("up", num_25, None, None), ("down", num_15, None, None)),
        "best35": (("up", num_35, None, None),),
        "best15": (("down", num_15, None, None),),
        "allb35": (("all", num_35, None, None),),
        "allb50": (("all", num_50, None, None),),
        "apb50": (("up", num_35, "combo_icon", {"ap", "app"}), ("down", num_15, "combo_icon", {"ap", "app"})),
        "fdxb50": (("up", num_35, "sync_icon", {"fdx", "fdxp"}), ("down", num_15, "sync_icon", {"fdx", "fdxp"})),
    }

    if selection_type in selection_rules:
        song_sources = {"up": up_songs_data, "down": down_songs_data, "all": song_record}
        selected_songs = {"up": [], "down": []}
        target_side = {"up": "up", "down": "down", "all": "up"}
        for source_key, count, field, allowed_values in selection_rules[selection_type]:
            source = song_sources[source_key]
            filtered_source = source if field is None else [x for x in source if x.get(field) in allowed_values]
            selected_songs[target_side[source_key]] = sorted(
                filtered_source,
                key=sort_rule,
                reverse=True,
            )[(page-1)*count : page*count]
        up_songs = selected_songs["up"]
        down_songs = selected_songs["down"]

    elif type == "unknown":
        up_songs = list(filter(lambda x: x['version'] == "UNKNOWN", song_record))

    elif type == "rct50":
        up_songs = song_record

    elif type == "sun50":
        sun_targets = (
            (100.4000, 100.4999, 100.5000),
            (99.9000, 99.9999, 100.0000),
        )
        sun_candidates = []
        for song in song_record:
            score = achievement_value(song.get("score"))
            target = next(
                (target for low, high, target in sun_targets if low <= score <= high),
                None,
            )
            if target is not None:
                sun_candidates.append((song, score, target))
        selected_sun_candidates = sorted(
            sun_candidates,
            key=lambda item: (
                round(item[2] - item[1], 4),
                -float(item[0].get("internalLevelValue", 0) or 0),
                str(item[0].get("name", "")),
                str(item[0].get("difficulty", "")),
                str(item[0].get("type", "")),
            ),
        )[(page-1)*num_50 : page*num_50]
        sun_groups = {target: [] for _, _, target in sun_targets}
        for song, _, target in selected_sun_candidates:
            sun_groups[target].append(song)
        up_songs = sun_groups[100.5000]
        down_songs = sun_groups[100.0000]

    else:
        return select_records(song_record, "best50", command, ver)

    return up_songs, down_songs, details

async def generate_records(user_id, id_use, type="best50", command="", ver="jp"):
    _id_use_data = get_user(id_use)
    if not _id_use_data:
        return mention_error(user_id) if id_use != user_id else segaid_error(user_id)

    if "personal_info" not in _id_use_data:
        return mention_error(user_id) if id_use != user_id else info_error(user_id)

    recent = (type == "rct50")
    recent_type = (type == "best40")
    song_record = read_record(id_use, recent, recent_type, ver=ver)
    if not len(song_record):
        return mention_record_error(user_id) if id_use != user_id else record_error(user_id)

    up_songs, down_songs, details = select_records(song_record, type, command, ver)
    if not up_songs and not down_songs:
        return song_error(user_id)

    if type == "unknown":
        type = "未だ知らず"

    record_img = generate_records_picture(
        up_songs,
        down_songs,
        type.upper(),
        ver,
        details,
    )

    # 获取用户信息并创建用户信息图片
    user_info = _id_use_data.get('personal_info')
    profile_img = generate_profile(user_info, user_id=id_use)
    img = _compose_user_images([profile_img, record_img], user_id)

    original_url, preview_url = await upload_generated_image(img, user_id)

    # 检查上传是否成功
    if not original_url or not preview_url:
        logger.error(f"[Image] ✗ Upload failed")
        return system_error(user_id)

    message = ImageMessage(original_content_url=original_url, preview_image_url=preview_url)

    return message

async def generate_friend_record(user_id, friend_code, type="best50", cmd="", ver="jp"):
    _udata = get_user(user_id)
    if not _udata or 'sega_id' not in _udata or 'sega_pwd' not in _udata:
        return segaid_error(user_id)

    sega_id = _udata['sega_id']
    sega_pwd = _udata['sega_pwd']

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

    error, friend_info, friend_records = await fetch_friend_data()

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

    recent_type = (type == "best40")
    friend_records = get_detailed_info(friend_records, ver, recent_type)

    up_songs, down_songs, details = select_records(friend_records, type, cmd, ver)

    if not (len(up_songs) + len(down_songs)):
        return song_error(user_id)

    user_info_img = generate_profile(friend_info)
    rcd_img = generate_records_picture(
        up_songs,
        down_songs,
        type.upper(),
        ver,
        details,
    )
    img = _compose_user_images([user_info_img, rcd_img], user_id)

    original_url, preview_url = await upload_generated_image(img, user_id)
    message = [
        TextMessage(text=get_multilingual_text(language_catalog("messages.friend_rcd_text"), user_id).format(name=friend_info["name"])),
        ImageMessage(original_content_url=original_url, preview_image_url=preview_url)
    ]

    return message

async def generate_level_records(user_id, id_use, level, ver="jp", page=1):
    _id_use_data = get_user(id_use)
    if not _id_use_data:
        return mention_error(user_id) if id_use != user_id else segaid_error(user_id)

    if "personal_info" not in _id_use_data:
        return mention_error(user_id) if id_use != user_id else info_error(user_id)

    song_record = read_record(id_use, ver=ver)

    if not len(song_record):
        return mention_record_error(user_id) if id_use != user_id else record_error(user_id)

    level_values = parse_level_value(level)
    if not level_values:
        return song_error(user_id)

    lv_min = min(level_values)
    lv_max = max(level_values)
    command = f"-lv {lv_min} {lv_max} -page {page}"

    up_level_list, down_level_list, _ = select_records(song_record, "best50", command, ver)

    if not up_level_list and not down_level_list:
        return level_record_not_found(level, page, user_id)

    title = f"Lv {level}"

    record_img = generate_records_picture(
        up_level_list,
        down_level_list,
        title.replace("+", "⁺"),
        ver,
    )

    # 获取用户信息并创建用户信息图片
    user_info = _id_use_data.get('personal_info')
    profile_img = generate_profile(user_info, user_id=id_use)
    img = _compose_user_images([profile_img, record_img], user_id)

    original_url, preview_url = await upload_generated_image(img, user_id)

    message = [
        ImageMessage(original_content_url=original_url, preview_image_url=preview_url),
        level_record_page_hint(page, user_id) if page == 1 else None
    ]
    message = [m for m in message if m]
    return message

async def generate_version_songs(user_id, version_title, ver="jp"):
    songs, versions = read_dxdata(ver)

    version_title = version_title.lower().replace("dx", "maimaiでらっくす").replace("deluxe", "maimaiでらっくす")
    target_version_info = next(
        (version for version in versions if version_title == version["version"].lower()),
        None,
    )
    target_versions = [target_version_info["version"]] if target_version_info else []
    if not target_versions:
        return version_error(user_id)

    songs_data = [
        song
        for song in songs
        if song["version"] in target_versions and song["type"] != "utage"
    ]
    version_list_img = generate_version_list(
        songs_data,
        version_info=target_version_info,
        ver=ver,
    )

    try:
        img = compose_generated_images(
            [version_list_img],
            timezone_offset=get_user_timezone(user_id),
            bg_filter=_get_user_bg_filter(user_id),
            outer_margin=0,
            image_y_offset=0,
        )
    finally:
        version_list_img.close()

    original_url, preview_url = await upload_generated_image(img, user_id)

    # 检查上传是否成功
    if not original_url or not preview_url:
        logger.error(f"[Image] ✗ Upload failed")
        return system_error(user_id)

    message = ImageMessage(original_content_url=original_url, preview_image_url=preview_url)

    return message

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
    except Exception:
        pass


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


def _download_line_message_content(message_id: str) -> bytes:
    with ApiClient(configuration) as api_client:
        content = MessagingApiBlob(api_client).get_message_content(message_id)
    return bytes(content)


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
            crop_img = build_score_crop_preview_image(image_bytes)
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
            result = recognize_score_image_bytes(
                image_bytes,
            )
            ver = get_user_field(user_id, "version", "jp") or "jp"
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
    command_match = re.fullmatch(r"(?P<command>rec|crop)(?:\s+(?P<suffix>-flex))?", command_text)
    if not command_match:
        return False
    command = command_match.group("command")
    force_flex = bool(command_match.group("suffix"))
    if force_flex and command != "rec":
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

    _enqueue_score_recognition_task(event, command, quoted_message_id, force_flex=force_flex)
    return True


def _bump_stats():
    with stats_lock:
        STATS['tasks_processed'] += 1


def _run_sync_handler(cmd, ctx, *, count_completion=True):
    if cmd.queue == QUEUE_SYNC:
        try:
            track_event('sync_cmd', user_id=ctx.user_id,
                        metadata={'command': cmd.name, 'source': 'line'})
        except Exception as exc:
            logger.debug("[EventTracker] sync_cmd tracking skipped: %s", exc)
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
    try:
        track_event('image_gen', user_id=ctx.user_id,
                    metadata={'command': cmd.name, 'source': 'line'})
    except Exception as exc:
        logger.debug("[EventTracker] image_gen tracking skipped: %s", exc)
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
                          (cmd.handler, (ctx.event,)))
        return True
    return False


# ---- sync/image 命令 handlers，签名 (ctx) -> Optional[Message] ----

def cmd_profile(ctx):
    return get_user_info(ctx.user_id, ctx.source_type)

def cmd_status(ctx):
    return get_bot_status(ctx.user_id)

def cmd_refresh_menu(ctx):
    try:
        link_rich_menu_for_state(ctx.user_id, get_user(ctx.user_id) or {})
    except Exception as e:
        logger.warning("[RichMenu] Silent refresh failed user_id=%s error=%s", ctx.user_id, e)
    return None

def cmd_unbind_prompt(ctx):
    warn = _check_private_or_warn(ctx, language_catalog("messages.unbind_group_warning_text"))
    if warn is not None:
        return warn
    user_data = get_user(ctx.user_id) or {}
    if not _can_open_settings(user_data):
        return generate_status_flex(
            language_catalog("main.not_linked_title"),
            language_catalog("messages.rebind_not_bound_text"),
            ctx.user_id,
            tone="warning",
        )
    url = f"https://{DOMAIN}/linebot/unbind?token={generate_unbind_token(ctx.user_id)}"
    return generate_account_action_flex("unbind", url, ctx.user_id)

def cmd_ranking(ctx):
    ver_arg = ctx.match.group(3) if ctx.match else None
    return get_ranking(
        ctx.user_id,
        ctx.id_use,
        ver_arg,
    )

def handle_postback_command(event, text):
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
        ver = get_user_field(user_id, 'version') or "jp"
        id_use = record_match.group(2) or user_id
        reply_msg = asyncio.run(get_song_record_by_id(user_id, id_use, record_match.group(1), ver))
        smart_reply(user_id, event.reply_token, reply_msg, configuration,
                    source_type=source_type)
        return True

    return False

def cmd_artist(ctx):
    keyword, page = parse_paginated_keyword(ctx.text)
    return search_by_artist(ctx.user_id, keyword, ctx.mai_ver, page, ctx.source_type)

def cmd_designer(ctx):
    keyword, page = parse_paginated_keyword(ctx.text)
    return search_by_designer(ctx.user_id, keyword, ctx.mai_ver, page, ctx.source_type)

def cmd_bpm(ctx):
    query = parse_bpm_query(ctx.text)
    if query is None:
        return input_error(ctx.user_id)
    return search_by_bpm(
        ctx.user_id,
        query.minimum,
        query.maximum,
        ctx.mai_ver,
        query.page,
        ctx.source_type,
    )

def cmd_song_info(ctx):
    keyword = re.sub(r"(\s+info|ってどんな曲)$", "", ctx.text, flags=re.IGNORECASE).strip()
    if not keyword:
        quoted_message_id = getattr(ctx.event.message, "quoted_message_id", None)
        if not quoted_message_id:
            return info_error(ctx.user_id)
        try:
            image_bytes = _download_line_message_content(quoted_message_id)
            recognition = recognize_score_image_bytes(
                image_bytes,
                fields=("main_title",),
            )
        except InvalidScoreImageError:
            return song_error(ctx.user_id)
        keyword = str(
            (recognition.get("parsed") or {}).get("title") or ""
        ).strip()
        if not keyword:
            return song_error(ctx.user_id)
        logger.info(
            "[SongInfo] OCR title search: user_id=%s title=%s",
            ctx.user_id,
            keyword,
        )
    return asyncio.run(search_song(ctx.user_id, keyword, ctx.mai_ver))

def cmd_random_song(ctx):
    keyword = re.sub(r"^random", "", ctx.text).strip()
    return asyncio.run(random_song(ctx.user_id, keyword, ctx.mai_ver))

def cmd_rc(ctx):
    return handle_rc_command(ctx.text, ctx.user_id)

def cmd_export(ctx):
    fmt = ctx.match.group(2).lower()
    return handle_export_command(ctx.user_id, fmt)

def cmd_plate(ctx):
    title, filter_mode = parse_plate_query(ctx.text)
    return asyncio.run(generate_plate_rcd(
        ctx.user_id, ctx.id_use, title, ctx.mai_ver_use, filter_mode=filter_mode))

def cmd_level_records(ctx):
    level, page = parse_level_records_query(ctx.text)
    return asyncio.run(generate_level_records(
        ctx.user_id, ctx.id_use, level, ctx.mai_ver_use, page))

def cmd_version_songs(ctx):
    msg = ctx.text
    title = re.sub(r"\s*\+\s*", " PLUS",
                   re.sub(r"\s+ver$", "", msg, flags=re.IGNORECASE)).strip()
    return asyncio.run(generate_version_songs(ctx.user_id, title, ctx.mai_ver))

def cmd_level_rank_list(ctx):
    """Level/constant list. Keeps self lookup behavior for compatibility."""
    level = re.sub(r"\s+levels$", "", ctx.text, flags=re.IGNORECASE)
    return asyncio.run(generate_level_rank_progress(
        ctx.user_id, ctx.user_id, level, ver=ctx.mai_ver))

def cmd_level_rank_progress(ctx):
    """Level/category + rank + prog, for example "14AP prog -uc"."""
    msg_lower = ctx.text.lower()
    level, rank = _parse_level_rank_progress_text(msg_lower)
    if not level or not rank:
        return input_error(ctx.user_id)
    filter_mode = parse_filter_mode(msg_lower)
    return asyncio.run(generate_level_rank_progress(
        ctx.user_id, ctx.id_use, level, rank, ctx.mai_ver_use,
        filter_mode=filter_mode))

def cmd_b_records(ctx):
    """b50 / best50 / ab50 / ... → generate_records；mode 由 RANK_COMMANDS 解析"""
    msg_lower = ctx.text.lower()
    splits = re.split(r"[ \n]", msg_lower, 1)
    first = splits[0]
    rest = splits[1] if len(splits) > 1 else ""
    mode = None
    for aliases, mode_value in RANK_COMMANDS.items():
        if first in aliases:
            mode = mode_value
            break
    if mode is None:
        return input_error(ctx.user_id)  # matcher 保证不会到这
    return asyncio.run(generate_records(
        ctx.user_id, ctx.id_use, mode, rest, ctx.mai_ver_use))

def cmd_calc_notes(ctx):
    """calc <tap> <hold> <slide> [touch] <break>"""
    notes = parse_note_counts(ctx.text)
    if notes is None:
        return input_error(ctx.user_id)
    return generate_calc_result_flex(
        notes,
        get_note_score(notes),
        user_id=ctx.user_id,
    )


# ---- bind / rebind / settings 共用小工具 ----

def _check_private_or_warn(ctx, warn_text_dict):
    if ctx.source_type != 'user':
        return generate_status_flex(
            language_catalog("main.private_chat_title"),
            warn_text_dict,
            ctx.user_id,
            tone="warning",
        )
    return None

def _has_full_account(user_data):
    return all(k in user_data for k in ['sega_id', 'sega_pwd', 'version'])

def _can_open_settings(user_data):
    return _has_full_account(user_data) or bool(
        user_data.get("import_only")
        or user_data.get("auth_type") == "import_token"
        or user_data.get("import_tokens")
    )

def cmd_bind(ctx):
    warn = _check_private_or_warn(ctx, language_catalog("messages.bind_group_warning_text"))
    if warn is not None:
        return warn
    add_user(ctx.user_id)
    if _has_full_account(get_user(ctx.user_id) or {}):
        return generate_status_flex(
            language_catalog("main.already_linked_title"),
            language_catalog("messages.already_bound_text"),
            ctx.user_id,
            tone="warning",
        )
    url = f"https://{DOMAIN}/linebot/sega_bind?token={generate_bind_token(ctx.user_id)}"
    return generate_account_action_flex("bind", url, ctx.user_id)

def cmd_rebind(ctx):
    warn = _check_private_or_warn(ctx, language_catalog("messages.rebind_group_warning_text"))
    if warn is not None:
        return warn
    if not _has_full_account(get_user(ctx.user_id) or {}):
        return generate_status_flex(
            language_catalog("main.not_linked_title"),
            language_catalog("messages.rebind_not_bound_text"),
            ctx.user_id,
            tone="warning",
        )
    url = f"https://{DOMAIN}/linebot/sega_bind?token={generate_bind_token(ctx.user_id)}&mode=rebind"
    return generate_account_action_flex("rebind", url, ctx.user_id)

def cmd_settings(ctx):
    warn = _check_private_or_warn(ctx, language_catalog("messages.settings_group_warning_text"))
    if warn is not None:
        return warn
    if not _can_open_settings(get_user(ctx.user_id) or {}):
        return generate_status_flex(
            language_catalog("main.not_linked_title"),
            language_catalog("messages.rebind_not_bound_text"),
            ctx.user_id,
            tone="warning",
        )
    url = f"https://{DOMAIN}/linebot/settings?token={generate_settings_token(ctx.user_id)}"
    return generate_account_action_flex("settings", url, ctx.user_id)


# ---- B 系列命令的 first-word 集合（从 RANK_COMMANDS 自动展开）----
_B_COMMAND_WORDS = rank_command_words()
HELP_B_COMMAND_WORDS = rank_command_words(hidden=HIDDEN_HELP_COMMAND_WORDS)


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
    Command(Regex(r"^.+\s+record$", re.IGNORECASE),
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
    Command(Regex(r"^.+(\s+info|ってどんな曲)$", re.IGNORECASE),
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
        
    bind_url = f"https://{DOMAIN}/linebot/sega_bind?token={generate_bind_token(user_id)}"
    reply_message = generate_welcome_flex(user_id, bind_url=bind_url)

    return smart_reply(user_id, reply_token, reply_message, configuration, False)


# Unfollow 事件处理
@handler.add(UnfollowEvent)
def handle_unfollow(event):
    user_id = event.source.user_id
    logger.info(f"[UnfollowEvent] {user_id} left")
    unlink_rich_menu(user_id)
    try:
        track_event('user_unbind', user_id=user_id, metadata={'source': 'line_unfollow'})
    except Exception: pass
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
    process = psutil.Process(os.getpid())
    process_memory_mb = round(process.memory_info().rss / (1024**2), 1)

    with stats_lock:
        task_stats = dict(STATS)

    stats = {
        'total_users': total_users,
        'jp_users': jp_users,
        'intl_users': intl_users,
        'jp_percent': round((jp_users / total_users * 100) if total_users > 0 else 0, 1),
        'intl_percent': round((intl_users / total_users * 100) if total_users > 0 else 0, 1),
        'cpu_percent': cpu_percent,
        'cpu_count_total': cpu_count,
        'cpu_count_used': round(cpu_percent / 100 * cpu_count, 1),
        'memory_percent': round(memory.percent, 1),
        'memory_used_gb': round(memory.used / (1024**3), 1),
        'total_memory': round(memory.total / (1024**3), 1),
        'process_memory_mb': process_memory_mb,
        'uptime': uptime_str,
        'python_version': platform.python_version(),
        'platform': f"{platform.system()} {platform.release()}",
        'platform_short': platform.system(),
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
            cleaned_rate_limits = cleanup_rate_limiter_tracking(rate_limiter_module)

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
