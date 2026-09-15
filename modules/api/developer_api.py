import asyncio
import json
import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from flask import Blueprint, Response, jsonify, request, stream_with_context

from modules.api.api_auth import (
    require_dev_token,
    require_owner_permission,
    require_user_permission,
)
from modules.bindtoken_manager import generate_bind_token, generate_settings_token
from modules.config_loader import DOMAIN
from modules.devtoken_manager import load_dev_tokens, save_dev_tokens
from modules.event_tracker import track_event
from modules.i18n import DEFAULT_LANGUAGE, normalize_language
from modules.line_messenger import smart_push
from modules.perm_request_generator import generate_perm_request_message
from modules.perm_request_handler import (
    accept_perm_request,
    get_pending_perm_requests,
    reject_perm_request,
    send_perm_request,
)
from modules.task_runtime import check_rate_limit
from modules.rich_menu_manager import link_bound_rich_menu, link_unbound_rich_menu
from modules.user_db import get_all_user_ids, get_user, get_user_field, user_exists
from modules.user_manager import add_user, delete_user, edit_user_value


logger = logging.getLogger(__name__)
developer_api = Blueprint("developer_api", __name__)
SYNC_LOCK_TTL_SECONDS = 600
_sync_locks = {}
_sync_locks_guard = threading.Lock()


@dataclass(frozen=True)
class DeveloperApiServices:
    configuration: object
    nickname: Callable
    process_credentials: Callable
    sync_user_data: Callable
    sync_timeout: int


_services: DeveloperApiServices | None = None


def configure_developer_api(*, configuration, nickname, process_credentials, sync_user_data, sync_timeout):
    global _services
    _services = DeveloperApiServices(configuration, nickname, process_credentials, sync_user_data, sync_timeout)


@developer_api.route("/api/v2/users", methods=["GET"])
@developer_api.route("/api/v1/users", methods=["GET"])
@require_dev_token
def api_list_users():
    try:
        token_info = request.token_info
        token_id = token_info['token_id']

        dev_tokens = load_dev_tokens()
        allowed_users = dev_tokens.get(token_id, {}).get('allowed_users', [])

        users_list = []
        for user_id in get_all_user_ids():
            has_access = False
            access_type = None

            if get_user_field(user_id, 'registered_via_token') == token_id:
                has_access = True
                access_type = "owner"
            elif user_id in allowed_users:
                has_access = True
                access_type = "granted"

            if has_access:
                nickname = _services.nickname(user_id, use_cache=True)
                users_list.append({
                    "user_id": user_id,
                    "nickname": nickname,
                    "access_type": access_type
                })

        logger.debug(f"[API] List users: token_id={token_id}, note={token_info['note']}, count={len(users_list)}")

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


@developer_api.route("/api/v2/users", methods=["POST"])
@developer_api.route("/api/v1/users", methods=["POST"])
@require_dev_token
def api_create_user():
    user_id = ''
    try:
        data = request.form.to_dict() or request.get_json(force=True, silent=True) or {}
        user_id = data.get('user_id', '')
        nickname = data.get('nickname', '')

        if not user_id:
            return jsonify({
                "error": "Missing parameter",
                "message": "Parameter 'user_id' is required"
            }), 400

        if not nickname:
            return jsonify({
                "error": "Missing parameter",
                "message": "Parameter 'nickname' is required"
            }), 400

        token_info = request.token_info
        logger.info(f"[API] Create user: user_id={user_id}, nickname={nickname}, token_id={token_info['token_id']}, note={token_info['note']}")

        if user_exists(user_id):
            return jsonify({
                "error": "User already exists",
                "message": f"User {user_id} was created already."
            }), 409

        bind_token = generate_bind_token(user_id)

        bind_url = f"https://{DOMAIN}/linebot/sega_bind?token={bind_token}"

        add_user(user_id)
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
            "message": "Bind URL generated successfully."
        }), 201

    except Exception as e:
        logger.error(f"[API] ✗ Create user error: user_id={user_id}, error={e}", exc_info=True)
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500


@developer_api.route("/api/v2/users/<user_id>", methods=["GET"])
@developer_api.route("/api/v1/users/<user_id>", methods=["GET"])
@require_dev_token
@require_user_permission
def api_get_user(user_id):
    try:
        user_data = get_user(user_id)
        if not user_data:
            return jsonify({"error": "User not found"}), 404

        nickname = _services.nickname(user_id, use_cache=True)

        token_info = request.token_info
        logger.debug(f"[API] Get user: user_id={user_id}, token_id={token_info['token_id']}, note={token_info['note']}")

        sensitive_keys = {'sega_id', 'sega_pwd', 'perm_requests', 'registered_via_token'}
        safe_data = {k: v for k, v in user_data.items() if k not in sensitive_keys}

        return jsonify({
            "success": True,
            "user_id": user_id,
            "nickname": nickname,
            "data": safe_data
        })

    except Exception as e:
        logger.error(f"[API] ✗ Get user error: user_id={user_id}, error={e}", exc_info=True)
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500


@developer_api.route("/api/v2/users/<user_id>", methods=["DELETE"])
@developer_api.route("/api/v1/users/<user_id>", methods=["DELETE"])
@require_dev_token
@require_owner_permission
def api_delete_user(user_id):
    try:
        nickname = _services.nickname(user_id, use_cache=True)

        delete_user(user_id)
        link_unbound_rich_menu(user_id)

        token_info = request.token_info
        logger.info(f"[API] Delete user: user_id={user_id}, nickname={nickname}, token_id={token_info['token_id']}, note={token_info['note']}")
        track_event('user_unbind', user_id=user_id, metadata={'token_id': token_info['token_id']})

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


@developer_api.route("/api/v2/users/<user_id>/bind-url", methods=["GET"])
@developer_api.route("/api/v1/users/<user_id>/bind-url", methods=["GET"])
@require_dev_token
@require_user_permission
def api_create_bind_url(user_id):
    try:
        token_info = request.token_info
        logger.info(f"[API] Create bind URL: user_id={user_id}, token_id={token_info['token_id']}, note={token_info['note']}")

        bind_token = generate_bind_token(user_id)
        bind_url = f"https://{DOMAIN}/linebot/sega_bind?token={bind_token}"

        return jsonify({
            "success": True,
            "user_id": user_id,
            "bind_url": bind_url,
            "expires_in": 120,
            "message": "Bind URL generated successfully."
        }), 201

    except Exception as e:
        logger.error(f"[API] ✗ Create bind URL error: user_id={user_id}, error={e}", exc_info=True)
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500


@developer_api.route("/api/v2/users/<user_id>/rebind-url", methods=["GET"])
@developer_api.route("/api/v1/users/<user_id>/rebind-url", methods=["GET"])
@require_dev_token
@require_user_permission
def api_create_rebind_url(user_id):
    try:
        token_info = request.token_info
        logger.info(f"[API] Create rebind URL: user_id={user_id}, token_id={token_info['token_id']}, note={token_info['note']}")

        rebind_token = generate_bind_token(user_id)
        rebind_url = f"https://{DOMAIN}/linebot/sega_bind?token={rebind_token}&mode=rebind"

        return jsonify({
            "success": True,
            "user_id": user_id,
            "rebind_url": rebind_url,
            "expires_in": 120,
            "message": "Rebind URL generated successfully."
        }), 201

    except Exception as e:
        logger.error(f"[API] ✗ Create rebind URL error: user_id={user_id}, error={e}", exc_info=True)
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500


@developer_api.route("/api/v2/users/<user_id>/settings-url", methods=["GET"])
@developer_api.route("/api/v1/users/<user_id>/settings-url", methods=["GET"])
@require_dev_token
@require_user_permission
def api_create_settings_url(user_id):
    try:
        token_info = request.token_info
        logger.info(f"[API] Create settings URL: user_id={user_id}, token_id={token_info['token_id']}, note={token_info['note']}")

        settings_token = generate_settings_token(user_id)
        settings_url = f"https://{DOMAIN}/linebot/settings?token={settings_token}"

        return jsonify({
            "success": True,
            "user_id": user_id,
            "settings_url": settings_url,
            "expires_in": 1800,
            "message": "Settings URL generated successfully."
        }), 201

    except Exception as e:
        logger.error(f"[API] ✗ Create settings URL error: user_id={user_id}, error={e}", exc_info=True)
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500


@developer_api.route("/api/v2/users/<user_id>/bind", methods=["POST"])
@require_dev_token
@require_user_permission
def api_bind_user(user_id):
    try:
        token_info = request.token_info
        data = request.form.to_dict() or request.get_json(force=True, silent=True) or {}

        sega_id = data.get('sega_id', '')
        password = data.get('password', '')
        ver = data.get('ver', 'jp').strip().lower()
        aime = data.get('aime', '0')
        timezone = data.get('timezone', '9')
        language = normalize_language(data.get('language'), DEFAULT_LANGUAGE)

        if not sega_id:
            return jsonify({"error": "Missing parameter", "message": "Parameter 'sega_id' is required"}), 400
        if not password:
            return jsonify({"error": "Missing parameter", "message": "Parameter 'password' is required"}), 400
        if ver not in ('jp', 'intl'):
            return jsonify({"error": "Invalid parameter", "message": "Parameter 'ver' must be jp or intl"}), 400
        try:
            timezone_int = int(timezone)
        except (ValueError, TypeError):
            timezone_int = 9
        try:
            aime_int = int(aime)
        except (ValueError, TypeError):
            aime_int = 0

        user_data = get_user(user_id) or {}
        has_account = all(key in user_data for key in ['sega_id', 'sega_pwd', 'version'])
        if has_account:
            return jsonify({"error": "Already bound", "message": "User already has a SEGA account linked. Use PUT to rebind."}), 409

        result = asyncio.run(_services.process_credentials(user_id, sega_id, password, ver, language, timezone_int, aime_int, False))
        if result == "MAINTENANCE":
            return jsonify({"error": "Maintenance", "message": "The official website is under maintenance. Please try again later."}), 503
        elif result:
            track_event('user_bind', user_id=user_id, metadata={'version': ver, 'via_token': True})
            link_bound_rich_menu(user_id, get_user(user_id))
            logger.info(f"[API] ✓ Bind success: user_id={user_id}, ver={ver}, token_id={token_info['token_id']}")
            return jsonify({"success": True, "user_id": user_id, "message": "SEGA account bound successfully."})
        else:
            return jsonify({"error": "Authentication failed", "message": "Invalid SEGA ID or password."}), 401

    except Exception as e:
        logger.error(f"[API] ✗ Bind error: user_id={user_id}, error={e}", exc_info=True)
        return jsonify({"error": "Internal server error", "message": str(e)}), 500


@developer_api.route("/api/v2/users/<user_id>/bind", methods=["PUT"])
@require_dev_token
@require_user_permission
def api_rebind_user(user_id):
    try:
        token_info = request.token_info
        data = request.form.to_dict() or request.get_json(force=True, silent=True) or {}

        user_data = get_user(user_id) or {}
        has_account = all(key in user_data for key in ['sega_id', 'sega_pwd', 'version'])
        if not has_account:
            return jsonify({"error": "Not bound", "message": "User has no SEGA account linked. Use POST to bind first."}), 404

        sega_id = data.get('sega_id', '') or user_data.get('sega_id', '')
        password = data.get('password', '') or user_data.get('sega_pwd', '')

        ver = data.get('ver', user_data.get('version', 'jp')).strip().lower()
        aime = data.get('aime', str(user_data.get('aime', 0)))
        language = normalize_language(user_data.get('language'), DEFAULT_LANGUAGE)
        timezone_int = user_data.get('timezone', 9)

        if ver not in ('jp', 'intl'):
            return jsonify({"error": "Invalid parameter", "message": "Parameter 'ver' must be jp or intl"}), 400

        try:
            aime_int = int(aime)
        except (ValueError, TypeError):
            aime_int = user_data.get('aime', 0)

        result = asyncio.run(_services.process_credentials(user_id, sega_id, password, ver, language, timezone_int, aime_int, True))
        if result == "MAINTENANCE":
            return jsonify({"error": "Maintenance", "message": "The official website is under maintenance. Please try again later."}), 503
        elif result:
            track_event('user_rebind', user_id=user_id, metadata={'version': ver, 'via_token': True})
            logger.info(f"[API] ✓ Rebind success: user_id={user_id}, ver={ver}, token_id={token_info['token_id']}")
            return jsonify({"success": True, "user_id": user_id, "message": "SEGA account rebound successfully."})
        else:
            return jsonify({"error": "Authentication failed", "message": "Invalid SEGA ID or password."}), 401

    except Exception as e:
        logger.error(f"[API] ✗ Rebind error: user_id={user_id}, error={e}", exc_info=True)
        return jsonify({"error": "Internal server error", "message": str(e)}), 500


def _get_api_sync_lock(user_id):
    now = time.monotonic()
    with _sync_locks_guard:
        _cleanup_sync_locks_locked(now)
        entry = _sync_locks.get(user_id)
        if entry is None:
            entry = {
                "lock": threading.Lock(),
                "last_used": now,
            }
            _sync_locks[user_id] = entry
        else:
            entry["last_used"] = now
        return entry["lock"]


def _mark_api_sync_lock_released(user_id, lock):
    now = time.monotonic()
    with _sync_locks_guard:
        entry = _sync_locks.get(user_id)
        if entry and entry.get("lock") is lock:
            entry["last_used"] = now


def _cleanup_sync_locks_locked(now=None):
    now = now or time.monotonic()
    stale_user_ids = [
        locked_user_id
        for locked_user_id, entry in _sync_locks.items()
        if now - entry.get("last_used", now) >= SYNC_LOCK_TTL_SECONDS
        and not entry.get("lock").locked()
    ]
    for locked_user_id in stale_user_ids:
        _sync_locks.pop(locked_user_id, None)
    return len(stale_user_ids)


def cleanup_api_sync_locks():
    with _sync_locks_guard:
        return _cleanup_sync_locks_locked()


def _api_sync_result_payload(result):
    status_code = int(result.get("status_code") or (200 if result.get("success") else 500))
    payload = {
        "success": bool(result.get("success")),
        "user_id": result.get("user_id"),
        "version": result.get("version"),
        "username": result.get("username"),
        "rating": result.get("rating"),
        "last_update": result.get("last_update"),
        "elapsed_time": result.get("elapsed_time"),
        "func_status": result.get("func_status"),
        "best_count": result.get("best_count", 0),
        "recent_count": result.get("recent_count", 0),
        "message": result.get("message"),
    }
    if not result.get("success"):
        payload["error"] = result.get("error") or "Sync failed"
    return payload, status_code


def _run_api_sync(user_id, ver):
    return asyncio.run(asyncio.wait_for(
        _services.sync_user_data(user_id, ver),
        timeout=_services.sync_timeout,
    ))


def _get_sync_version(user_id):
    user_data = get_user(user_id) or {}
    return user_data.get("version", "jp")


@developer_api.route("/api/v2/users/<user_id>/sync/stream", methods=["POST"])
@require_dev_token
@require_user_permission
def api_sync_user_data_stream(user_id):
    if check_rate_limit(user_id, "api_sync_user_data_stream"):
        return jsonify({"error": "Rate limited", "message": "Too many sync requests. Please retry later."}), 429

    token_info = request.token_info
    ver = _get_sync_version(user_id)
    lock = _get_api_sync_lock(user_id)
    track_event(
        "sync_cmd",
        user_id=user_id,
        metadata={"command": "sync-stream", "source": "api"},
    )

    def write_event(event, **payload):
        payload["event"] = event
        payload.setdefault("user_id", user_id)
        return json.dumps(payload, ensure_ascii=False) + "\n"

    @stream_with_context
    def generate():
        if not lock.acquire(blocking=False):
            yield write_event("failed", success=False, error="Sync already running", message=f"User {user_id} is already syncing")
            return

        try:
            start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            yield write_event("accepted", success=True, version=ver, started_at=start_time, message="Sync started.")
            logger.info(
                "[API] Stream sync started: user_id=%s, token_id=%s",
                user_id, token_info["token_id"],
            )
            result = _run_api_sync(user_id, ver)
            payload, _ = _api_sync_result_payload(result)
            track_event("sync_task", user_id=user_id, metadata={
                "success": bool(payload.get("success")),
                "trigger": "api",
                "version": ver,
                "elapsed_time": payload.get("elapsed_time"),
                "error": payload.get("error"),
            })
            event = "completed" if payload.get("success") else "failed"
            yield write_event(event, **payload)
            logger.info(
                "[API] Stream sync finished: user_id=%s, success=%s, token_id=%s",
                user_id, payload.get("success"), token_info["token_id"],
            )
        except asyncio.TimeoutError:
            track_event("sync_task", user_id=user_id, metadata={
                "success": False,
                "trigger": "api",
                "version": ver,
                "error": "Timeout",
            })
            logger.warning("[API] Stream sync timeout: user_id=%s", user_id)
            yield write_event("failed", success=False, error="Timeout", message=f"Sync exceeded {_services.sync_timeout}s")
        except Exception as exc:
            track_event("sync_task", user_id=user_id, metadata={
                "success": False,
                "trigger": "api",
                "version": ver,
                "error": str(exc)[:200],
            })
            logger.exception("[API] Stream sync failed: user_id=%s", user_id)
            yield write_event("failed", success=False, error="Internal server error", message=str(exc))
        finally:
            lock.release()
            _mark_api_sync_lock_released(user_id, lock)

    return Response(generate(), mimetype="application/x-ndjson")


# ==================== Permission Management APIs (RESTful) ====================

@developer_api.route("/api/v2/users/<user_id>/permissions", methods=["POST"])
@developer_api.route("/api/v1/users/<user_id>/permissions", methods=["POST"])
@require_dev_token
def api_request_user_permission(user_id):
    try:
        data = request.form.to_dict() or request.get_json(force=True, silent=True) or {}
        requester_name = data.get('requester_name', '')

        token_info = request.token_info
        token_id = token_info['token_id']

        if not requester_name:
            requester_name = token_info.get('note', token_id)

        logger.info(f"[API] Request permission: target_user_id={user_id}, token_id={token_id}, note={token_info['note']}")

        result = send_perm_request(token_id, user_id, requester_name)

        if result['success']:
            try:
                perm_requests = get_pending_perm_requests(user_id)
                perm_msg = generate_perm_request_message(perm_requests, user_id)
                if perm_msg:
                    smart_push(user_id, [perm_msg], _services.configuration)
            except Exception as e:
                logger.warning(f"[API] ⚠ Failed to push permission request notification: user_id={user_id}, error={e}")

            return jsonify({
                "success": True,
                "request_id": result['request_id'],
                "user_id": user_id,
                "message": result['message']
            }), 201  # 201 Created for new permission request

        else:
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


@developer_api.route("/api/v2/users/<user_id>/permissions/requests", methods=["GET"])
@developer_api.route("/api/v1/users/<user_id>/permissions/requests", methods=["GET"])
@require_dev_token
@require_owner_permission
def api_get_user_permission_requests(user_id):
    try:
        requests = get_pending_perm_requests(user_id)

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


@developer_api.route("/api/v1/users/<user_id>/permissions/requests/<request_id>", methods=["PATCH"])
@developer_api.route("/api/v2/users/<user_id>/permissions/requests/<request_id>", methods=["PATCH"])
@require_dev_token
@require_owner_permission
def api_manage_user_permission(user_id, request_id):
    action = ""
    try:
        data = request.form.to_dict() or request.get_json(force=True, silent=True) or {}
        action = data.get('action', '')

        if action not in ("accept", "reject"):
            return jsonify({
                "error": "Invalid parameter",
                "message": "Parameter 'action' must be 'accept' or 'reject'"
            }), 400

        token_info = request.token_info
        logger.info(f"[API] Manage permission: action={action}, request_id={request_id}, user_id={user_id}, token_id={token_info['token_id']}, note={token_info['note']}")

        handler = accept_perm_request if action == "accept" else reject_perm_request
        result = handler(user_id, request_id)
        if result["success"]:
            return jsonify({
                "success": True,
                "user_id": user_id,
                "token_id": result["token_id"],
                "token_note": result["token_note"],
                "message": result["message"],
            })

        status_code = 404 if result['error'] in ["User not found", "Request not found", "Invalid token"] else 400
        return jsonify({
            "error": result['error'],
            "message": result['message']
        }), status_code

    except Exception as e:
        logger.error(f"[API] ✗ Manage permission error: user_id={user_id}, request_id={request_id}, action={action}, error={e}", exc_info=True)
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500


@developer_api.route("/api/v1/users/<user_id>/permissions/self", methods=["DELETE"])
@developer_api.route("/api/v2/users/<user_id>/permissions/self", methods=["DELETE"])
@require_dev_token
def api_revoke_own_permission(user_id):
    try:
        _udata = get_user(user_id)
        if not _udata:
            return jsonify({"error": "User not found", "message": f"User {user_id} does not exist"}), 404

        token_info = request.token_info
        token_id = token_info['token_id']

        if _udata.get('registered_via_token') == token_id:
            return jsonify({"error": "Forbidden", "message": "Owner permission cannot be self-revoked"}), 403

        dev_tokens = load_dev_tokens()
        allowed_users = dev_tokens.get(token_id, {}).get('allowed_users', [])
        if user_id not in allowed_users:
            return jsonify({"error": "Permission not found", "message": f"Token does not have granted permission for user {user_id}"}), 404

        allowed_users.remove(user_id)
        dev_tokens[token_id]['allowed_users'] = allowed_users
        save_dev_tokens(dev_tokens)

        logger.info(f"[API] Self-revoke permission: token_id={token_id}, user_id={user_id}")
        return jsonify({"success": True, "user_id": user_id, "message": "Permission revoked"})

    except Exception as e:
        logger.error(f"[API] ✗ Self-revoke permission error: user_id={user_id}, error={e}", exc_info=True)
        return jsonify({"error": "Internal server error", "message": str(e)}), 500


@developer_api.route("/api/v1/users/<user_id>/permissions/<token_id>", methods=["DELETE"])
@developer_api.route("/api/v2/users/<user_id>/permissions/<token_id>", methods=["DELETE"])
@require_dev_token
@require_owner_permission
def api_revoke_user_permission(user_id, token_id):
    try:
        token_info = request.token_info
        logger.info(f"[API] Revoke permission: target_token_id={token_id}, user_id={user_id}, token_id={token_info['token_id']}, note={token_info['note']}")

        dev_tokens = load_dev_tokens()

        if token_id not in dev_tokens:
            return jsonify({
                "error": "Token not found",
                "message": f"Token {token_id} does not exist"
            }), 404

        allowed_users = dev_tokens[token_id].get('allowed_users', [])
        if user_id in allowed_users:
            allowed_users.remove(user_id)
            dev_tokens[token_id]['allowed_users'] = allowed_users
            save_dev_tokens(dev_tokens)

            return jsonify({
                "success": True,
                "user_id": user_id,
                "token_id": token_id,
                "message": f"Permission revoked for token {token_id}"
            })
        else:
            return jsonify({
                "error": "Permission not found",
                "message": f"Token {token_id} does not have permission to access user {user_id}"
            }), 404

    except Exception as e:
        logger.error(f"[API] ✗ Revoke permission error: user_id={user_id}, target_token_id={token_id}, error={e}", exc_info=True)
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500
