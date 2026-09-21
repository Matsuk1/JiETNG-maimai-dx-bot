import logging
from datetime import datetime, timedelta
import os

from modules.config_loader import (
    DXDATA_FILE, DXDATA_VERSION_FILE, OVERRIDE_FILE, JP_OVERRIDE_FILE, INTL_OVERRIDE_FILE,
    NOTICE_FILE, TIP_AD_FILE,
    BACKUP_DIR, DEV_TOKENS_FILE, IMG_DIR,
    FONT_FILE, LOGO_FILE, QR_CODE_FILE,
    VERSIONS_DIR, COVERS_DIR, PLATES_DIR,
    ICON_TYPE_DIR, ICON_SCORE_DIR, ICON_DX_STAR_DIR,
    ICON_COMBO_DIR, ICON_SYNC_DIR,
    ICON_COMBO_RCD_DIR, ICON_SYNC_RCD_DIR,
    ICON_BASE_DIR, BG_DIR, RATING_DIR
)
from modules.user_db import load_all_users, save_user
from modules.user_manager import delete_user
from modules.dbpool_manager import database_cursor
from modules.event_tracker import init_events_table
from modules.i18n import normalize_language

logger = logging.getLogger(__name__)


def clean_unbound_users() -> dict:
    cutoff = datetime.now() - timedelta(hours=1)
    users_to_delete = []
    for user_id, value in load_all_users().items():
        if "sega_id" in value and "sega_pwd" in value:
            continue
        if value.get("import_only") or value.get("auth_type") == "import_token" or value.get("import_tokens"):
            continue
        created_at = value.get('created_at') or value.get('registered_at')
        if created_at:
            try:
                if datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S') > cutoff:
                    continue
            except (ValueError, TypeError):
                pass
        users_to_delete.append(user_id)

    for user_id in users_to_delete:
        logger.info("[SystemCheck] Deleting unbound user: user_id=%s", user_id)
        delete_user(user_id)
    logger.info("[SystemCheck] Cleaned unbound users: count=%s", len(users_to_delete))
    return {"deleted_count": len(users_to_delete), "deleted_users": users_to_delete}


def clean_deprecated_user_fields() -> dict:
    deprecated_fields = {"friend_requests", "id_use", "line_friends", "beta", "beta_ver", "mai_friends"}
    cleaned_users = []
    total_fields_removed = 0
    for user_id, user_data in load_all_users().items():
        fields_removed = sorted(deprecated_fields.intersection(user_data))
        for field in fields_removed:
            user_data.pop(field)
        changed = bool(fields_removed)
        if 'language' in user_data:
            normalized_language = normalize_language(user_data['language'])
            if normalized_language != user_data['language']:
                user_data['language'] = normalized_language
                changed = True
        if changed:
            save_user(user_id, user_data)
            cleaned_users.append({"user_id": user_id, "removed_fields": fields_removed})
            total_fields_removed += len(fields_removed)
            logger.debug("[SystemCheck] Cleaned user fields: user_id=%s removed=%s", user_id, fields_removed)

    logger.info("[SystemCheck] Cleaned deprecated fields: users=%s fields=%s",
                len(cleaned_users), total_fields_removed)
    return {"cleaned_user_count": len(cleaned_users),
            "total_fields_removed": total_fields_removed, "cleaned_users": cleaned_users}


def check_database_connection() -> bool:
    try:
        with database_cursor() as (_, cursor):
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return True
    except Exception:
        logger.exception("[SystemCheck] Database connection check failed")
        return False


def check_required_files() -> dict[str, bool]:
    required_files = {
        "config.json": ("file", "config.json"),
        "dxdata_file": ("file", DXDATA_FILE),
        "dxdata_version": ("file", DXDATA_VERSION_FILE),
        "override_file": ("file", OVERRIDE_FILE),
        "jp_override_file": ("file", JP_OVERRIDE_FILE),
        "intl_override_file": ("file", INTL_OVERRIDE_FILE),
        "notice_file": ("file", NOTICE_FILE),
        "tip_ad_file": ("file", TIP_AD_FILE),
        "dev_tokens": ("file", DEV_TOKENS_FILE),
        "font": ("file", FONT_FILE),
        "logo": ("file", LOGO_FILE),
        "qrcode": ("file", QR_CODE_FILE),
        "backup_dir": ("dir", BACKUP_DIR),
        "img_dir": ("dir", IMG_DIR),
        "versions_dir": ("dir", VERSIONS_DIR),
        "covers_dir": ("dir", COVERS_DIR),
        "plates_dir": ("dir", PLATES_DIR),
        "icon_type": ("dir", ICON_TYPE_DIR),
        "icon_score": ("dir", ICON_SCORE_DIR),
        "icon_dx_star": ("dir", ICON_DX_STAR_DIR),
        "icon_combo": ("dir", ICON_COMBO_DIR),
        "icon_sync": ("dir", ICON_SYNC_DIR),
        "icon_combo_rcd": ("dir", ICON_COMBO_RCD_DIR),
        "icon_sync_rcd": ("dir", ICON_SYNC_RCD_DIR),
        "icon_base": ("dir", ICON_BASE_DIR),
        "bg_dir": ("dir", BG_DIR),
        "rating_dir": ("dir", RATING_DIR),
    }

    results = {}
    for name, (kind, path) in required_files.items():
        if not path:
            logger.warning("[SystemCheck] Path not configured: %s", name)
            results[name] = False
            continue
        if kind == "dir":
            os.makedirs(path, exist_ok=True)
        elif not os.path.isfile(path):
            directory = os.path.dirname(path)
            if directory:
                os.makedirs(directory, exist_ok=True)
            with open(path, 'a', encoding='utf-8'):
                pass
        results[name] = True
    return results

def run_system_check() -> dict:
    database_ok = check_database_connection()
    init_events_table()
    checks = {
        "database": database_ok,
        "files": check_required_files(),
        "cleanup": clean_unbound_users(),
        "deprecated_fields": clean_deprecated_user_fields(),
    }
    logger.log(logging.INFO if database_ok else logging.WARNING,
               "[SystemCheck] Completed with status=%s", "PASS" if database_ok else "WARNING")
    return {"timestamp": datetime.now().isoformat(), "checks": checks,
            "overall_status": "PASS" if database_ok else "WARNING"}
