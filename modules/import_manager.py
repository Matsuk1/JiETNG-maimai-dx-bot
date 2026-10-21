"""
Processed record import helpers.

The public import endpoint accepts the same processed JSON schema produced by
modules.export_manager.build_payload, then converts it back to the small record
shape used by write_record.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from modules.dbpool_manager import database_cursor
from modules.maimai_utils import get_rating_image_path
from modules.record_manager import write_record
from modules.user_db import get_user, save_user

_RANK_TO_ICON = {
    "SSS+": "sssp",
    "SSS": "sss",
    "SS+": "ssp",
    "SS": "ss",
    "S+": "sp",
    "S": "s",
    "AAA": "aaa",
    "AA": "aa",
    "A": "a",
    "BBB": "bbb",
    "BB": "bb",
    "B": "b",
    "C": "c",
    "D": "d",
}

_COMBO_TO_ICON = {"AP+": "app", "AP": "ap", "FC+": "fcp", "FC": "fc"}
_SYNC_TO_ICON = {
    "FDX+": "fdxp",
    "FDX": "fdx",
    "FS+": "fsp",
    "FS": "fs",
    "SYNC": "sync",
    "Sync": "sync",
}
_TYPE_TO_INTERNAL = {
    "DX": "dx",
    "Standard": "std",
    "STD": "std",
    "Utage": "utage",
    "UTAGE": "utage",
}
_DIFF_TO_INTERNAL = {
    "Basic": "basic",
    "Advanced": "advanced",
    "Expert": "expert",
    "Master": "master",
    "Re:Master": "remaster",
    "ReMaster": "remaster",
    "Utage": "utage",
}


class ImportValidationError(ValueError):
    pass


def _score_string(value: Any) -> str:
    if value is None:
        raise ImportValidationError("record achievement is required")
    if isinstance(value, str):
        raw = value.strip()
        if raw.endswith("%"):
            number = float(raw[:-1])
            return f"{number:.4f}%"
        number = float(raw)
        return f"{number:.4f}%"
    return f"{float(value):.4f}%"


def _dx_score_string(record: dict) -> str:
    if record.get("dx_score") is None:
        return "0 / 0"
    if record.get("dx_score_max") is None:
        raw = str(record.get("dx_score", "")).strip()
        return raw if "/" in raw else f"{raw} / 0"
    return f"{int(record.get('dx_score'))} / {int(record.get('dx_score_max'))}"


def _map_value(mapping: dict, value: Any, default: str) -> str:
    if value is None:
        return default
    text = str(value).strip()
    return mapping.get(text, mapping.get(text.upper(), text.lower()))


def _transform_processed_record(record: dict) -> dict:
    if not isinstance(record, dict):
        raise ImportValidationError("each record must be an object")

    title = record.get("title") or record.get("name")
    if not title:
        raise ImportValidationError("record title is required")

    return {
        "name": str(title),
        "difficulty": _map_value(_DIFF_TO_INTERNAL, record.get("difficulty"), "master"),
        "type": _map_value(_TYPE_TO_INTERNAL, record.get("type"), "dx"),
        "score": _score_string(record.get("achievement", record.get("score"))),
        "dx_score": _dx_score_string(record),
        "score_icon": _map_value(_RANK_TO_ICON, record.get("rank"), "d"),
        "combo_icon": _map_value(_COMBO_TO_ICON, record.get("combo"), "back"),
        "sync_icon": _map_value(_SYNC_TO_ICON, record.get("sync"), "back"),
    }


def _transform_profile(profile: dict) -> dict:
    profile = profile or {}
    rating = str(profile.get("rating", "0"))
    try:
        rating_int = int(float(rating))
    except (TypeError, ValueError):
        rating_int = 0
    out = {
        "name": profile.get("name") or "Imported",
        "rating": rating,
        "rating_block_path": get_rating_image_path(rating_int),
        "trophy_content": profile.get("trophy")
        or profile.get("trophy_content")
        or "N/A",
        "trophy_url": profile.get("trophy_url") or "N/A",
        "icon_url": profile.get("icon_url") or "N/A",
        "nameplate_url": profile.get("nameplate_url") or "N/A",
        "class_rank_url": profile.get("class_rank_url") or "N/A",
        "cource_rank_url": profile.get("course_rank_url")
        or profile.get("cource_rank_url")
        or "N/A",
    }
    return {k: v for k, v in out.items() if v is not None}


def import_processed_payload(
    user_id: str, payload: dict, source: str = "api_import"
) -> dict:
    if not isinstance(payload, dict):
        raise ImportValidationError("request body must be a JSON object")

    user_data = get_user(user_id)
    if not user_data:
        raise ImportValidationError("user does not exist")

    records = payload.get("records")
    if not isinstance(records, dict):
        raise ImportValidationError("payload.records is required")

    has_best = "best" in records
    has_recent = "recent" in records
    best_source = records.get("best", [])
    recent_source = records.get("recent", [])
    if not has_best and not has_recent:
        raise ImportValidationError("records.best or records.recent is required")
    if has_best and not isinstance(best_source, list):
        raise ImportValidationError("records.best must be an array")
    if has_recent and not isinstance(recent_source, list):
        raise ImportValidationError("records.recent must be an array")
    if has_best and has_recent and not best_source and not recent_source:
        raise ImportValidationError("payload contains no records")

    best = (
        [_transform_processed_record(item) for item in best_source] if has_best else []
    )
    recent = (
        [_transform_processed_record(item) for item in recent_source]
        if has_recent
        else []
    )

    version = str(
        payload.get("maimai_version")
        or payload.get("version")
        or user_data.get("version")
        or "jp"
    ).lower()
    if version not in ("jp", "intl"):
        version = "jp"

    profile = _transform_profile(payload.get("profile") or {})
    user_data["version"] = version
    user_data["personal_info"] = profile
    user_data["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user_data.setdefault("created_at", user_data["last_update"])
    user_data.setdefault("language", "ja")
    user_data.setdefault("timezone", 9)
    if user_data.get("import_only") or user_data.get("auth_type") == "import_token":
        user_data["auth_type"] = "import_token"
        user_data["import_only"] = True
        user_data.setdefault("import_only_created_at", user_data.get("created_at"))
        user_data["import_only_initialized_at"] = user_data["last_update"]
    user_data["last_import"] = {
        "source": source,
        "imported_at": user_data["last_update"],
        "schema_version": payload.get("schema_version"),
        "profile": profile,
        "best_count": len(best) if has_best else None,
        "recent_count": len(recent) if has_recent else None,
    }
    with database_cursor(write=True) as (_, cursor):
        if has_best:
            write_record(user_id, best, recent=False, cursor=cursor)
        if has_recent:
            write_record(user_id, recent, recent=True, cursor=cursor)
        save_user(user_id, user_data, cursor=cursor, raise_on_error=True)

    return {
        "best_count": len(best) if has_best else None,
        "recent_count": len(recent) if has_recent else None,
        "version": version,
        "profile": profile,
    }
