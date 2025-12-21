"""
系统启动自检模块
在系统启动时执行各种检查和清理任务
"""
import logging
from datetime import datetime
import os
from typing import List, Dict, Any
from modules.config_loader import _config, write_user, mark_user_dirty, USERS
from modules.user_manager import delete_user
from modules.dbpool_manager import get_connection

logger = logging.getLogger(__name__)


def clean_unbound_users() -> Dict[str, Any]:
    """
    清理未完成绑定的用户
    删除没有 sega_id 或 sega_pwd 字段的账户
    """

    deleted_users = []

    # 遍历所有用户
    for user_id, value in USERS.items():
        # 检查是否缺少 sega_id 或 sega_pwd
        if "sega_id" not in value or "sega_pwd" not in value:
            logger.info(f"[SystemCheck] → Deleting unbound user: user_id={user_id}, reason=missing_credentials")
            delete_user(user_id)
            deleted_users.append(user_id)

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
    删除不再使用的字段：friend_requests, id_use, line_friends, beta, beta_ver
    """

    deprecated_fields = ["friend_requests", "id_use", "line_friends", "beta", "beta_ver"]
    cleaned_users = []
    total_fields_removed = 0

    # 遍历所有用户
    for user_id, user_data in USERS.items():
        fields_removed = []

        # 检查并删除废弃字段
        for field in deprecated_fields:
            if field in user_data:
                del user_data[field]
                fields_removed.append(field)
                total_fields_removed += 1

        # 如果有字段被删除，标记用户数据为脏数据并记录
        if fields_removed:
            mark_user_dirty(user_id)
            cleaned_users.append({
                "user_id": user_id,
                "removed_fields": fields_removed
            })
            logger.debug(f"[SystemCheck] Cleaned deprecated fields: user_id={user_id}, fields={fields_removed}")

    # 如果有修改，写入文件
    if cleaned_users:
        write_user()

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
    检查必要文件是否存在

    Returns:
        文件检查结果字典
    """
    file_path_config = _config.get("file_path", {})

    required_files = {
        "config.json": "config.json",
        "dxdata_list": file_path_config.get("dxdata_list", ""),
        "user_list": file_path_config.get("user_list", ""),
        "font_file": file_path_config.get("font", ""),
        "logo_file": file_path_config.get("logo", ""),
    }

    results = {}
    all_pass = True

    for name, path in required_files.items():
        if not path:
            logger.warning(f"[SystemCheck] ⚠ File path not configured: file={name}")
            results[name] = False
            continue

        exists = os.path.exists(path)
        results[name] = exists

        if exists:
            logger.info(f"[SystemCheck] ✓ File exists: file={name}, path={path}")
        else:
            logger.warning(f"[SystemCheck] ✗ File not found: file={name}, path={path}")
            all_pass = False

    return results

def run_system_check() -> Dict[str, Any]:
    """
    运行完整的系统自检

    Returns:
        所有检查结果的汇总字典
    """
    logger.info("=" * 60)
    logger.info("[SystemCheck] → Starting system check...")
    logger.info("=" * 60)

    results = {
        "timestamp": None,
        "checks": {}
    }

    # 1. 数据库连接检查
    logger.info("[SystemCheck] → Phase 1/4: Checking database connection...")
    results["checks"]["database"] = check_database_connection()

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
    logger.info("=" * 60)
    logger.info("[SystemCheck] ✓ System check completed")
    logger.info("=" * 60)

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

    logger.info("=" * 60)

    # 添加时间戳
    results["timestamp"] = datetime.now().isoformat()
    results["overall_status"] = "PASS" if all_pass else "WARNING"

    return results
