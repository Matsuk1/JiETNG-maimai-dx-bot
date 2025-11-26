"""
JiETNG API Client
封装所有 API 调用
"""

import requests
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class JiETNGAPIClient:
    """JiETNG API 客户端"""

    def __init__(self, base_url: str, token: str):
        """
        初始化 API 客户端

        Args:
            base_url: API 基础 URL
            token: API 访问 Token
        """
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        发送 HTTP 请求

        Args:
            method: HTTP 方法
            endpoint: API 端点
            **kwargs: requests 参数

        Returns:
            响应 JSON 数据
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                timeout=30,
                **kwargs
            )

            logger.debug(f"{method} {url} - Status: {response.status_code}")

            # 尝试解析 JSON
            try:
                data = response.json()
            except ValueError:
                data = {"error": "Invalid JSON response", "text": response.text}

            # 检查 HTTP 状态码
            if response.status_code >= 400:
                logger.error(f"API Error: {response.status_code} - {data}")

            return {
                "status_code": response.status_code,
                "data": data,
                "success": response.status_code < 400
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            return {
                "status_code": 0,
                "data": {"error": "Request failed", "message": str(e)},
                "success": False
            }

    # ==================== 用户管理 ====================

    def get_users(self) -> Dict[str, Any]:
        """获取所有用户列表"""
        return self._request("GET", "/users")

    def create_user(self, user_id: str, nickname: str, language: str = "en") -> Dict[str, Any]:
        """
        创建新用户并生成绑定链接

        Args:
            user_id: 用户 ID（必须以 U 开头）
            nickname: 用户昵称
            language: 语言设置 (ja/en/zh)

        Returns:
            包含 bind_url 和 token 的响应
        """
        return self._request("POST", f"/register/{user_id}", json={
            "nickname": nickname,
            "language": language
        })

    def get_user(self, user_id: str) -> Dict[str, Any]:
        """获取用户信息"""
        return self._request("GET", f"/user/{user_id}")

    def delete_user(self, user_id: str) -> Dict[str, Any]:
        """删除用户"""
        return self._request("DELETE", f"/user/{user_id}")

    def update_user(self, user_id: str) -> Dict[str, Any]:
        """队列用户数据更新"""
        return self._request("POST", f"/update/{user_id}")

    # ==================== 记录管理 ====================

    def get_records(
        self,
        user_id: str,
        record_type: str = "best50",
        command: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取用户成绩记录

        Args:
            user_id: 用户 ID
            record_type: 记录类型 (best50/best100/best35/best15等)
            command: 筛选命令（可选）

        Returns:
            包含 old_songs 和 new_songs 的响应
        """
        params = {"type": record_type}
        if command:
            params["command"] = command

        return self._request("GET", f"/records/{user_id}", params=params)

    # ==================== 歌曲搜索 ====================

    def search_songs(
        self,
        query: str = "",
        ver: str = "jp",
        max_results: int = 6
    ) -> Dict[str, Any]:
        """
        搜索歌曲

        Args:
            query: 搜索关键词（空字符串使用 __empty__）
            ver: 版本 (jp/intl)
            max_results: 最大结果数

        Returns:
            包含歌曲列表的响应
        """
        # 处理空字符串
        if query == "":
            query = "__empty__"

        params = {
            "q": query,
            "ver": ver,
            "max_results": max_results
        }

        return self._request("GET", "/search", params=params)

    # ==================== 版本管理 ====================

    def get_versions(self) -> Dict[str, Any]:
        """获取所有 maimai 版本列表"""
        return self._request("GET", "/versions")

    # ==================== 任务管理 ====================

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        查询任务状态

        Args:
            task_id: 任务 ID

        Returns:
            包含任务状态的响应（running/queued/completed/cancelled/not_found）
        """
        return self._request("GET", f"/task/{task_id}")
