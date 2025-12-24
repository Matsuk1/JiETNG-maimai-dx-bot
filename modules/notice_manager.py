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
            notice['id'] = f"migrated_{i}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            modified = True

    if modified:
        _save_notices(notices)

def _migrate_notices_v2():
    """迁移公告到v2格式(多语言+草稿+投票)"""
    if not os.path.exists(NOTICE_FILE):
        return False

    with open(NOTICE_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    notices = data.get("notices", [])
    modified = False

    for notice in notices:
        # 迁移1: content 字符串 -> 多语言对象
        if isinstance(notice.get('content'), str):
            old_content = notice['content']
            notice['content'] = {
                'ja': old_content,
                'en': old_content,
                'zh': old_content
            }
            modified = True

        # 迁移2: 添加默认字段
        if 'status' not in notice:
            notice['status'] = 'published'
            modified = True

        if 'voting_enabled' not in notice:
            notice['voting_enabled'] = False
            modified = True

        if 'created_by' not in notice:
            notice['created_by'] = 'system'
            modified = True

        if 'updated_at' not in notice:
            notice['updated_at'] = notice.get('date', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            modified = True

    if modified:
        _save_notices(notices)

    return modified

def _load_notices():
    """加载公告列表并执行必要的迁移"""
    if not os.path.exists(NOTICE_FILE):
        return []

    with open(NOTICE_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
        notices = data.get("notices", [])

    # 检查是否需要迁移v1（添加ID）
    if notices and 'id' not in notices[0]:
        _migrate_notices()
        with open(NOTICE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            notices = data.get("notices", [])

    # 检查是否需要迁移v2（多语言+草稿+投票）
    if notices and isinstance(notices[0].get('content'), str):
        _migrate_notices_v2()
        with open(NOTICE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            notices = data.get("notices", [])

    return notices

def _save_notices(notices):
    """保存公告列表到文件"""
    os.makedirs(os.path.dirname(NOTICE_FILE), exist_ok=True)
    with open(NOTICE_FILE, 'w', encoding='utf-8') as f:
        json.dump({"notices": notices}, f, ensure_ascii=False, indent=2)

def _generate_unique_id():
    """生成唯一的公告ID"""
    notices = _load_notices()
    existing_ids = [n.get('id', '') for n in notices]

    notice_id = datetime.now().strftime('%Y%m%d%H%M%S')
    counter = 1
    while notice_id in existing_ids:
        notice_id = datetime.now().strftime('%Y%m%d%H%M%S') + f"_{counter}"
        counter += 1

    return notice_id

def upload_notice(content, date=None, status='published', voting_enabled=False, created_by='system',
                  button_type=None, button_label=None, button_value=None):
    """
    上传新公告

    Args:
        content: 多语言内容字典 {'ja': '...', 'en': '...', 'zh': '...'} 或字符串(向后兼容)
        date: 创建时间
        status: 'draft' 或 'published'
        voting_enabled: 是否启用投票
        created_by: 创建者用户ID
        button_type: 按钮类型 ('uri' 或 'message')
        button_label: 按钮标签 {'ja': '...', 'en': '...', 'zh': '...'}
        button_value: 按钮值（URI或消息文本）

    Returns:
        notice_id: 公告ID
    """
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # 处理内容格式
    if isinstance(content, str):
        # 向后兼容：字符串转换为多语言对象
        content_dict = {'ja': content, 'en': content, 'zh': content}
    elif isinstance(content, dict):
        # 验证至少有一种语言
        if not any(content.values()):
            raise ValueError("At least one language content is required")

        # 未填写的语言使用已填写的语言
        filled_content = next((v for v in content.values() if v), "")
        content_dict = {
            'ja': content.get('ja') or filled_content,
            'en': content.get('en') or filled_content,
            'zh': content.get('zh') or filled_content
        }
    else:
        raise ValueError("Content must be a string or dict")

    notices = _load_notices()
    notice_id = _generate_unique_id()

    new_notice = {
        "id": notice_id,
        "content": content_dict,
        "date": date,
        "status": status,
        "voting_enabled": voting_enabled,
        "created_by": created_by,
        "updated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    # 添加按钮（如果提供）
    if button_type and button_value and button_label:
        new_notice['button'] = {
            'type': button_type,
            'label': button_label,
            'value': button_value
        }

    notices.insert(0, new_notice)
    _save_notices(notices)

    return notice_id

def get_latest_notice():
    """获取最新通知（兼容旧API，不过滤草稿）"""
    notices = _load_notices()
    return notices[0] if notices else None

def get_latest_published_notice():
    """获取最新的已发布公告（排除草稿）"""
    notices = _load_notices()
    for notice in notices:
        if notice.get('status') == 'published':
            return notice
    return None

def get_all_notices(include_drafts=False):
    """
    获取所有公告

    Args:
        include_drafts: 是否包含草稿（仅管理员）

    Returns:
        公告列表
    """
    notices = _load_notices()
    if not include_drafts:
        notices = [n for n in notices if n.get('status') == 'published']
    return notices

def get_notice_by_id(notice_id):
    """根据ID获取公告"""
    notices = _load_notices()
    for notice in notices:
        if notice.get('id') == notice_id:
            return notice
    return None

def update_notice(notice_id, content, button_type=None, button_label=None, button_value=None, remove_button=False):
    """
    更新公告

    Args:
        notice_id: 公告ID
        content: 多语言内容字典 或 字符串(向后兼容)
        button_type: 按钮类型 ('uri' 或 'message')
        button_label: 按钮标签 {'ja': '...', 'en': '...', 'zh': '...'}
        button_value: 按钮值（URI或消息文本）
        remove_button: 是否移除按钮

    Returns:
        bool: 是否成功
    """
    notices = _load_notices()

    # 处理内容格式
    if isinstance(content, str):
        content_dict = {'ja': content, 'en': content, 'zh': content}
    elif isinstance(content, dict):
        if not any(content.values()):
            raise ValueError("At least one language content is required")
        filled_content = next((v for v in content.values() if v), "")
        content_dict = {
            'ja': content.get('ja') or filled_content,
            'en': content.get('en') or filled_content,
            'zh': content.get('zh') or filled_content
        }
    else:
        raise ValueError("Content must be a string or dict")

    for i, notice in enumerate(notices):
        if notice.get('id') == notice_id:
            notices[i]['content'] = content_dict
            notices[i]['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # 处理按钮
            if remove_button:
                notices[i].pop('button', None)
            elif button_type and button_value and button_label:
                notices[i]['button'] = {
                    'type': button_type,
                    'label': button_label,
                    'value': button_value
                }

            _save_notices(notices)
            return True

    return False

def publish_notice(notice_id):
    """
    将草稿发布为正式公告

    Args:
        notice_id: 公告ID

    Returns:
        bool: 是否成功
    """
    notices = _load_notices()

    for i, notice in enumerate(notices):
        if notice.get('id') == notice_id:
            if notice.get('status') != 'draft':
                return False  # 已经发布或状态不是draft

            notices[i]['status'] = 'published'
            notices[i]['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            _save_notices(notices)
            return True

    return False

def delete_notice(notice_id):
    """删除公告"""
    notices = _load_notices()
    original_count = len(notices)
    notices = [n for n in notices if n.get('id') != notice_id]

    if len(notices) < original_count:
        _save_notices(notices)
        return True

    return False

def get_notices_by_date(target_date):
    """按日期获取公告（YYYY-MM-DD）"""
    return [n for n in _load_notices() if n['date'].startswith(target_date)]
