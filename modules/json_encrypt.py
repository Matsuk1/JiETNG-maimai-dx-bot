"""
JSON加密模块

使用Fernet对称加密保护敏感的JSON数据
"""

import os
import json
from typing import Dict, Any
from cryptography.fernet import Fernet


def write_encrypted_json(data: Dict[str, Any], filename: str, key: bytes) -> None:
    """
    将字典加密后写入文件

    Args:
        data: 要加密的字典数据
        filename: 目标文件路径
        key: Fernet加密密钥 (32字节base64编码)
    """
    fernet = Fernet(key)
    json_str = json.dumps(data)
    encrypted = fernet.encrypt(json_str.encode())

    # 确保目录存在
    os.makedirs(os.path.dirname(filename) or ".", exist_ok=True)

    with open(filename, 'wb') as f:
        f.write(encrypted)


def read_encrypted_json(filename: str, key: bytes) -> Dict[str, Any]:
    """
    从加密文件读取并解密JSON数据

    Args:
        filename: 加密文件路径
        key: Fernet解密密钥

    Returns:
        解密后的字典数据,如果文件不存在则返回空字典
    """
    fernet = Fernet(key)

    # 如果文件不存在,创建空文件
    if not os.path.exists(filename):
        write_encrypted_json({}, filename, key)

    with open(filename, 'rb') as f:
        encrypted = f.read()

    decrypted = fernet.decrypt(encrypted).decode()
    return json.loads(decrypted)
