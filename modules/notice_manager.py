import json
import os
from datetime import datetime
from modules.config_loader import NOTICE_FILE

def _migrate_notices():
    """为旧公告添加 ID（如果缺失）"""
    if not os.path.exists(NOTICE_FILE):
        return

    with open(NOTICE_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    notices = data.get("notices", [])
    modified = False

    for i, notice in enumerate(notices):
        if 'id' not in notice:
            # 为旧公告生成 ID
            notice['id'] = f"migrated_{i}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            modified = True

    if modified:
        _save_notices(notices)

def _load_notices():
    if not os.path.exists(NOTICE_FILE):
        return []
    with open(NOTICE_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
        notices = data.get("notices", [])

        # 检查是否需要迁移
        if notices and 'id' not in notices[0]:
            _migrate_notices()
            # 重新加载
            with open(NOTICE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                notices = data.get("notices", [])

        return notices

def _save_notices(notices):
    with open(NOTICE_FILE, 'w', encoding='utf-8') as f:
        json.dump({"notices": notices}, f, ensure_ascii=False, indent=2)

def upload_notice(content, date=None):
    """上传新通知"""
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    notices = _load_notices()

    # 生成唯一ID
    notice_id = datetime.now().strftime('%Y%m%d%H%M%S')
    if notices:
        # 确保ID唯一
        existing_ids = [n.get('id', '') for n in notices]
        counter = 1
        while notice_id in existing_ids:
            notice_id = datetime.now().strftime('%Y%m%d%H%M%S') + f"_{counter}"
            counter += 1

    new_notice = {
        "id": notice_id,
        "content": content,
        "date": date
    }

    notices.insert(0, new_notice)
    _save_notices(notices)
    return notice_id

def get_latest_notice():
    """获取最新通知"""
    notices = _load_notices()
    return notices[0] if notices else None

def get_all_notices():
    """获取所有通知"""
    return _load_notices()

def get_notice_by_id(notice_id):
    """根据ID获取通知"""
    notices = _load_notices()
    for notice in notices:
        if notice.get('id') == notice_id:
            return notice
    return None

def update_notice(notice_id, content):
    """更新通知"""
    notices = _load_notices()
    for i, notice in enumerate(notices):
        if notice.get('id') == notice_id:
            notices[i]['content'] = content
            notices[i]['date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            _save_notices(notices)
            return True
    return False

def delete_notice(notice_id):
    """删除通知"""
    notices = _load_notices()
    original_count = len(notices)
    notices = [n for n in notices if n.get('id') != notice_id]

    if len(notices) < original_count:
        _save_notices(notices)
        return True
    return False

def get_notices_by_date(target_date):
    """按日期获取通知（YYYY-MM-DD）"""
    return [n for n in _load_notices() if n['date'].startswith(target_date)]
