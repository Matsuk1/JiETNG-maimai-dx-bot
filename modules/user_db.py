"""MySQL-backed storage for JiETNG user documents."""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from modules.dbpool_manager import database_cursor

logger = logging.getLogger(__name__)


def _decode_json(value: Any) -> Any:
    return json.loads(value) if isinstance(value, str) else value


def _encode_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def init_users_table() -> None:
    """Create the users table when it does not already exist."""
    try:
        with database_cursor(write=True) as (_, cursor):
            cursor.execute("SHOW TABLES LIKE 'users'")
            if cursor.fetchone():
                logger.info("[UserDB] users table ready")
                return
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id VARCHAR(64) PRIMARY KEY,
                    data JSON NOT NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                        ON UPDATE CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)
            logger.info("[UserDB] users table created")
    except Exception:
        logger.exception("[UserDB] Failed to initialize users table")


def load_all_users() -> dict:
    """Load all users as a ``{user_id: data}`` mapping."""
    try:
        with database_cursor() as (_, cursor):
            cursor.execute("SELECT user_id, data FROM users")
            users = {user_id: _decode_json(data) for user_id, data in cursor.fetchall()}
        logger.info("[UserDB] Loaded %s users", len(users))
        return users
    except Exception:
        logger.exception("[UserDB] Failed to load users")
        raise


def _save_user(cursor: Any, user_id: str, user_data: dict) -> None:
    data_json = _encode_json(user_data)
    cursor.execute(
        "INSERT INTO users (user_id, data) VALUES (%s, %s) "
        "ON DUPLICATE KEY UPDATE data = %s, updated_at = CURRENT_TIMESTAMP",
        (user_id, data_json, data_json),
    )


def save_user(
    user_id: str,
    user_data: dict,
    *,
    cursor: Any = None,
    raise_on_error: bool = False,
) -> bool:
    """Insert or replace one user document, optionally within an existing transaction."""
    try:
        if cursor is not None:
            _save_user(cursor, user_id, user_data)
        else:
            with database_cursor(write=True) as (_, own_cursor):
                _save_user(own_cursor, user_id, user_data)
        return True
    except Exception:
        if raise_on_error:
            raise
        logger.exception("[UserDB] Failed to save user: user_id=%s", user_id)
        return False


def update_user_fields(user_id: str, fields: dict) -> bool:
    """Atomically replace supplied top-level fields, preserving concurrent edits."""
    if not isinstance(fields, dict) or not fields:
        raise ValueError("At least one user field is required")
    arguments = []
    for field, value in fields.items():
        # Quoted JSON path members keep dots and quotes inside literal keys.
        arguments.extend(("$." + json.dumps(field, ensure_ascii=False), _encode_json(value)))
    pairs = ", ".join("%s, CAST(%s AS JSON)" for _ in fields)
    try:
        with database_cursor(write=True) as (_, cursor):
            cursor.execute(
                f"UPDATE users SET data = JSON_SET(data, {pairs}), "
                "updated_at = CURRENT_TIMESTAMP WHERE user_id = %s",
                (*arguments, user_id),
            )
            if cursor.rowcount:
                return True
            # An unchanged document can report zero affected rows.
            cursor.execute("SELECT 1 FROM users WHERE user_id = %s", (user_id,))
            return cursor.fetchone() is not None
    except Exception:
        logger.exception("[UserDB] Failed to update user fields: user_id=%s", user_id)
        return False


def create_user_if_missing(user_id: str, user_data: dict) -> bool:
    """Insert a user without replacing an existing document."""
    try:
        with database_cursor(write=True) as (_, cursor):
            cursor.execute(
                "INSERT IGNORE INTO users (user_id, data) VALUES (%s, %s)",
                (user_id, _encode_json(user_data)),
            )
            return cursor.rowcount > 0
    except Exception:
        logger.exception("[UserDB] Failed to create user: user_id=%s", user_id)
        return False


def delete_user_from_db(user_id: str) -> None:
    """Delete one user document."""
    try:
        with database_cursor(write=True) as (_, cursor):
            cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
    except Exception:
        logger.exception("[UserDB] Failed to delete user: user_id=%s", user_id)


def increment_user_field(user_id: str, field: str, delta: Any) -> None:
    """Atomically increment a numeric JSON field."""
    path = f"$.{field}"
    try:
        with database_cursor(write=True) as (_, cursor):
            cursor.execute(
                "UPDATE users SET data = JSON_SET(data, %s, "
                "COALESCE(JSON_EXTRACT(data, %s), 0) + %s), "
                "updated_at = CURRENT_TIMESTAMP WHERE user_id = %s",
                (path, path, delta, user_id),
            )
    except Exception:
        logger.exception(
            "[UserDB] Failed to increment field: user_id=%s field=%s",
            user_id,
            field,
        )


def get_user(user_id: str) -> Optional[dict]:
    """Return one complete user document, or ``None`` when absent or unavailable."""
    try:
        with database_cursor() as (_, cursor):
            cursor.execute("SELECT data FROM users WHERE user_id = %s", (user_id,))
            row = cursor.fetchone()
        return _decode_json(row[0]) if row is not None else None
    except Exception:
        logger.exception("[UserDB] Failed to get user: user_id=%s", user_id)
        return None


def user_exists(user_id: str) -> bool:
    """Return whether a user row exists."""
    try:
        with database_cursor() as (_, cursor):
            cursor.execute("SELECT 1 FROM users WHERE user_id = %s", (user_id,))
            return cursor.fetchone() is not None
    except Exception:
        logger.exception("[UserDB] Failed to check user: user_id=%s", user_id)
        return False


def get_user_field(user_id: str, field: str, default: Any = None) -> Any:
    """Read one top-level JSON field from a user document."""
    try:
        with database_cursor() as (_, cursor):
            cursor.execute(
                "SELECT JSON_EXTRACT(data, %s) FROM users WHERE user_id = %s",
                (f"$.{field}", user_id),
            )
            row = cursor.fetchone()
        if row is None or row[0] is None:
            return default
        try:
            return _decode_json(row[0])
        except (json.JSONDecodeError, ValueError):
            return row[0]
    except Exception:
        logger.exception(
            "[UserDB] Failed to get field: user_id=%s field=%s",
            user_id,
            field,
        )
        return default


def update_user_field(user_id: str, field: str, value: Any) -> None:
    """Set one top-level JSON field."""
    try:
        with database_cursor(write=True) as (_, cursor):
            cursor.execute(
                "UPDATE users SET data = JSON_SET(data, %s, CAST(%s AS JSON)), "
                "updated_at = CURRENT_TIMESTAMP WHERE user_id = %s",
                (f"$.{field}", _encode_json(value), user_id),
            )
    except Exception:
        logger.exception(
            "[UserDB] Failed to update field: user_id=%s field=%s",
            user_id,
            field,
        )


def remove_user_field(user_id: str, field: str) -> None:
    """Remove one top-level JSON field."""
    try:
        with database_cursor(write=True) as (_, cursor):
            cursor.execute(
                "UPDATE users SET data = JSON_REMOVE(data, %s), "
                "updated_at = CURRENT_TIMESTAMP WHERE user_id = %s",
                (f"$.{field}", user_id),
            )
    except Exception:
        logger.exception(
            "[UserDB] Failed to remove field: user_id=%s field=%s",
            user_id,
            field,
        )


def get_all_user_ids() -> list[str]:
    """Return all user IDs."""
    try:
        with database_cursor() as (_, cursor):
            cursor.execute("SELECT user_id FROM users")
            return [row[0] for row in cursor.fetchall()]
    except Exception:
        logger.exception("[UserDB] Failed to get user IDs")
        return []
