import json
import logging
import os
import queue
import re
import secrets
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from types import SimpleNamespace
from typing import Callable

from PIL import Image, UnidentifiedImageError
from flask import (
    Blueprint,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
)

from modules.backup_manager import create_backup
from modules.config_loader import (
    ADMIN_PASSWORD,
    BACKUP_DIR,
    BG_DIR,
    CONFIG_PATH,
    DB_HOST,
    DB_NAME,
    DB_PASSWORD,
    DB_USER,
    DXDATA_FILE,
    DXDATA_URL,
    LOG_FILE,
    VAPID_PUBLIC_KEY,
    read_dxdata,
)
from modules.devtoken_manager import (
    create_dev_token,
    list_dev_tokens,
    load_dev_tokens,
    revoke_dev_token,
    save_dev_tokens,
)
from modules.dxdata_manager import update_dxdata_with_comparison
from modules.event_tracker import get_hourly_stats
from modules.message_manager import build_dxdata_update_message
from modules.monitoring.codex_agent import (
    CodexMonitorBusy,
    CodexMonitorError,
    CodexMonitorTimeout,
    ask_codex,
    get_generated_image,
    release_codex_session,
)
from modules.monitoring.file_access import is_asset_image, resolve_allowed_path
from modules.monitoring.markdown_renderer import render_markdown
from modules.notice_manager import (
    delete_notice,
    get_all_notices,
    get_latest_published_notice,
    get_notice_by_id,
    publish_notice,
    update_notice,
    upload_notice,
)
from modules.notice_stats import (
    calculate_notice_stats,
    get_all_notices_stats,
)
from modules.notification_manager import (
    add_push_subscription,
    clear_notifications,
    get_notifications,
    remove_push_subscription,
)
from modules.rich_menu_manager import link_unbound_rich_menu
from modules.task_runtime import discard_queued, track_queued
from modules.tip_ad_manager import (
    create_tip_ad,
    delete_tip_ad,
    get_all_tip_ads,
    get_tip_ad_by_id,
    update_tip_ad,
)
from modules.user_db import get_all_user_ids, get_user, load_all_users, save_user, user_exists
from modules.user_manager import (
    clear_notice_read_status,
    clear_notice_record,
    delete_user,
    edit_user_value,
    nickname_cache,
    nickname_cache_lock,
    record_notice_vote,
)
from modules.web_i18n import localized_payload


logger = logging.getLogger(__name__)
admin_api = Blueprint("admin_api", __name__)
CSRF_EXEMPT_ENDPOINTS = (
    "admin_trigger_update",
    "admin_create_notice",
    "admin_update_notice",
    "admin_delete_notice",
    "admin_publish_notice",
    "notice_vote",
    "admin_create_tip_ads",
    "admin_put_tip_ads",
    "admin_delete_tip_ads",
    "admin_backgrounds",
    "admin_delete_background",
    "admin_edit_user",
    "admin_delete_user",
    "admin_clear_cache",
    "admin_get_user_data",
    "admin_load_nicknames",
    "admin_delete_backup",
    "admin_update_dxdata",
)


@dataclass(frozen=True)
class AdminServices:
    overview: Callable
    nickname: Callable
    fallback_nickname: Callable
    update_task: Callable
    task_queue: object
    task_tracking: dict
    task_tracking_lock: object


_services: AdminServices | None = None


@dataclass
class _AIMonitorJob:
    session_id: str
    created_at: float
    status: str = "running"
    result: dict | None = None
    error: str = ""
    status_code: int = 500


_ai_monitor_jobs: dict[str, _AIMonitorJob] = {}
_ai_monitor_jobs_lock = threading.Lock()
_AI_MONITOR_JOB_TTL_SECONDS = 3600
_AI_MONITOR_JOB_ID = re.compile(r"^[A-Za-z0-9_-]{16,80}$")


def configure_admin_api(**services):
    global _services
    _services = AdminServices(**services)


def check_admin_auth():
    return session.get("admin_authenticated", False)


def _json_body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def _ai_monitor_images():
    uploads = request.files.getlist("images")
    if len(uploads) > 3:
        raise ValueError("At most 3 images are allowed")

    validated = []
    suffixes = {"PNG": ".png", "JPEG": ".jpg", "WEBP": ".webp"}
    if any(
        upload.mimetype in {"image/heic", "image/heif"}
        or os.path.splitext(upload.filename or "")[1].lower() in {".heic", ".heif"}
        for upload in uploads
    ):
        from pillow_heif import register_heif_opener
        register_heif_opener()
    for uploaded in uploads:
        image_data = uploaded.read(5 * 1024 * 1024 + 1)
        if len(image_data) > 5 * 1024 * 1024:
            raise ValueError("Each image must be 5MB or smaller")
        if not image_data:
            raise ValueError("Attached image is empty")
        try:
            with Image.open(BytesIO(image_data)) as image:
                detected_format = image.format
                width, height = image.size
                if width < 1 or height < 1 or width * height > 40_000_000:
                    raise ValueError("Image dimensions are not supported")
                image.load()
                if detected_format in {"HEIC", "HEIF"}:
                    converted = BytesIO()
                    image.convert("RGB").save(converted, format="JPEG", quality=90)
                    image_data = converted.getvalue()
                    detected_format = "JPEG"
        except (Image.DecompressionBombError, UnidentifiedImageError, OSError) as exc:
            raise ValueError("Only valid PNG, JPEG, WebP, or HEIC images are allowed") from exc
        if detected_format not in suffixes:
            raise ValueError("Only PNG, JPEG, WebP, or HEIC images are allowed")
        validated.append((suffixes[detected_format], image_data))
    return validated


def _cleanup_ai_monitor_jobs(now: float) -> None:
    expired = [
        job_id for job_id, job in _ai_monitor_jobs.items()
        if job.status != "running" and now - job.created_at >= _AI_MONITOR_JOB_TTL_SECONDS
    ]
    for job_id in expired:
        _ai_monitor_jobs.pop(job_id, None)


def _run_ai_monitor_job(
    job_id: str,
    session_id: str,
    question: str,
    history: list[dict[str, str]],
    image_inputs: list[tuple[str, bytes]],
) -> None:
    try:
        try:
            runtime_snapshot = _services.overview(force_refresh=False)
        except Exception as exc:
            logger.warning("[AIMonitor] In-process snapshot unavailable: %s", exc)
            runtime_snapshot = {"available": False, "error": type(exc).__name__}
        response = ask_codex(
            question,
            session_id=session_id,
            runtime_snapshot=runtime_snapshot,
            history=history,
            image_inputs=image_inputs,
        )
        update = {
            "status": "completed",
            "result": {
                "answer": response["text"],
                "answer_html": render_markdown(response["text"]),
                "images": response["images"],
            },
            "status_code": 200,
        }
    except CodexMonitorBusy as exc:
        update = {"status": "failed", "error": str(exc), "status_code": 429}
    except CodexMonitorTimeout as exc:
        logger.warning("[AIMonitor] Diagnosis timed out")
        update = {"status": "failed", "error": str(exc), "status_code": 504}
    except CodexMonitorError as exc:
        logger.warning("[AIMonitor] Diagnosis unavailable: %s", exc)
        update = {"status": "failed", "error": str(exc), "status_code": 503}
    except Exception as exc:
        logger.exception("[AIMonitor] Background diagnosis failed")
        update = {
            "status": "failed",
            "error": f"Diagnosis failed: {type(exc).__name__}",
            "status_code": 500,
        }
    with _ai_monitor_jobs_lock:
        job = _ai_monitor_jobs.get(job_id)
        if job is not None:
            job.status = update["status"]
            job.result = update.get("result")
            job.error = update.get("error", "")[:500]
            job.status_code = update["status_code"]


@admin_api.route("/admin/panel", methods=["GET", "POST"])
def admin_panel():
    if request.method == "POST":
        password = request.form.get("password", "")

        if password and password == ADMIN_PASSWORD:
            session['admin_authenticated'] = True
            session.permanent = True
            return redirect("/admin/panel")
        else:
            return render_template("admin_login.html", error="Invalid password")

    if not check_admin_auth():
        return render_template("admin_login.html")

    force_refresh = bool(request.args.get('refresh'))
    stats = _services.overview(force_refresh=force_refresh)

    logs = ""
    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            logs = ''.join(f.readlines()[-100:])
    except Exception as e:
        logs = f"Error reading logs: {e}"

    return render_template(
        "admin_panel.html",
        total_users=stats['total_users'],
        stats=stats,
        logs=logs
    )


@admin_api.route("/admin/api/overview", methods=["GET"])
def admin_api_overview():
    if not check_admin_auth():
        return jsonify({"error": "Unauthorized"}), 401
    force_refresh = bool(request.args.get("refresh"))
    return jsonify({"success": True, "stats": _services.overview(force_refresh=force_refresh)})


@admin_api.route("/admin/logout", methods=["GET"])
def admin_logout():
    release_codex_session(session.pop("ai_monitor_session_id", ""))
    session.pop('admin_authenticated', None)
    return redirect("/admin/panel")

@admin_api.route("/admin/api/hourly", methods=["GET"])
def admin_api_hourly():
    if not check_admin_auth():
        return jsonify({"error": "Unauthorized"}), 401
    date_str = request.args.get("date", "")
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        return jsonify({"error": "Invalid date format, use YYYY-MM-DD"}), 400
    return jsonify(get_hourly_stats(date_str))


@admin_api.route("/admin/api/users", methods=["GET"])
def admin_api_users():
    if not check_admin_auth():
        return jsonify({"error": "Unauthorized"}), 401

    try:
        limit = max(1, min(100, int(request.args.get("limit", 50))))
        offset = max(0, int(request.args.get("offset", 0)))
    except ValueError:
        return jsonify({"success": False, "message": "Invalid pagination"}), 400

    query = request.args.get("q", "").strip().lower()
    all_users = load_all_users()
    rows = []
    for user_id, user_info in all_users.items():
        nickname = user_info.get("nickname") or _services.fallback_nickname(user_id)
        if query and query not in user_id.lower() and query not in str(nickname).lower():
            continue
        rows.append({
            "user_id": user_id,
            "nickname": nickname,
            "json_str": json.dumps(user_info, indent=2, ensure_ascii=False),
        })

    rows.sort(key=lambda item: item["user_id"])
    page = rows[offset:offset + limit]
    return jsonify({
        "success": True,
        "users": page,
        "total": len(rows),
        "offset": offset,
        "limit": limit,
        "has_more": offset + limit < len(rows),
    })


@admin_api.route("/admin/trigger_update", methods=["POST"])
def admin_trigger_update():
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    data = _json_body()
    user_id = data.get('user_id')

    if not user_id:
        return jsonify({'error': 'User ID required'}), 400

    try:
        mock_event = SimpleNamespace(source=SimpleNamespace(user_id=user_id), reply_token=None)

        task_id = f"admin_update_{user_id}_{datetime.now().timestamp()}"

        nickname = _services.nickname(user_id, use_cache=True)

        track_queued(_services.task_tracking, _services.task_tracking_lock, {
            'id': task_id,
            'function': 'async_admin_maimai_update_task',
            'queue_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'user_id': user_id,
            'nickname': nickname
        })

        _services.task_queue.put_nowait((_services.update_task, (mock_event,), task_id))

        return jsonify({
            'success': True,
            'message': f'Update task queued for user {user_id}'
        })
    except queue.Full:
        discard_queued(_services.task_tracking, _services.task_tracking_lock, task_id)
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

@admin_api.route("/admin/get_logs", methods=["GET"])
def admin_get_logs():
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            logs = ''.join(f.readlines()[-100:])
        return jsonify({'logs': logs})
    except Exception as e:
        return jsonify({'logs': f'Error reading logs: {e}'})


@admin_api.route("/admin/api/ai-monitor/query", methods=["POST"])
def admin_ai_monitor_query():
    if not check_admin_auth():
        return jsonify({"error": "Unauthorized"}), 401

    if request.content_length and request.content_length > 16 * 1024 * 1024:
        return jsonify({"success": False, "message": "Request is too large"}), 413

    data = request.form if request.form or request.files else _json_body()
    raw_history = data.get("history", [])
    if isinstance(raw_history, str):
        try:
            raw_history = json.loads(raw_history)
        except (TypeError, json.JSONDecodeError):
            raw_history = []
    try:
        image_inputs = _ai_monitor_images()
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400

    question = str(data.get("question") or "").strip()
    if not question and image_inputs:
        question = "Analyze the attached image or images."
    if not question:
        return jsonify({"success": False, "message": "Question is required"}), 400
    if len(question) > 2000:
        return jsonify({"success": False, "message": "Question is too long"}), 400

    job_id = str(data.get("job_id") or secrets.token_urlsafe(24))
    if not _AI_MONITOR_JOB_ID.fullmatch(job_id):
        return jsonify({"success": False, "message": "Invalid job ID"}), 400
    session_id = session.setdefault("ai_monitor_session_id", secrets.token_urlsafe(24))

    history = []
    if isinstance(raw_history, list):
        for item in raw_history[-20:]:
            if not isinstance(item, dict) or item.get("role") not in {"user", "assistant"}:
                continue
            content = str(item.get("content", "")).strip()
            if content:
                history.append({"role": item["role"], "content": content[:4000]})

    with _ai_monitor_jobs_lock:
        _cleanup_ai_monitor_jobs(time.monotonic())
        existing = _ai_monitor_jobs.get(job_id)
        if existing is not None:
            if existing.session_id != session_id:
                return jsonify({"success": False, "message": "Job ID is already in use"}), 409
            return jsonify({"success": True, "job_id": job_id, "status": existing.status}), 202
        active = next((
            active_id for active_id, job in _ai_monitor_jobs.items()
            if job.session_id == session_id and job.status == "running"
        ), None)
        if active:
            return jsonify({"success": True, "job_id": active, "status": "running"}), 202
        _ai_monitor_jobs[job_id] = _AIMonitorJob(session_id, time.monotonic())

    threading.Thread(
        target=_run_ai_monitor_job,
        args=(job_id, session_id, question, history, image_inputs),
        name=f"ai-monitor-{job_id[:8]}",
        daemon=True,
    ).start()
    return jsonify({"success": True, "job_id": job_id, "status": "running"}), 202


@admin_api.route("/admin/api/ai-monitor/query/<job_id>", methods=["GET"])
def admin_ai_monitor_result(job_id: str):
    if not check_admin_auth():
        return jsonify({"error": "Unauthorized"}), 401
    session_id = session.get("ai_monitor_session_id", "")
    with _ai_monitor_jobs_lock:
        _cleanup_ai_monitor_jobs(time.monotonic())
        job = _ai_monitor_jobs.get(job_id)
        if job is None or job.session_id != session_id:
            return jsonify({"success": False, "message": "Diagnosis not found"}), 404
        status = job.status
        result = dict(job.result or {})
        error = job.error
        status_code = job.status_code
    if status == "running":
        return jsonify({"success": True, "job_id": job_id, "status": status}), 202
    if status == "completed":
        return jsonify({"success": True, "job_id": job_id, "status": status, **result})
    return jsonify({"success": False, "job_id": job_id, "status": status, "message": error}), status_code


@admin_api.route("/admin/api/ai-monitor/image", methods=["GET"])
def admin_ai_monitor_image():
    if not check_admin_auth():
        return jsonify({"error": "Unauthorized"}), 401
    token = request.args.get("token", "")
    if token:
        generated = get_generated_image(token)
        if generated is None:
            return jsonify({"error": "Image not found"}), 404
        return send_file(generated, conditional=True, max_age=3600)
    path, error = resolve_allowed_path(request.args.get("path", ""))
    if error or path is None or not is_asset_image(path):
        return jsonify({"error": "Image not found"}), 404
    return send_file(path, conditional=True, max_age=3600)

@admin_api.route("/admin/get_notices", methods=["GET"])
def admin_get_notices():
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        notices = get_all_notices(include_drafts=True)
        return jsonify({'success': True, 'notices': notices})
    except Exception as e:
        logger.error(f"[Admin] ✗ Get notices error: error={e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_api.route("/admin/create_notice", methods=["POST"])
def admin_create_notice():
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    data = _json_body()

    content = localized_payload(data, "content")
    if not any(content.values()):
        return jsonify({'success': False, 'message': 'At least one language content is required'}), 400

    status = data.get('status', 'published')  # 'draft' | 'published'
    voting_enabled = data.get('voting_enabled', False)
    created_by = session.get('user_id', 'admin')

    button_type = data.get('button_type')
    button_value = data.get('button_value', '').strip()
    button_labels = localized_payload(data, "button_label")

    try:
        notice_id = upload_notice(
            content=content,
            status=status,
            voting_enabled=voting_enabled,
            created_by=created_by,
            button_type=button_type,
            button_label=button_labels if button_type and button_value else None,
            button_value=button_value
        )

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

@admin_api.route("/admin/update_notice", methods=["POST"])
def admin_update_notice():
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    data = _json_body()
    notice_id = data.get('notice_id')

    content = localized_payload(data, "content")
    if not notice_id or not any(content.values()):
        return jsonify({'success': False, 'message': 'Notice ID and at least one language content are required'}), 400

    button_type = data.get('button_type')
    button_value = data.get('button_value', '').strip()
    remove_button = data.get('remove_button', False)
    button_labels = localized_payload(data, "button_label")

    try:
        latest_notice = get_latest_published_notice()
        is_latest = latest_notice and latest_notice.get('id') == notice_id

        success = update_notice(
            notice_id,
            content,
            button_type=button_type,
            button_label=button_labels if button_type and button_value else None,
            button_value=button_value,
            remove_button=remove_button
        )

        if success:
            notice = get_notice_by_id(notice_id)
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

@admin_api.route("/admin/delete_notice", methods=["POST"])
def admin_delete_notice():
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    data = _json_body()
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

@admin_api.route("/admin/publish_notice", methods=["POST"])
def admin_publish_notice():
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    data = _json_body()
    notice_id = data.get('notice_id')

    if not notice_id:
        return jsonify({'success': False, 'message': 'Notice ID is required'}), 400

    try:
        success = publish_notice(notice_id)

        if success:
            clear_notice_read_status(notice_id)
            logger.info(f"[Admin] ✓ Published draft notice: notice_id={notice_id}")
            return jsonify({'success': True, 'message': 'Notice published successfully'})
        else:
            return jsonify({'success': False, 'message': 'Notice not found or already published'}), 404

    except Exception as e:
        logger.error(f"[Admin] ✗ Publish notice error: error={e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_api.route("/admin/get_notice_stats", methods=["GET"])
def admin_get_notice_stats():
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    notice_id = request.args.get('notice_id')

    try:
        if notice_id:
            stats = calculate_notice_stats(notice_id)
            if stats is None:
                return jsonify({'success': False, 'message': 'Notice not found'}), 404
            return jsonify({'success': True, 'stats': stats})
        else:
            stats = get_all_notices_stats()
            return jsonify({'success': True, 'stats': stats})

    except Exception as e:
        logger.error(f"[Admin] ✗ Get notice stats error: error={e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_api.route("/linebot/notice_vote", methods=["POST"])
def notice_vote():
    data = _json_body()
    user_id = data.get('user_id')
    notice_id = data.get('notice_id')
    vote_type = data.get('vote_type')  # 'support' | 'oppose'

    if not all([user_id, notice_id, vote_type]):
        return jsonify({'success': False, 'message': 'Missing required parameters'}), 400

    if vote_type not in ['support', 'oppose']:
        return jsonify({'success': False, 'message': 'Invalid vote type'}), 400

    try:
        notice = get_notice_by_id(notice_id)
        if not notice:
            return jsonify({'success': False, 'message': 'Notice not found'}), 404

        if not notice.get('voting_enabled'):
            return jsonify({'success': False, 'message': 'Voting is not enabled for this notice'}), 400

        success = record_notice_vote(user_id, notice_id, vote_type)

        if success:
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

@admin_api.route("/admin/tip_ads", methods=["GET"])
def admin_get_tip_ads():
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        tip_ads = get_all_tip_ads()
        return jsonify({'success': True, 'tip_ads': tip_ads})
    except Exception as e:
        logger.error(f"[Admin] ✗ Get tip/ads error: error={e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_api.route("/admin/tip_ads/<tip_ad_id>", methods=["GET"])
def admin_get_tip_ad(tip_ad_id):
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        tip_ad = get_tip_ad_by_id(tip_ad_id)
        return jsonify({'success': True, 'tip_ad': tip_ad})
    except Exception as e:
        logger.error(f"[Admin] ✗ Get tip/ads by id error: error={e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_api.route("/admin/tip_ads", methods=["POST"])
def admin_create_tip_ads():
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    data = _json_body()
    tip_type = data.get('type')
    text = localized_payload(data, "text")
    button_type = data.get('button_type')
    button_labels = localized_payload(data, "button_label")
    button_value = data.get('button_value')
    enabled = data.get('enabled', True)

    if not tip_type or not any(text.values()):
        return jsonify({'success': False, 'message': 'Missing required fields'}), 400

    if tip_type not in ['tip', 'ad']:
        return jsonify({'success': False, 'message': 'Invalid type'}), 400

    try:
        tip_ad = create_tip_ad(
            tip_type=tip_type,
            text=text,
            button_type=button_type,
            button_labels=button_labels,
            button_value=button_value,
            enabled=enabled
        )
        logger.info(f"[Admin] ✓ Created tip/ad: id={tip_ad['id']}, type={tip_type}")
        return jsonify({'success': True, 'tip_ad': tip_ad})
    except Exception as e:
        logger.error(f"[Admin] ✗ Create tip/ad error: error={e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_api.route("/admin/tip_ads/<tip_ad_id>", methods=["PUT"])
def admin_put_tip_ads(tip_ad_id):
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    data = _json_body()

    if not tip_ad_id:
        return jsonify({'success': False, 'message': 'Missing id'}), 400

    tip_type = data.get('type')
    text = localized_payload(data, "text")
    button_type = data.get('button_type')
    button_labels = localized_payload(data, "button_label")
    button_value = data.get('button_value')
    enabled = data.get('enabled')
    remove_button = data.get('remove_button', False)

    try:
        tip_ad = update_tip_ad(
            tip_ad_id=tip_ad_id,
            tip_type=tip_type,
            text=text,
            button_type=button_type,
            button_labels=button_labels,
            button_value=button_value,
            enabled=enabled,
            remove_button=remove_button
        )

        if tip_ad:
            logger.info(f"[Admin] ✓ Updated tip/ad: id={tip_ad_id}")
            return jsonify({'success': True, 'tip_ad': tip_ad})
        else:
            return jsonify({'success': False, 'message': 'Tip/ad not found'}), 404
    except Exception as e:
        logger.error(f"[Admin] ✗ Update tip/ad error: error={e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_api.route("/admin/tip_ads/<tip_ad_id>", methods=["DELETE"])
def admin_delete_tip_ads(tip_ad_id):
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    if not tip_ad_id:
        return jsonify({'success': False, 'message': 'Missing id'}), 400

    try:
        success = delete_tip_ad(tip_ad_id)
        if success:
            logger.info(f"[Admin] ✓ Deleted tip/ad: id={tip_ad_id}")
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': 'Tip/ad not found'}), 404
    except Exception as e:
        logger.error(f"[Admin] ✗ Delete tip/ad error: error={e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== 背景图管理 API ====================

@admin_api.route("/admin/backgrounds", methods=["GET", "POST"])
def admin_backgrounds():
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    if request.method == "GET":
        try:
            files = []
            for f in sorted(os.listdir(BG_DIR)):
                if not f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    continue
                filepath = os.path.join(BG_DIR, f)
                size_bytes = os.path.getsize(filepath)
                if size_bytes < 1024:
                    size_str = f"{size_bytes}B"
                elif size_bytes < 1024 * 1024:
                    size_str = f"{size_bytes / 1024:.1f}KB"
                else:
                    size_str = f"{size_bytes / (1024 * 1024):.1f}MB"
                files.append({
                    'name': f,
                    'size': size_str,
                    'is_user': f.startswith("jietnguser_"),
                })
            return jsonify({'success': True, 'files': files})
        except Exception as e:
            logger.error(f"[Admin] ✗ List backgrounds error: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    uploaded = request.files.get('file')
    if not uploaded or not uploaded.filename:
        return jsonify({'success': False, 'message': 'No file provided'}), 400

    original_name = uploaded.filename
    ext = os.path.splitext(original_name)[1].lower()
    if ext not in {'.png', '.jpg', '.jpeg', '.webp', '.heic', '.heif'}:
        return jsonify({'success': False, 'message': 'Unsupported format. Only PNG/JPG/WebP/HEIC.'}), 400

    file_data = uploaded.read()
    if len(file_data) > 10 * 1024 * 1024:
        return jsonify({'success': False, 'message': 'File too large (max 10MB)'}), 400

    try:
        from PIL import Image as PILImage
        from io import BytesIO
        try:
            from pillow_heif import register_heif_opener
            register_heif_opener()
        except ImportError:
            pass
        with PILImage.open(BytesIO(file_data)) as source_img:
            source_img.load()
            img = source_img.copy()
    except Exception:
        return jsonify({'success': False, 'message': 'Invalid or corrupted image file'}), 400

    safe_name = os.path.splitext(os.path.basename(original_name))[0] + ext
    if not safe_name or safe_name.startswith('.'):
        return jsonify({'success': False, 'message': 'Invalid filename'}), 400

    if ext in {'.heic', '.heif'}:
        safe_name = os.path.splitext(safe_name)[0] + '.webp'
        save_path = os.path.join(BG_DIR, safe_name)
        try:
            img = img.convert("RGB")
            img.save(save_path, "WEBP", quality=85)
        except Exception as e:
            logger.error(f"[Admin] ✗ HEIC conversion error: {e}")
            return jsonify({'success': False, 'message': 'Failed to convert HEIC'}), 500
    else:
        save_path = os.path.join(BG_DIR, safe_name)
        try:
            with open(save_path, 'wb') as f:
                f.write(file_data)
        except Exception as e:
            logger.error(f"[Admin] ✗ Upload background error: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    logger.info(f"[Admin] ✓ Uploaded background: {safe_name}")
    return jsonify({'success': True, 'filename': safe_name}), 201


@admin_api.route("/admin/backgrounds/<filename>", methods=["DELETE"])
def admin_delete_background(filename):
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    safe_name = os.path.basename(filename)
    filepath = os.path.join(BG_DIR, safe_name)

    if not os.path.exists(filepath):
        return jsonify({'success': False, 'message': 'File not found'}), 404

    try:
        os.remove(filepath)
        logger.info(f"[Admin] ✓ Deleted background: {safe_name}")

        for uid, udata in load_all_users().items():
            user_bg_list = udata.get('bg_files', [])
            if safe_name in user_bg_list:
                user_bg_list.remove(safe_name)
                edit_user_value(uid, 'bg_files', user_bg_list)

        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"[Admin] ✗ Delete background error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


# ==================== 用户管理 API ====================

@admin_api.route("/admin/edit_user", methods=["POST"])
def admin_edit_user():
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    data = _json_body()
    user_id = data.get('user_id')
    user_data = data.get('user_data')

    if not user_id or user_data is None:
        return jsonify({
            'success': False,
            'message': 'User ID and user data required'
        }), 400

    try:
        if not user_exists(user_id):
            return jsonify({
                'success': False,
                'message': f'User {user_id} not found'
            }), 404

        existing_data = get_user(user_id) or {}
        existing_data.update(user_data)
        save_user(user_id, existing_data)

        logger.info(f"[Admin] ✓ User data edited: user_id={user_id}")


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

@admin_api.route("/admin/delete_user", methods=["POST"])
def admin_delete_user():
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    data = _json_body()
    user_id = data.get('user_id')

    if not user_id:
        return jsonify({
            'success': False,
            'message': 'User ID required'
        }), 400

    try:
        if not user_exists(user_id):
            return jsonify({
                'success': False,
                'message': f'User {user_id} not found'
            }), 404

        delete_user(user_id)
        link_unbound_rich_menu(user_id)

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

@admin_api.route("/admin/clear_cache", methods=["POST"])
def admin_clear_cache():
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

@admin_api.route("/admin/get_user_data", methods=["POST"])
def admin_get_user_data():
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    data = _json_body()
    user_id = data.get('user_id')

    if not user_id:
        return jsonify({
            'success': False,
            'message': 'User ID required'
        }), 400

    try:
        user_info = get_user(user_id)
        if not user_info:
            return jsonify({
                'success': False,
                'message': f'User {user_id} not found'
            }), 404

        nickname = _services.nickname(user_id, use_cache=False)

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

@admin_api.route("/admin/load_nicknames", methods=["POST"])
def admin_load_nicknames():
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        data = _json_body()
        refresh = bool(data.get('refresh'))

        nicknames = {}
        if refresh:
            for user_id in get_all_user_ids():
                nicknames[user_id] = _services.nickname(user_id, use_cache=False)
        else:
            for user_id, user_info in load_all_users().items():
                nicknames[user_id] = user_info.get('nickname') or _services.fallback_nickname(user_id)

        return jsonify({
            'success': True,
            'nicknames': nicknames,
            'count': len(nicknames),
            'refreshed': refresh
        })

    except Exception as e:
        logger.error(f"[Admin] ✗ Load nicknames error: error={e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@admin_api.route("/admin/backups", methods=["POST"])
def admin_create_backup():
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        db_config = {
            'host': DB_HOST,
            'user': DB_USER,
            'password': DB_PASSWORD,
            'database': DB_NAME
        }

        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config_data = json.load(f)

        success, message, backup_path = create_backup(
            users_data=load_all_users(),
            config_data=config_data,
            db_config=db_config,
            backup_password=ADMIN_PASSWORD,
        )

        return jsonify({'success': success, 'message': message})
    except Exception as e:
        logger.error(f"[Admin] ✗ Create backup error: error={e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)})


@admin_api.route("/admin/get_backups", methods=["GET"])
def admin_get_backups():
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        backup_files = []

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

@admin_api.route("/admin/download_backup", methods=["GET"])
def admin_download_backup():
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    filename = None
    try:
        filename = request.args.get('file')
        if not filename:
            return jsonify({
                'success': False,
                'message': 'Missing file parameter'
            }), 400

        if not filename.startswith("backup_") or not filename.endswith(".zip"):
            return jsonify({
                'success': False,
                'message': 'Invalid backup filename'
            }), 400

        if ".." in filename or "/" in filename or "\\" in filename:
            return jsonify({
                'success': False,
                'message': 'Invalid filename'
            }), 400

        backup_path = os.path.join(BACKUP_DIR, filename)

        if not os.path.exists(backup_path):
            return jsonify({
                'success': False,
                'message': 'Backup file not found'
            }), 404

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

@admin_api.route("/admin/delete_backup", methods=["POST"])
def admin_delete_backup():
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        data = _json_body()
        filename = data.get('filename')

        if not filename:
            return jsonify({
                'success': False,
                'message': 'Missing filename parameter'
            }), 400

        if not filename.startswith("backup_") or not filename.endswith(".zip"):
            return jsonify({
                'success': False,
                'message': 'Invalid backup filename'
            }), 400

        if ".." in filename or "/" in filename or "\\" in filename:
            return jsonify({
                'success': False,
                'message': 'Invalid filename'
            }), 400

        backup_path = os.path.join(BACKUP_DIR, filename)

        if not os.path.exists(backup_path):
            return jsonify({
                'success': False,
                'message': 'Backup file not found'
            }), 404

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

@admin_api.route("/admin/dxdata_status", methods=["GET"])
def admin_dxdata_status():
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        songs, versions = read_dxdata()
        total_songs = len(songs)
        std_songs = len([s for s in songs if s['type'] == 'std'])
        dx_songs = len([s for s in songs if s['type'] == 'dx'])
        utage_songs = len([s for s in songs if s['type'] == 'utage'])

        total_sheets = 0
        jp_sheets = 0
        intl_sheets = 0

        for song in songs:
            if song['type'] == 'utage':
                continue
            for sheet in song['sheets']:
                total_sheets += 1
                if sheet['regions'].get('jp', False):
                    jp_sheets += 1
                if sheet['regions'].get('intl', False):
                    intl_sheets += 1

        total_versions = len(versions)
        version_names = [v.get('abbr', '') for v in versions]

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
            'versions': total_versions,
            'version_names': version_names
        })

    except Exception as e:
        logger.error(f"[Admin] ✗ DXData status error: error={e}", exc_info=True)
        return jsonify({
            'error': str(e)
        }), 500

@admin_api.route("/admin/update_dxdata", methods=["POST"])
def admin_update_dxdata():
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        result = update_dxdata_with_comparison(DXDATA_URL, DXDATA_FILE)
        message = build_dxdata_update_message(result, None)
        diff = result.get('diff', {})
        return jsonify({
            'success': True,
            'message': message,
            'sheets_added': diff.get('sheets_added', 0),
            'songs_added': diff.get('songs_added', 0)
        })
    except Exception as e:
        logger.error(f"[Admin] ✗ Update DXData error: error={e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_api.route("/admin/notifications", methods=["GET"])
def admin_get_notifications():
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    return jsonify(get_notifications())


@admin_api.route("/admin/notifications", methods=["DELETE"])
def admin_clear_notifications():
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    clear_notifications()
    return jsonify({'success': True})


@admin_api.route("/admin/vapid-public-key", methods=["GET"])
def admin_vapid_public_key():
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    return VAPID_PUBLIC_KEY, 200, {'Content-Type': 'text/plain'}


@admin_api.route("/admin/push-subscription", methods=["POST"])
def admin_add_push_subscription():
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    sub = _json_body()
    if not sub or not sub.get('endpoint'):
        return jsonify({'error': 'Invalid subscription'}), 400

    add_push_subscription(sub)
    return jsonify({'success': True})


@admin_api.route("/admin/push-subscription", methods=["DELETE"])
def admin_remove_push_subscription():
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    data = _json_body()
    endpoint = data.get('endpoint') if data else None
    if not endpoint:
        return jsonify({'error': 'Missing endpoint'}), 400

    remove_push_subscription(endpoint)
    return jsonify({'success': True})


# ==================== Admin DevToken Management ====================

@admin_api.route("/admin/devtokens", methods=["GET"])
def admin_list_devtokens():
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        tokens = list_dev_tokens()
        all_tokens = load_dev_tokens()
        for t in tokens:
            token_data = all_tokens.get(t['token_id'], {})
            t['allowed_users_count'] = len(token_data.get('allowed_users', []))
        return jsonify({'success': True, 'tokens': tokens})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@admin_api.route("/admin/devtokens", methods=["POST"])
def admin_create_devtoken():
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    data = _json_body()
    note = data.get('note', '').strip() if data else ''
    if not note:
        return jsonify({'success': False, 'message': 'Note is required'})

    result = create_dev_token(note, created_by='admin')
    if result:
        return jsonify({
            'success': True,
            'token_id': result['token_id'],
            'token': result['token']
        })
    return jsonify({'success': False, 'message': 'Failed to create token'})


@admin_api.route("/admin/devtokens/<token_id>", methods=["PATCH"])
def admin_update_devtoken(token_id):
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    data = _json_body()
    if data and data.get('revoked'):
        if revoke_dev_token(token_id):
            return jsonify({'success': True})
        return jsonify({'success': False, 'message': 'Token not found'})

    return jsonify({'success': False, 'message': 'No valid fields to update'})


@admin_api.route("/admin/devtokens/<token_id>", methods=["DELETE"])
def admin_delete_devtoken(token_id):
    if not check_admin_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    tokens = load_dev_tokens()
    if token_id not in tokens:
        return jsonify({'success': False, 'message': 'Token not found'})

    del tokens[token_id]
    save_dev_tokens(tokens, force=True)
    return jsonify({'success': True})
