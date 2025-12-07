"""
Maimai Cookie 管理模块
支持 cookie 的导出、导入、验证和加密存储
"""

import json
import logging
import base64
import os
from pathlib import Path
from http.cookies import SimpleCookie
from datetime import datetime
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)


def _get_encryption_key(password: str) -> bytes:
    """生成加密密钥

    Args:
        password: 加密密码（必须提供）

    Returns:
        bytes: Fernet 加密密钥
    """
    if not password:
        raise ValueError("加密密码不能为空")

    # 使用固定的 salt
    salt = b'maimai_cookie_salt_2025'

    # 使用 PBKDF2HMAC 派生密钥
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key


def encrypt_data(data: str, password: str) -> str:
    """加密数据

    Args:
        data: 要加密的字符串
        password: 加密密码（必须提供）

    Returns:
        str: 加密后的字符串（base64编码）
    """
    key = _get_encryption_key(password)
    f = Fernet(key)
    encrypted = f.encrypt(data.encode())
    return encrypted.decode()


def decrypt_data(encrypted_data: str, password: str) -> str:
    """解密数据

    Args:
        encrypted_data: 加密的字符串
        password: 解密密码（必须提供）

    Returns:
        str: 解密后的字符串

    Raises:
        Exception: 解密失败（密码错误或数据损坏）
    """
    key = _get_encryption_key(password)
    f = Fernet(key)
    decrypted = f.decrypt(encrypted_data.encode())
    return decrypted.decode()


def export_cookies(cookies, file_path: str, encrypt: bool = False, password: str = None) -> dict:
    """导出 cookies 到 JSON 文件

    Args:
        cookies: aiohttp cookies 对象 (SimpleCookie)
        file_path: 保存路径
        encrypt: 是否加密存储
        password: 加密密码（仅在 encrypt=True 时使用）

    Returns:
        dict: 导出的 cookies 字典
    """
    cookies_dict = {}

    # 将 cookies 转换为可序列化的字典
    for key, cookie in cookies.items():
        cookies_dict[key] = {
            'value': cookie.value,
            'domain': cookie.get('domain', ''),
            'path': cookie.get('path', '/'),
            'expires': cookie.get('expires', ''),
            'max-age': cookie.get('max-age', ''),
            'secure': cookie.get('secure', False),
            'httponly': cookie.get('httponly', False)
        }

    # 添加元数据
    metadata = {
        'cookies': cookies_dict,
        'export_time': datetime.now().isoformat(),
        'count': len(cookies_dict),
        'encrypted': encrypt
    }

    # 保存到文件
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)

    if encrypt:
        # 加密模式：将 JSON 加密后保存
        json_str = json.dumps(metadata, ensure_ascii=False)
        encrypted_data = encrypt_data(json_str, password)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(encrypted_data)
        logger.info(f"Cookies 已加密导出到: {file_path}")
    else:
        # 普通模式：直接保存 JSON
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        logger.info(f"Cookies 已导出到: {file_path}")

    logger.info(f"包含 {len(cookies_dict)} 个 cookie")
    logger.debug(f"Cookie keys: {list(cookies_dict.keys())}")

    return cookies_dict


def import_cookies(file_path: str, password: str = None) -> SimpleCookie:
    """从 JSON 文件导入 cookies

    Args:
        file_path: cookies 文件路径
        password: 解密密码（如果文件是加密的）

    Returns:
        SimpleCookie 对象

    Raises:
        FileNotFoundError: 文件不存在
        json.JSONDecodeError: JSON 格式错误
        Exception: 解密失败
    """
    if not Path(file_path).exists():
        raise FileNotFoundError(f"Cookie 文件不存在: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        file_content = f.read()

    # 尝试判断是否是加密文件
    try:
        # 先尝试作为 JSON 解析
        data = json.loads(file_content)
    except json.JSONDecodeError:
        # JSON 解析失败，可能是加密文件
        logger.debug("检测到加密的 cookie 文件，尝试解密...")
        try:
            decrypted_content = decrypt_data(file_content, password)
            data = json.loads(decrypted_content)
            logger.info("Cookie 文件解密成功")
        except Exception as e:
            raise Exception(f"Cookie 解密失败: {e}. 请检查密码是否正确")

    # 兼容旧格式（没有元数据）
    if 'cookies' in data:
        cookies_dict = data['cookies']
        export_time = data.get('export_time', 'unknown')
        is_encrypted = data.get('encrypted', False)
        logger.debug(f"Cookie 导出时间: {export_time}, 加密: {is_encrypted}")
    else:
        cookies_dict = data

    # 转换为 SimpleCookie 对象
    cookies = SimpleCookie()
    for key, value_dict in cookies_dict.items():
        cookies[key] = value_dict['value']

        # 设置其他属性（如果存在）
        if value_dict.get('domain'):
            cookies[key]['domain'] = value_dict['domain']
        if value_dict.get('path'):
            cookies[key]['path'] = value_dict['path']
        if value_dict.get('expires'):
            cookies[key]['expires'] = value_dict['expires']

    logger.info(f"Cookies 已从文件导入: {file_path}")
    logger.info(f"包含 {len(cookies)} 个 cookie")
    logger.debug(f"Cookie keys: {list(cookies.keys())}")

    return cookies


async def validate_cookies(cookies, ver="jp") -> bool:
    """验证 cookies 是否有效

    Args:
        cookies: SimpleCookie 对象
        ver: 版本 (jp/intl)

    Returns:
        bool: cookies 是否有效
    """
    from modules.maimai_manager import get_maimai_info

    try:
        user_info = await get_maimai_info(cookies, ver)
        if user_info and user_info.get('name') and user_info.get('name') != "NAME_ERROR":
            logger.info(f"Cookie 验证成功: {user_info.get('name')}")
            return True
        else:
            logger.warning("Cookie 验证失败: 无法获取用户信息")
            return False
    except Exception as e:
        logger.error(f"Cookie 验证异常: {e}")
        return False


def get_cookie_info(file_path: str) -> dict:
    """获取 cookie 文件的信息（不导入）

    Args:
        file_path: cookies 文件路径

    Returns:
        dict: cookie 信息
            {
                'export_time': str,
                'cookie_count': int,
                'cookie_keys': list,
                'file_size': int
            }
    """
    if not Path(file_path).exists():
        raise FileNotFoundError(f"Cookie 文件不存在: {file_path}")

    file_path_obj = Path(file_path)
    file_size = file_path_obj.stat().st_size

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 兼容旧格式
    if 'cookies' in data:
        cookies_dict = data['cookies']
        export_time = data.get('export_time', 'unknown')
    else:
        cookies_dict = data
        export_time = 'unknown'

    return {
        'export_time': export_time,
        'cookie_count': len(cookies_dict),
        'cookie_keys': list(cookies_dict.keys()),
        'file_size': file_size,
        'file_path': str(file_path)
    }


class CookieManager:
    """Cookie 管理器类"""

    def __init__(self, storage_dir: str = "cookies", encrypt: bool = True, password: str = None):
        """初始化 Cookie 管理器

        Args:
            storage_dir: cookie 存储目录
            encrypt: 是否加密存储 cookie（默认开启）
            password: 加密密码（可选，不提供则使用默认密钥）
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.encrypt = encrypt
        self.password = password
        logger.debug(f"Cookie 管理器初始化，存储目录: {self.storage_dir}, 加密: {encrypt}")

    def get_cookie_path(self, account_name: str) -> Path:
        """获取账号的 cookie 文件路径

        Args:
            account_name: 账号名称

        Returns:
            Path: cookie 文件路径
        """
        return self.storage_dir / f"{account_name}.json"

    def save(self, account_name: str, cookies) -> str:
        """保存账号的 cookies

        Args:
            account_name: 账号名称
            cookies: SimpleCookie 对象

        Returns:
            str: 保存的文件路径
        """
        file_path = self.get_cookie_path(account_name)
        export_cookies(cookies, str(file_path), encrypt=self.encrypt, password=self.password)
        return str(file_path)

    def load(self, account_name: str) -> SimpleCookie:
        """加载账号的 cookies

        Args:
            account_name: 账号名称

        Returns:
            SimpleCookie: cookies 对象

        Raises:
            FileNotFoundError: cookie 文件不存在
        """
        file_path = self.get_cookie_path(account_name)
        return import_cookies(str(file_path), password=self.password)

    def exists(self, account_name: str) -> bool:
        """检查账号的 cookie 是否存在

        Args:
            account_name: 账号名称

        Returns:
            bool: cookie 是否存在
        """
        return self.get_cookie_path(account_name).exists()

    def delete(self, account_name: str) -> bool:
        """删除账号的 cookies

        Args:
            account_name: 账号名称

        Returns:
            bool: 是否成功删除
        """
        file_path = self.get_cookie_path(account_name)
        if file_path.exists():
            file_path.unlink()
            logger.info(f"已删除 cookie: {account_name}")
            return True
        return False

    def list_accounts(self) -> list:
        """列出所有已保存的账号

        Returns:
            list: 账号名称列表
        """
        return [p.stem for p in self.storage_dir.glob("*.json")]

    def get_info(self, account_name: str) -> dict:
        """获取账号 cookie 的信息

        Args:
            account_name: 账号名称

        Returns:
            dict: cookie 信息
        """
        file_path = self.get_cookie_path(account_name)
        return get_cookie_info(str(file_path))

    async def validate(self, account_name: str, ver="jp") -> bool:
        """验证账号的 cookies 是否有效

        Args:
            account_name: 账号名称
            ver: 版本 (jp/intl)

        Returns:
            bool: cookies 是否有效
        """
        cookies = self.load(account_name)
        return await validate_cookies(cookies, ver)
