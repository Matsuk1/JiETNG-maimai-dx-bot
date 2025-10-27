"""
系统启动自检模块
在系统启动时执行各种检查和清理任务
"""
import logging
from typing import List, Dict, Any
from modules.config_loader import read_user, write_user, mark_user_dirty, USERS
from modules.user_console import delete_user

logger = logging.getLogger(__name__)


def clean_unbound_users() -> Dict[str, Any]:
    read_user()
    deleted_users = []

    # 遍历所有用户
    for user_id, value in USERS.items():
        if "version" not in value:
            logger.info(f"Deleting unbound user: {user_id}")
            delete_user(user_id)
            deleted_users.append(user_id)

    result = {
        "deleted_count": len(deleted_users),
        "deleted_users": deleted_users,
    }

    if deleted_users:
        logger.info(f"Cleaned up {len(deleted_users)} unbound users")
    else:
        logger.info("No unbound users found")

    return result


def check_database_connection() -> bool:
    """
    检查数据库连接是否正常

    Returns:
        True if connection is healthy, False otherwise
    """
    try:
        from modules.db_pool import get_connection

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        conn.close()

        logger.info("✓ Database connection check passed")
        return True

    except Exception as e:
        logger.error(f"✗ Database connection check failed: {e}")
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
            logger.warning(f"⚠ {name} path not configured")
            results[name] = False
            continue

        exists = os.path.exists(path)
        results[name] = exists

        if exists:
            logger.info(f"✓ {name} exists: {path}")
        else:
            logger.warning(f"✗ {name} not found: {path}")
            all_pass = False

    return results


def clean_user_status_fields() -> Dict[str, Any]:
    """
    清理用户 status 字段中不需要的数据
    只保留 notice_read 字段

    Returns:
        清理结果
    """
    read_user()

    cleaned_count = 0
    removed_fields = []

    for user_id, user_data in users.items():
        # 确保 status 字段存在
        if "status" not in user_data:
            user_data["status"] = {"notice_read": False}
            mark_user_dirty()
            cleaned_count += 1
            continue

        # 获取当前 status
        status = user_data["status"]

        # 保存 notice_read 的值
        notice_read = status.get("notice_read", False)

        # 检查是否有其他字段需要删除
        extra_fields = [k for k in status.keys() if k != "notice_read"]

        if extra_fields:
            # 只保留 notice_read
            user_data["status"] = {"notice_read": notice_read}
            mark_user_dirty()
            cleaned_count += 1
            removed_fields.extend([(user_id, field) for field in extra_fields])
            logger.debug(f"Cleaned status fields for {user_id}: {extra_fields}")

        # 删除 recent_rating 字段
        if "recent_rating" in user_data:
            del user_data["recent_rating"]
            mark_user_dirty()
            logger.debug(f"Removed recent_rating from {user_id}")

    if cleaned_count > 0:
        write_user()
        logger.info(f"✓ Cleaned status fields for {cleaned_count} users")
    else:
        logger.info("✓ No status fields need cleaning")

    return {
        "cleaned_count": cleaned_count,
        "removed_fields_count": len(removed_fields)
    }


def check_data_integrity() -> Dict[str, Any]:
    """
    检查数据完整性

    Returns:
        数据完整性检查结果
    """
    read_user()

    issues = []

    # 检查用户数据结构
    for user_id, user_data in users.items():
        # 检查必要字段
        if "status" not in user_data:
            issues.append(f"User {user_id} missing 'status' field")
            # 自动修复
            user_data["status"] = {"notice_read": False}
            mark_user_dirty()

    if issues:
        logger.warning(f"Found {len(issues)} data integrity issues (auto-fixed)")
        write_user()
    else:
        logger.info("✓ Data integrity check passed")

    return {
        "issues_found": len(issues),
        "issues": issues,
        "auto_fixed": len(issues)
    }


def run_system_check() -> Dict[str, Any]:
    """
    运行完整的系统自检

    Returns:
        所有检查结果的汇总字典
    """
    logger.info("=" * 60)
    logger.info("Starting system check...")
    logger.info("=" * 60)

    results = {
        "timestamp": None,
        "checks": {}
    }

    # 1. 数据库连接检查
    logger.info("\n[1/5] Checking database connection...")
    results["checks"]["database"] = check_database_connection()

    # 2. 必要文件检查
    logger.info("\n[2/5] Checking required files...")
    results["checks"]["files"] = check_required_files()

    # 3. 数据完整性检查
    logger.info("\n[3/5] Checking data integrity...")
    results["checks"]["data_integrity"] = check_data_integrity()

    # 4. 清理用户 status 字段
    logger.info("\n[4/5] Cleaning user status fields...")
    results["checks"]["status_cleanup"] = clean_user_status_fields()

    # 5. 清理未绑定的代理用户
    logger.info("\n[5/5] Cleaning unbound users...")
    results["checks"]["cleanup"] = clean_unbound_users()

    # 生成报告
    logger.info("\n" + "=" * 60)
    logger.info("System check completed")
    logger.info("=" * 60)

    # 统计结果
    status_cleanup = results["checks"]["status_cleanup"]
    if status_cleanup["cleaned_count"] > 0:
        logger.info(f"• Cleaned status fields for {status_cleanup['cleaned_count']} users")

    cleanup = results["checks"]["cleanup"]
    if cleanup["deleted_count"] > 0:
        logger.info(f"• Deleted {cleanup['deleted_count']} unbound users")

    all_pass = results["checks"]["database"]
    if all_pass:
        logger.info("✓ All critical checks passed")
    else:
        logger.warning("⚠ Some checks failed, please review logs")

    logger.info("=" * 60 + "\n")

    # 添加时间戳
    from datetime import datetime
    results["timestamp"] = datetime.now().isoformat()
    results["overall_status"] = "PASS" if all_pass else "WARNING"

    return results
