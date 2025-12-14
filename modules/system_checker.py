"""
系统启动自检模块
在系统启动时执行各种检查和清理任务
"""
import logging
from typing import List, Dict, Any
from modules.config_loader import write_user, mark_user_dirty, USERS
from modules.user_manager import delete_user

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


def check_database_connection() -> bool:
    """
    检查数据库连接是否正常

    Returns:
        True if connection is healthy, False otherwise
    """
    try:
        from modules.dbpool_manager import get_connection

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
    import os
    from modules.config_loader import _config

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
    logger.info("[SystemCheck] → Phase 1/3: Checking database connection...")
    results["checks"]["database"] = check_database_connection()

    # 2. 必要文件检查
    logger.info("[SystemCheck] → Phase 2/3: Checking required files...")
    results["checks"]["files"] = check_required_files()

    # 3. 清理未绑定的代理用户
    logger.info("[SystemCheck] → Phase 3/3: Cleaning unbound users...")
    results["checks"]["cleanup"] = clean_unbound_users()

    # 生成报告
    logger.info("=" * 60)
    logger.info("[SystemCheck] ✓ System check completed")
    logger.info("=" * 60)

    # 统计结果
    cleanup = results["checks"]["cleanup"]
    if cleanup["deleted_count"] > 0:
        logger.info(f"[SystemCheck] ✓ Deleted unbound users: count={cleanup['deleted_count']}")

    all_pass = results["checks"]["database"]
    if all_pass:
        logger.info("[SystemCheck] ✓ All critical checks passed")
    else:
        logger.warning("[SystemCheck] ⚠ Some checks failed, please review logs")

    logger.info("=" * 60)

    # 添加时间戳
    from datetime import datetime
    results["timestamp"] = datetime.now().isoformat()
    results["overall_status"] = "PASS" if all_pass else "WARNING"

    return results
