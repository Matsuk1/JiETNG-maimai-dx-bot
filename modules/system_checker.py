"""
系统启动自检模块
在系统启动时执行各种检查和清理任务
"""
import logging
from datetime import datetime, timedelta
import os
from typing import Dict, Any
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
from modules.dbpool_manager import get_connection
from modules.event_tracker import init_events_table
from modules.i18n import normalize_language

logger = logging.getLogger(__name__)


def clean_unbound_users() -> Dict[str, Any]:
    """
    清理未完成绑定的用户
    删除注册超过1小时且既没有 SEGA 凭据、也没有 import-token 身份的账户
    """
    now = datetime.now()
    cutoff = now - timedelta(hours=1)

    all_users = load_all_users()

    # 先收集需要删除的用户，避免在迭代中修改字典
    users_to_delete = []
    for user_id, value in all_users.items():
        if "sega_id" in value and "sega_pwd" in value:
            continue
        if (
            value.get("import_only")
            or value.get("auth_type") == "import_token"
            or value.get("import_tokens")
        ):
            continue
        # 检查注册时间，未满1小时的跳过
        created_at = value.get('created_at') or value.get('registered_at')
        if created_at:
            try:
                created_time = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
                if created_time > cutoff:
                    continue
            except (ValueError, TypeError):
                pass
        users_to_delete.append(user_id)

    for user_id in users_to_delete:
        logger.info(f"[SystemCheck] → Deleting unbound user: user_id={user_id}, reason=missing_credentials")
        delete_user(user_id)

    deleted_users = users_to_delete

    result = {
        "deleted_count": len(deleted_users),
        "deleted_users": deleted_users,
    }

    if deleted_users:
        logger.info(f"[SystemCheck] ✓ Cleaned up unbound users: count={len(deleted_users)}")
    else:
        logger.info("[SystemCheck] ✓ No unbound users found")

    return result


def clean_deprecated_user_fields() -> Dict[str, Any]:
    """
    清理用户数据中的废弃字段
    """

    deprecated_fields = ["friend_requests", "id_use", "line_friends", "beta", "beta_ver", "mai_friends"]
    cleaned_users = []
    total_fields_removed = 0

    all_users = load_all_users()

    # 遍历所有用户
    for user_id, user_data in all_users.items():
        fields_removed = []
        changed = False

        # 修正旧的语言代码
        if 'language' in user_data:
            normalized_language = normalize_language(user_data['language'])
            if normalized_language != user_data['language']:
                user_data['language'] = normalized_language
                changed = True
        # 检查并删除废弃字段
        for field in deprecated_fields:
            if field in user_data:
                del user_data[field]
                fields_removed.append(field)
                total_fields_removed += 1
                changed = True

        # 如果数据有变化，保存到 DB 并记录
        if changed:
            save_user(user_id, user_data)
            cleaned_users.append({
                "user_id": user_id,
                "removed_fields": fields_removed
            })
            logger.debug(f"[SystemCheck] Cleaned user fields: user_id={user_id}, removed={fields_removed}")

    result = {
        "cleaned_user_count": len(cleaned_users),
        "total_fields_removed": total_fields_removed,
        "cleaned_users": cleaned_users
    }

    if cleaned_users:
        logger.info(f"[SystemCheck] ✓ Cleaned deprecated fields: users={len(cleaned_users)}, fields_removed={total_fields_removed}")
    else:
        logger.info("[SystemCheck] ✓ No deprecated fields found")

    return result


def check_database_connection() -> bool:
    """
    检查数据库连接是否正常

    Returns:
        True if connection is healthy, False otherwise
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        conn.close()

        logger.info("[SystemCheck] ✓ Database connection check passed")
        return True

    except Exception as e:
        logger.error(f"[SystemCheck] ✗ Database connection check failed: error={e}")
        return False


def check_required_files() -> Dict[str, bool]:
    """
    检查必要文件和目录，不存在则自动创建

    Returns:
        文件检查结果字典
    """
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
            logger.warning(f"[SystemCheck] ⚠ Path not configured: {name}")
            results[name] = False
            continue

        if kind == "dir":
            if not os.path.isdir(path):
                os.makedirs(path, exist_ok=True)
                logger.info(f"[SystemCheck] ✓ Directory created: {name} -> {path}")
            else:
                logger.info(f"[SystemCheck] ✓ Directory exists: {name} -> {path}")
        else:
            if not os.path.isfile(path):
                os.makedirs(os.path.dirname(path), exist_ok=True)
                open(path, 'a').close()
                logger.info(f"[SystemCheck] ✓ File created: {name} -> {path}")
            else:
                logger.info(f"[SystemCheck] ✓ File exists: {name} -> {path}")
        results[name] = True

    return results

def run_system_check() -> Dict[str, Any]:
    """
    运行完整的系统自检

    Returns:
        所有检查结果的汇总字典
    """
    logger.info("[SystemCheck] → Starting system check...")

    results = {
        "timestamp": None,
        "checks": {}
    }

    # 1. 数据库连接检查
    logger.info("[SystemCheck] → Phase 1/4: Checking database connection...")
    results["checks"]["database"] = check_database_connection()

    # 1.5 初始化 events 表
    init_events_table()

    # 2. 必要文件检查
    logger.info("[SystemCheck] → Phase 2/4: Checking required files...")
    results["checks"]["files"] = check_required_files()

    # 3. 清理未绑定的代理用户
    logger.info("[SystemCheck] → Phase 3/4: Cleaning unbound users...")
    results["checks"]["cleanup"] = clean_unbound_users()

    # 4. 清理废弃的用户字段
    logger.info("[SystemCheck] → Phase 4/4: Cleaning deprecated user fields...")
    results["checks"]["deprecated_fields"] = clean_deprecated_user_fields()

    # 生成报告
    logger.info("[SystemCheck] ✓ System check completed")

    # 统计结果
    cleanup = results["checks"]["cleanup"]
    if cleanup["deleted_count"] > 0:
        logger.info(f"[SystemCheck] ✓ Deleted unbound users: count={cleanup['deleted_count']}")

    deprecated_cleanup = results["checks"]["deprecated_fields"]
    if deprecated_cleanup["cleaned_user_count"] > 0:
        logger.info(f"[SystemCheck] ✓ Cleaned deprecated fields: users={deprecated_cleanup['cleaned_user_count']}, fields={deprecated_cleanup['total_fields_removed']}")

    all_pass = results["checks"]["database"]
    if all_pass:
        logger.info("[SystemCheck] ✓ All critical checks passed")
    else:
        logger.warning("[SystemCheck] ⚠ Some checks failed, please review logs")

    # 添加时间戳
    results["timestamp"] = datetime.now().isoformat()
    results["overall_status"] = "PASS" if all_pass else "WARNING"

    return results
