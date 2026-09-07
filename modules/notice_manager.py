import json
import os
import threading
from datetime import datetime

from modules.config_loader import NOTICE_FILE
from modules.i18n import language_codes


_notice_lock = threading.RLock()
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"


def _normalize_content(content):
    if isinstance(content, str):
        return {language: content for language in language_codes()}
    if not isinstance(content, dict):
        raise ValueError("Content must be a string or dict")

    fallback = next((value for value in content.values() if value), "")
    if not fallback:
        raise ValueError("At least one language content is required")
    return {language: content.get(language) or fallback for language in language_codes()}


def _normalize_notice(notice, index):
    changed = False
    defaults = {
        "id": f"migrated_{index}_{datetime.now():%Y%m%d%H%M%S}",
        "status": "published",
        "voting_enabled": False,
        "created_by": "system",
        "updated_at": notice.get("date") or datetime.now().strftime(TIMESTAMP_FORMAT),
    }
    for key, value in defaults.items():
        if key not in notice:
            notice[key] = value
            changed = True

    normalized_content = _normalize_content(notice.get("content", ""))
    if notice.get("content") != normalized_content:
        notice["content"] = normalized_content
        changed = True
    return changed


def _read_notices():
    if not os.path.exists(NOTICE_FILE):
        return []
    with open(NOTICE_FILE, encoding="utf-8") as file:
        data = json.load(file)
    notices = data.get("notices", []) if isinstance(data, dict) else []
    return notices if isinstance(notices, list) else []


def _save_notices(notices):
    directory = os.path.dirname(NOTICE_FILE)
    if directory:
        os.makedirs(directory, exist_ok=True)
    temporary_file = f"{NOTICE_FILE}.tmp"
    with open(temporary_file, "w", encoding="utf-8") as file:
        json.dump({"notices": notices}, file, ensure_ascii=False, indent=2)
    os.replace(temporary_file, NOTICE_FILE)


def _load_notices():
    with _notice_lock:
        notices = _read_notices()
        changed = False
        for index, notice in enumerate(notices):
            changed = _normalize_notice(notice, index) or changed
        if changed:
            _save_notices(notices)
        return notices


def _generate_unique_id(notices):
    base = datetime.now().strftime("%Y%m%d%H%M%S")
    existing_ids = {notice.get("id") for notice in notices}
    notice_id = base
    counter = 1
    while notice_id in existing_ids:
        notice_id = f"{base}_{counter}"
        counter += 1
    return notice_id


def _build_button(button_type, button_label, button_value):
    if button_type and button_label and button_value:
        return {"type": button_type, "label": button_label, "value": button_value}
    return None


def upload_notice(
    content,
    date=None,
    status="published",
    voting_enabled=False,
    created_by="system",
    button_type=None,
    button_label=None,
    button_value=None,
):
    with _notice_lock:
        notices = _load_notices()
        notice_id = _generate_unique_id(notices)
        timestamp = datetime.now().strftime(TIMESTAMP_FORMAT)
        notice = {
            "id": notice_id,
            "content": _normalize_content(content),
            "date": date or timestamp,
            "status": status,
            "voting_enabled": voting_enabled,
            "created_by": created_by,
            "updated_at": timestamp,
        }
        button = _build_button(button_type, button_label, button_value)
        if button:
            notice["button"] = button
        notices.insert(0, notice)
        _save_notices(notices)
        return notice_id


def get_latest_published_notice():
    return next(
        (notice for notice in _load_notices() if notice.get("status") == "published"),
        None,
    )


def get_all_notices(include_drafts=False):
    notices = _load_notices()
    if include_drafts:
        return notices
    return [notice for notice in notices if notice.get("status") == "published"]


def get_notice_by_id(notice_id):
    return next(
        (notice for notice in _load_notices() if notice.get("id") == notice_id), None
    )


def update_notice(
    notice_id,
    content,
    status=None,
    voting_enabled=None,
    button_type=None,
    button_label=None,
    button_value=None,
    remove_button=False,
):
    with _notice_lock:
        notices = _load_notices()
        notice = next((item for item in notices if item.get("id") == notice_id), None)
        if not notice:
            return False

        notice["content"] = _normalize_content(content)
        if status in {"draft", "published"}:
            notice["status"] = status
        if voting_enabled is not None:
            notice["voting_enabled"] = bool(voting_enabled)
        notice["updated_at"] = datetime.now().strftime(TIMESTAMP_FORMAT)
        if remove_button:
            notice.pop("button", None)
        else:
            button = _build_button(button_type, button_label, button_value)
            if button:
                notice["button"] = button
        _save_notices(notices)
        return True


def publish_notice(notice_id):
    with _notice_lock:
        notices = _load_notices()
        notice = next((item for item in notices if item.get("id") == notice_id), None)
        if not notice or notice.get("status") != "draft":
            return False
        notice.update(status="published", updated_at=datetime.now().strftime(TIMESTAMP_FORMAT))
        _save_notices(notices)
        return True


def delete_notice(notice_id):
    with _notice_lock:
        notices = _load_notices()
        remaining = [notice for notice in notices if notice.get("id") != notice_id]
        if len(remaining) == len(notices):
            return False
        _save_notices(remaining)
        return True
