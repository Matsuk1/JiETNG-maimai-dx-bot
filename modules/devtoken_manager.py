"""
开发者 Token 管理模块
Developer Token Management Module
"""

import json
import os
import secrets
from datetime import datetime

# 从配置加载文件路径
from modules.config_loader import DEV_TOKENS_FILE

def load_dev_tokens():
    """加载开发者 tokens"""
    if not os.path.exists(DEV_TOKENS_FILE):
        return {}

    try:
        with open(DEV_TOKENS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def save_dev_tokens(tokens):
    """保存开发者 tokens"""
    try:
        os.makedirs(os.path.dirname(DEV_TOKENS_FILE), exist_ok=True)
        with open(DEV_TOKENS_FILE, 'w', encoding='utf-8') as f:
            json.dump(tokens, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

def generate_token():
    """生成一个安全的随机 token"""
    return secrets.token_urlsafe(32)

def create_dev_token(note, created_by):
    """
    创建新的开发者 token

    Args:
        note: Token 备注说明
        created_by: 创建者的 user_id

    Returns:
        dict: 包含 token_id 和 token 的字典，失败返回 None
    """
    tokens = load_dev_tokens()

    # 生成唯一的 token_id
    token_id = f"jt_{secrets.token_hex(8)}"
    while token_id in tokens:
        token_id = f"jt_{secrets.token_hex(8)}"

    # 生成实际的 token
    token = generate_token()

    # 创建 token 数据
    created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    tokens[token_id] = {
        "token": token,
        "note": note,
        "created_at": created_at,
        "created_by": created_by,
        "last_used": None,
        "revoked": False
    }

    if save_dev_tokens(tokens):
        return {
            "token_id": token_id,
            "token": token,
            "note": note,
            "created_at": created_at
        }
    return None

def list_dev_tokens():
    """
    获取所有 token 列表

    Returns:
        list: Token 信息列表
    """
    tokens = load_dev_tokens()
    result = []

    for token_id, data in tokens.items():
        result.append({
            "token_id": token_id,
            "note": data.get("note", ""),
            "created_at": data.get("created_at", ""),
            "created_by": data.get("created_by", ""),
            "last_used": data.get("last_used", "Never"),
            "revoked": data.get("revoked", False),
            "token_preview": data.get("token", "")[:8] + "..." if data.get("token") else ""
        })

    return result

def revoke_dev_token(token_id):
    """
    撤销指定的 token

    Args:
        token_id: Token ID

    Returns:
        bool: 是否成功
    """
    tokens = load_dev_tokens()

    if token_id not in tokens:
        return False

    tokens[token_id]["revoked"] = True
    return save_dev_tokens(tokens)

def verify_dev_token(token):
    """
    验证 token 是否有效

    Args:
        token: 实际的 token 字符串

    Returns:
        dict: Token 信息，如果无效返回 None
    """
    tokens = load_dev_tokens()

    for token_id, data in tokens.items():
        if data.get("token") == token and not data.get("revoked", False):
            # 更新最后使用时间
            data["last_used"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            tokens[token_id] = data
            save_dev_tokens(tokens)

            return {
                "token_id": token_id,
                "note": data.get("note", ""),
                "created_by": data.get("created_by", "")
            }

    return None

def get_token_info(token_id=None, token=None):
    """
    获取 token 详细信息

    Args:
        token_id: Token ID（可选）
        token: 实际的 token 字符串（可选）

    Returns:
        dict: Token 详细信息，如果不存在返回 None
    """
    tokens = load_dev_tokens()

    if token_id and token_id in tokens:
        data = tokens[token_id]
        return {
            "token_id": token_id,
            "token": data.get("token", ""),
            "note": data.get("note", ""),
            "created_at": data.get("created_at", ""),
            "created_by": data.get("created_by", ""),
            "last_used": data.get("last_used", "Never"),
            "revoked": data.get("revoked", False)
        }

    if token:
        for tid, data in tokens.items():
            if data.get("token") == token:
                return {
                    "token_id": tid,
                    "token": data.get("token", ""),
                    "note": data.get("note", ""),
                    "created_at": data.get("created_at", ""),
                    "created_by": data.get("created_by", ""),
                    "last_used": data.get("last_used", "Never"),
                    "revoked": data.get("revoked", False)
                }

    return None
