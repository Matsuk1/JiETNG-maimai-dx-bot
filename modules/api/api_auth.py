"""Authentication and user-permission decorators for the developer API."""

import logging
from functools import wraps

from flask import jsonify, request

from modules.devtoken_manager import load_dev_tokens, verify_dev_token
from modules.import_token_manager import verify_import_token
from modules.user_db import get_user, get_user_field


MAIMAI_SESSION_CORS_ORIGINS = {
    "https://maimaidx.jp",
    "https://maimaidx-eng.com",
    "https://dxrating.net",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
}


def api_error_boundary(view=None, *, cors=False):
    """Convert unexpected endpoint failures to the shared JSON contract."""
    if view is None:
        return lambda function: api_error_boundary(function, cors=cors)
    logger = logging.getLogger(view.__module__)

    @wraps(view)
    def decorated(*args, **kwargs):
        try:
            return view(*args, **kwargs)
        except Exception as exc:
            logger.exception("[API] %s failed: path=%s", view.__name__, request.path)
            return _error("Internal server error", str(exc), 500, cors=cors)
    return decorated


def maimai_session_cors(response):
    origin = request.headers.get("Origin")
    if origin in MAIMAI_SESSION_CORS_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Vary"] = "Origin"
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response


def _error(error, message, status, *, cors=False):
    response = jsonify({"error": error, "message": message})
    return (maimai_session_cors(response) if cors else response), status


def _bearer_token(*, cors=False):
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None, _error(
            "No authorization header",
            "Authorization header is required",
            401,
            cors=cors,
        )

    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None, _error(
            "Invalid authorization header",
            "Authorization header must be in format: Bearer <token>",
            401,
            cors=cors,
        )
    return parts[1], None


def require_dev_token(view):
    @wraps(view)
    def decorated(*args, **kwargs):
        token, error = _bearer_token()
        if error:
            return error

        token_info = verify_dev_token(token)
        if not token_info:
            return _error("Invalid token", "Token is invalid or has been revoked", 401)

        request.token_info = token_info
        return view(*args, **kwargs)

    return decorated


def require_import_token(view):
    @wraps(view)
    def decorated(*args, **kwargs):
        if request.method == "OPTIONS":
            return view(*args, **kwargs)

        token, error = _bearer_token(cors=True)
        if error:
            return error

        token_info = verify_import_token(token)
        if not token_info:
            return _error(
                "Invalid token",
                "Import token is invalid or has been revoked",
                401,
                cors=True,
            )

        request.import_token_info = token_info
        return view(*args, **kwargs)

    return decorated


def check_user_permission(user_id, token_id):
    user_data = get_user(user_id)
    if not user_data:
        return False, _error(
            "User not found",
            f"User {user_id} does not exist",
            404,
        )

    if user_data.get("registered_via_token") == token_id:
        return True, user_data

    allowed_users = load_dev_tokens().get(token_id, {}).get("allowed_users", [])
    if user_id in allowed_users:
        return True, user_data

    return False, _error(
        "Permission denied",
        f"Token does not have permission to access user {user_id}",
        403,
    )


def require_user_permission(view):
    @wraps(view)
    def decorated(*args, **kwargs):
        user_id = kwargs.get("user_id")
        if not user_id:
            return _error("Missing parameter", "user_id is required", 400)

        allowed, result = check_user_permission(user_id, request.token_info["token_id"])
        return view(*args, **kwargs) if allowed else result

    return decorated


def require_owner_permission(view):
    @wraps(view)
    def decorated(*args, **kwargs):
        user_id = kwargs.get("user_id")
        if not user_id:
            return _error("Missing parameter", "user_id is required", 400)

        owner_token = get_user_field(user_id, "registered_via_token")
        if owner_token is None:
            return _error("User not found", f"User {user_id} does not exist", 404)
        if owner_token != request.token_info["token_id"]:
            return _error(
                "Forbidden",
                "Only the owner token (creator) can perform this operation",
                403,
            )
        return view(*args, **kwargs)

    return decorated
