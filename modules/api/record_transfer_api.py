import logging
from urllib.parse import quote

from flask import Blueprint, Response, current_app, jsonify, request

from modules.api.api_auth import (
    check_user_permission,
    maimai_session_cors,
    require_dev_token,
    require_import_token,
)
from modules.event_tracker import track_event
from modules.export_manager import _build_friendly_name, build_payload, to_json_bytes, to_xml_bytes
from modules.import_manager import ImportValidationError, import_processed_payload
from modules.task_runtime import check_rate_limit


logger = logging.getLogger(__name__)
record_transfer_api = Blueprint("record_transfer_api", __name__)


@record_transfer_api.get("/api/v2/users/<user_id>/export")
@require_dev_token
def export_records(user_id):
    try:
        token = request.token_info
        allowed, user = check_user_permission(user_id, token["token_id"])
        if not allowed:
            return user
        if "personal_info" not in user:
            return jsonify({"error": "User info not found, please sync first"}), 404

        fmt = (request.args.get("fmt", "json") or "json").strip().lower()
        if fmt not in ("json", "xml"):
            return jsonify({"error": "Invalid format", "message": "fmt must be 'json' or 'xml'"}), 400

        payload = build_payload(user_id)
        records = payload.get("records", {}) or {}
        if not records.get("best") and not records.get("recent"):
            return jsonify({"error": "No records to export, please sync first"}), 404

        content = to_json_bytes(payload) if fmt == "json" else to_xml_bytes(payload)
        filename = _build_friendly_name(payload.get("profile"), fmt)
        logger.info(
            "[API] Export generated: user_id=%s, fmt=%s, bytes=%s, token_id=%s",
            user_id, fmt, len(content), token["token_id"],
        )
        track_event("record_export", user_id=user_id, metadata={"format": fmt, "source": "api"})
        return Response(content, mimetype=f"application/{fmt}", headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}",
            "Content-Length": str(len(content)),
        })
    except Exception as exc:
        logger.exception("[API] Export records failed: user_id=%s", user_id)
        return jsonify({"error": "Internal server error", "message": str(exc)}), 500


@record_transfer_api.route("/api/v2/import/records", methods=["POST", "OPTIONS"])
@require_import_token
def import_records():
    if request.method == "OPTIONS":
        return maimai_session_cors(current_app.make_response(("", 204)))

    token = request.import_token_info
    user_id = token["user_id"]
    if check_rate_limit(user_id, "api_import_records"):
        return maimai_session_cors(jsonify({
            "error": "Rate limited",
            "message": "Too many import requests. Please retry later.",
        })), 429

    try:
        result = import_processed_payload(
            user_id,
            request.get_json(force=True, silent=False),
            source=f"import_token:{token.get('token_id')}",
        )
        logger.info(
            "[API] Import records: user_id=%s, token_id=%s, best=%s, recent=%s",
            user_id, token.get("token_id"), result["best_count"], result["recent_count"],
        )
        track_event("record_import", user_id=user_id, metadata={
            "token_id": token.get("token_id"),
            "best_count": result["best_count"],
            "recent_count": result["recent_count"],
            "version": result["version"],
        })
        return maimai_session_cors(jsonify({
            "success": True,
            "user_id": user_id,
            "best_count": result["best_count"],
            "recent_count": result["recent_count"],
            "version": result["version"],
            "message": "Records imported successfully.",
        }))
    except ImportValidationError as exc:
        return maimai_session_cors(jsonify({"error": "Invalid payload", "message": str(exc)})), 400
    except Exception as exc:
        logger.exception("[API] Import records failed: user_id=%s", user_id)
        return maimai_session_cors(jsonify({"error": "Internal server error", "message": str(exc)})), 500
