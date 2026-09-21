import json
import logging
import os
import subprocess
import tempfile
from datetime import datetime

import pyzipper

from modules.config_loader import BACKUP_DIR

logger = logging.getLogger(__name__)


def _write_json(path, data):
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def create_backup(users_data: dict, config_data: dict, db_config: dict,
                  backup_password: str) -> tuple[bool, str, str | None]:
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            sql_file = os.path.join(temp_dir, "maimai_records.sql")
            success, msg = _export_mysql_database(db_config, sql_file)
            if not success:
                logger.warning("[Backup] Database export warning: %s", msg)
                with open(sql_file, "w", encoding="utf-8") as file:
                    file.write(f"-- Database export failed: {msg}\n")

            user_json_file = os.path.join(temp_dir, "user.json")
            config_json_file = os.path.join(temp_dir, "config.json")
            _write_json(user_json_file, users_data)
            _write_json(config_json_file, config_data)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"backup_{timestamp}.zip"
            backup_path = os.path.join(BACKUP_DIR, backup_filename)
            with pyzipper.AESZipFile(
                backup_path, "w", compression=pyzipper.ZIP_DEFLATED,
                encryption=pyzipper.WZ_AES,
            ) as zf:
                zf.setpassword(backup_password.encode("utf-8"))
                zf.write(sql_file, arcname="maimai_records.sql")
                zf.write(user_json_file, arcname="user.json")
                zf.write(config_json_file, arcname="config.json")
            logger.info("[Backup] Encrypted backup created: %s", backup_path)
            size_mb = os.path.getsize(backup_path) / (1024 * 1024)
            message = (f"File: {backup_filename}\nSize: {size_mb:.2f} MB\n"
                       f"Password: config.admin_password\nLocation: {BACKUP_DIR}/")
            return True, message, backup_path
    except Exception as exc:
        logger.exception("[Backup] Backup failed")
        return False, f"❌ Backup failed\nError: {exc}", None


def _export_mysql_database(db_config: dict, output_file: str) -> tuple[bool, str]:
    try:
        host = db_config.get('host', 'localhost')
        user = db_config.get('user', 'root')
        password = db_config.get('password', '')
        database = db_config.get('database', 'maimai_records')
        cmd = ['mysqldump', f'--host={host}', f'--user={user}']
        if password:
            cmd.append(f'--password={password}')
        cmd.extend(['--single-transaction', '--quick', '--lock-tables=false', database])

        with open(output_file, 'w', encoding='utf-8') as file:
            result = subprocess.run(
                cmd, stdout=file, stderr=subprocess.PIPE, text=True, timeout=300,
            )
        if result.returncode != 0:
            error_msg = result.stderr.strip() if result.stderr else "Unknown error"
            logger.error("[Backup] mysqldump failed: %s", error_msg)
            return False, f"mysqldump error: {error_msg}"
        logger.info("[Backup] Database exported: %s", database)
        return True, "Database exported successfully"
    except FileNotFoundError:
        return False, "mysqldump command not found (MySQL client not installed)"
    except subprocess.TimeoutExpired:
        return False, "Database export timeout (>5 minutes)"
    except Exception as exc:
        return False, f"Export error: {exc}"
