import base64
import hmac
import hashlib
import time
from config_loader import BIND_TOKEN_KEY


# 生成 token
def generate_token(user_id: str) -> str:
    """
    生成一个基于 user_id 和时间戳的唯一 token
    格式：base64(user_id.timestamp.signature)
    """
    timestamp = str(int(time.time()))
    raw = f"{user_id}.{timestamp}".encode('utf-8')

    signature = hmac.new(BIND_TOKEN_KEY, raw, hashlib.sha256).digest()

    token = base64.urlsafe_b64encode(raw + b"." + signature).decode('utf-8')
    return token


# 通过 token 获取 user_id
TOKEN_EXPIRE_SECONDS = 120  # 有效期：2 分钟

def get_user_id_from_token(token: str) -> str:
    """
    验证 token 并提取 user_id。
    如果签名不一致或时间过期，则抛出异常。
    """
    try:
        decoded = base64.urlsafe_b64decode(token.encode('utf-8'))

        # 拆分 user_id.timestamp.signature
        parts = decoded.split(b".", 2)
        if len(parts) != 3:
            raise ValueError("Invalid token format")

        user_id_bytes, timestamp_bytes, signature = parts
        raw = user_id_bytes + b"." + timestamp_bytes

        # 验证签名
        expected_signature = hmac.new(BIND_TOKEN_KEY, raw, hashlib.sha256).digest()
        if not hmac.compare_digest(signature, expected_signature):
            raise ValueError("Invalid token signature")

        # 验证时间戳是否过期
        timestamp = int(timestamp_bytes.decode('utf-8'))
        now = int(time.time())
        if abs(now - timestamp) > TOKEN_EXPIRE_SECONDS:
            raise ValueError("Token expired")

        # 返回 user_id 字符串
        return user_id_bytes.decode('utf-8')

    except Exception as e:
        raise ValueError("Invalid token") from e
