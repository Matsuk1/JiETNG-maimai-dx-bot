"""
Token管理模块

生成和验证SEGA账户绑定的临时Token
"""

import base64
import hmac
import hashlib
import time
from modules.config_loader import BIND_TOKEN_KEY

# Token有效期 (秒)
TOKEN_EXPIRE_SECONDS = 120


def generate_bind_token(user_id: str) -> str:
    """
    生成绑定Token

    Args:
        user_id: 用户ID

    Returns:
        Base64编码的签名Token字符串
    """
    timestamp = str(int(time.time()))
    raw = f"{user_id}.{timestamp}".encode('utf-8')

    signature = hmac.new(BIND_TOKEN_KEY, raw, hashlib.sha256).digest()

    token = base64.urlsafe_b64encode(raw + b"." + signature).decode('utf-8')
    return token


def get_user_id_from_token(token: str) -> str:
    """
    验证Token并提取用户ID

    Args:
        token: Base64编码的Token字符串

    Returns:
        用户ID

    Raises:
        ValueError: Token无效、签名错误或已过期
    """
    try:
        decoded = base64.urlsafe_b64decode(token.encode('utf-8'))

        parts = decoded.split(b".", 2)
        if len(parts) != 3:
            raise ValueError("Invalid token format")

        user_id_bytes, timestamp_bytes, signature = parts
        raw = user_id_bytes + b"." + timestamp_bytes

        # 验证签名
        expected_signature = hmac.new(BIND_TOKEN_KEY, raw, hashlib.sha256).digest()
        if not hmac.compare_digest(signature, expected_signature):
            raise ValueError("Invalid token signature")

        # 验证时效
        timestamp = int(timestamp_bytes.decode('utf-8'))
        now = int(time.time())
        if abs(now - timestamp) > TOKEN_EXPIRE_SECONDS:
            raise ValueError("Token expired")

        return user_id_bytes.decode('utf-8')

    except Exception as e:
        raise ValueError("Invalid token") from e
