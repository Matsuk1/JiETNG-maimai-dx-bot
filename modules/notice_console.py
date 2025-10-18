import json
import os
from datetime import datetime
from modules.config_loader import NOTICE_FILE

def _load_notices():
    if not os.path.exists(NOTICE_FILE):
        return []
    with open(NOTICE_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
        return data.get("notices", [])

def _save_notices(notices):
    with open(NOTICE_FILE, 'w', encoding='utf-8') as f:
        json.dump({"notices": notices}, f, ensure_ascii=False, indent=2)

def upload_notice(content, date=None):
    """上传新通知"""
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')
    notices = _load_notices()
    notices.insert(0, {"content": content, "date": date})
    _save_notices(notices)

def get_latest_notice():
    """获取最新通知"""
    notices = _load_notices()
    return notices[0] if notices else None

def get_all_notices():
    """获取通知列表"""
    return _load_notices()

def get_notices_by_date(target_date):
    """按日期获取通知（YYYY-MM-DD）"""
    return [n for n in _load_notices() if n['date'] == target_date]
