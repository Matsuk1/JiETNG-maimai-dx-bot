"""同步客户端 / Sync client."""
from __future__ import annotations

import json
from typing import Any, Iterator, Mapping, Optional, Tuple

import httpx

from ._http import (
    DEFAULT_BASE_URL,
    DEFAULT_TIMEOUT,
    _attachment_filename,
    _binary_response,
    _build_headers,
    _check_response,
)


# ============================================================
# Resource 命名空间
# ============================================================

class _BaseResource:
    """资源基类，仅持有 client 引用。"""
    __slots__ = ("_client",)

    def __init__(self, client: "jietngClient"):
        self._client = client


class UsersResource(_BaseResource):
    """用户相关：列表 / 详情 / 绑定 / 同步 等。"""

    def list(self) -> dict:
        """``GET /users`` —— 列出所有已注册用户。"""
        return self._client._request("GET", "/users")

    def get(self, user_id: str) -> dict:
        """``GET /users/{user_id}`` —— 取单个用户数据。"""
        return self._client._request("GET", f"/users/{user_id}")

    def create(self, **fields: Any) -> dict:
        """``POST /users`` —— 创建用户（管理员 token）。"""
        return self._client._request("POST", "/users", json=fields)

    def delete(self, user_id: str) -> dict:
        """``DELETE /users/{user_id}`` —— 删除用户。"""
        return self._client._request("DELETE", f"/users/{user_id}")

    def sync_stream(self, user_id: str) -> Iterator[dict]:
        """``POST /users/{user_id}/sync/stream`` —— 逐行返回 accepted/completed 事件。"""
        with self._client._http.stream("POST", f"/users/{user_id}/sync/stream") as resp:
            if not (200 <= resp.status_code < 300):
                resp.read()
                _check_response(resp)
            for line in resp.iter_lines():
                if line:
                    yield json.loads(line)

    def get_rebind_url(self, user_id: str) -> dict:
        """``GET /users/{user_id}/rebind-url``"""
        return self._client._request("GET", f"/users/{user_id}/rebind-url")

    def get_bind_url(self, user_id: str) -> dict:
        """``GET /users/{user_id}/bind-url``"""
        return self._client._request("GET", f"/users/{user_id}/bind-url")

    def get_settings_url(self, user_id: str) -> dict:
        """``GET /users/{user_id}/settings-url``"""
        return self._client._request("GET", f"/users/{user_id}/settings-url")

    def bind(self, user_id: str, **fields: Any) -> dict:
        """``POST /users/{user_id}/bind`` —— 首次绑定 SEGA 账号。"""
        return self._client._request("POST", f"/users/{user_id}/bind", json=fields)

    def update_bind(self, user_id: str, **fields: Any) -> dict:
        """``PUT /users/{user_id}/bind`` —— 更新已绑定信息。"""
        return self._client._request("PUT", f"/users/{user_id}/bind", json=fields)


class PermissionsResource(_BaseResource):
    """对某个用户的访问权限管理。"""

    def request(self, user_id: str, requester_name: Optional[str] = None) -> dict:
        """``POST /users/{user_id}/permissions`` —— 请求访问权限。"""
        body = {"requester_name": requester_name} if requester_name else {}
        return self._client._request("POST", f"/users/{user_id}/permissions", json=body)

    def list_requests(self, user_id: str) -> dict:
        """``GET /users/{user_id}/permissions/requests`` —— owner 查看待处理请求。"""
        return self._client._request("GET", f"/users/{user_id}/permissions/requests")

    def accept(self, user_id: str, request_id: str) -> dict:
        """``PATCH …/permissions/requests/{request_id}`` —— owner 接受请求。"""
        return self._client._request(
            "PATCH",
            f"/users/{user_id}/permissions/requests/{request_id}",
            json={"action": "accept"},
        )

    def reject(self, user_id: str, request_id: str) -> dict:
        """``PATCH …/permissions/requests/{request_id}`` —— owner 拒绝请求。"""
        return self._client._request(
            "PATCH",
            f"/users/{user_id}/permissions/requests/{request_id}",
            json={"action": "reject"},
        )

    def revoke(self, user_id: str, token_id: str) -> dict:
        """``DELETE /users/{user_id}/permissions/{token_id}`` —— owner 撤销某个 token 的权限。"""
        return self._client._request("DELETE", f"/users/{user_id}/permissions/{token_id}")

    def revoke_self(self, user_id: str) -> dict:
        """``DELETE /users/{user_id}/permissions/self`` —— 当前 token 主动放弃对该用户的权限。"""
        return self._client._request("DELETE", f"/users/{user_id}/permissions/self")


class SongsResource(_BaseResource):
    """歌曲搜索 + 单曲信息。"""

    def search(
        self,
        q: str,
        ver: Optional[str] = None,
        max_results: int = 6,
        user_id: Optional[str] = None,
    ) -> dict:
        """``GET /songs/search``"""
        params = {"q": q, "max_results": max_results}
        if ver is not None:
            params["ver"] = ver
        if user_id:
            params["user_id"] = user_id
        return self._client._request("GET", "/songs/search", params=params)

    def info(self, song_id: str) -> dict:
        """``GET /songs/{song_id}/image`` —— 返回歌曲信息图片（PNG bytes）。"""
        return self._client._request("GET", f"/songs/{song_id}/image", binary=True)


class VersionsResource(_BaseResource):
    def list(self) -> dict:
        """``GET /versions``"""
        return self._client._request("GET", "/versions")


class DxdataResource(_BaseResource):
    def get(self, ver: str = "jp") -> dict:
        """``GET /dxdata?ver=…`` —— 获取 JP 或 INTL 的完整 DXData。"""
        return self._client._request("GET", "/dxdata", params={"ver": ver})


class ImagesResource(_BaseResource):
    """图片生成系列（返回 PNG bytes）。"""

    def user_song(self, user_id: str, song_id: str) -> bytes:
        """``GET /users/{user_id}/songs/{song_id}/image``"""
        return self._client._request(
            "GET", f"/users/{user_id}/songs/{song_id}/image", binary=True,
        )

    def records(self, user_id: str, command: str = "b50") -> bytes:
        """``GET /users/{user_id}/image?command=…`` —— b50/rct50/apb50/… 等成绩图。"""
        return self._client._request(
            "GET", f"/users/{user_id}/image",
            params={"command": command}, binary=True,
        )

    def plate(self, user_id: str, title: str, filter_mode: Optional[str] = None) -> bytes:
        """``GET /users/{user_id}/plate?title=…&filter=…``"""
        params: dict = {"title": title}
        if filter_mode:
            params["filter"] = filter_mode
        return self._client._request(
            "GET", f"/users/{user_id}/plate", params=params, binary=True,
        )

    def achievement(
        self,
        user_id: str,
        level: str,
        rank: Optional[str] = None,
        filter_mode: Optional[str] = None,
    ) -> bytes:
        """``GET /users/{user_id}/achievement?level=…&rank=…&filter=…``"""
        params: dict = {"level": level}
        if rank:
            params["rank"] = rank
        if filter_mode:
            params["filter"] = filter_mode
        return self._client._request(
            "GET", f"/users/{user_id}/achievement", params=params, binary=True,
        )


class ExportsResource(_BaseResource):
    """成绩导出（JSON / XML）。"""

    def download(self, user_id: str, fmt: str = "json") -> Tuple[bytes, Optional[str]]:
        """``GET /users/{user_id}/export?fmt=json|xml``

        Returns:
            (content_bytes, suggested_filename) —— filename 取自服务端
            Content-Disposition；可能为 None。
        """
        return self._client._request_with_filename(
            "GET", f"/users/{user_id}/export", params={"fmt": fmt},
        )

    def save(self, user_id: str, fmt: str = "json", path: Optional[str] = None) -> str:
        """便捷方法：直接保存到本地。返回最终写入的文件路径。

        Args:
            user_id: 用户 ID
            fmt: ``json`` 或 ``xml``
            path: 完整文件路径；不传则用服务端推荐的文件名写到当前目录
        """
        content, suggested = self.download(user_id, fmt=fmt)
        target = path or suggested or f"jietng-{user_id}.{fmt}"
        with open(target, "wb") as f:
            f.write(content)
        return target


class ImportsResource(_BaseResource):
    """Import Token 成绩上传。使用该资源时 client token 应为用户 Import Token。"""

    def records(self, payload: Mapping[str, Any]) -> dict:
        """``POST /import/records`` —— 上传加工后的成绩 JSON。"""
        return self._client._request("POST", "/import/records", json=dict(payload))


class ScoreRecognitionResource(_BaseResource):
    """maimai result-photo recognition."""

    @staticmethod
    def _upload(image: bytes, filename: str) -> dict:
        if not isinstance(image, (bytes, bytearray, memoryview)) or not image:
            raise ValueError("image must be non-empty bytes")
        return {
            "image": (filename, bytes(image), "application/octet-stream"),
        }

    def recognize(
        self,
        image: bytes,
        ver: str = "jp",
        filename: str = "score.jpg",
        timeout: float = 180.0,
    ) -> dict:
        """``POST /score-recognition`` with a JPEG, PNG, or WebP image."""
        return self._client._request(
            "POST",
            "/score-recognition",
            data={"ver": ver},
            files=self._upload(image, filename),
            timeout=timeout,
        )

    def recognize_image(
        self,
        image: bytes,
        ver: str = "jp",
        filename: str = "score.jpg",
        timeout: float = 180.0,
    ) -> bytes:
        """``POST /score-recognition/image`` and return the OCR result PNG."""
        return self._client._request(
            "POST",
            "/score-recognition/image",
            data={"ver": ver},
            files=self._upload(image, filename),
            timeout=timeout,
            binary=True,
        )


# ============================================================
# 主 client
# ============================================================

class jietngClient:
    """同步 JiETNG API 客户端。

    Example::

        from jietng import jietngClient

        client = jietngClient(token="your_token")
        users = client.users.list()
        b50_png = client.images.records("U123", command="b50")
        with open("b50.png", "wb") as f:
            f.write(b50_png)
    """

    def __init__(
        self,
        token: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        extra_headers: Optional[Mapping[str, str]] = None,
        transport: Optional[httpx.BaseTransport] = None,
    ):
        if not token:
            raise ValueError("token is required")
        self._token = token
        self._base_url = base_url.rstrip("/")
        self._headers = _build_headers(token, extra_headers)
        self._http = httpx.Client(
            base_url=self._base_url,
            headers=self._headers,
            timeout=timeout,
            transport=transport,
        )

        # Resource 命名空间
        self.users = UsersResource(self)
        self.permissions = PermissionsResource(self)
        self.songs = SongsResource(self)
        self.versions = VersionsResource(self)
        self.dxdata = DxdataResource(self)
        self.images = ImagesResource(self)
        self.exports = ExportsResource(self)
        self.imports = ImportsResource(self)
        self.score_recognition = ScoreRecognitionResource(self)

    # ---- context manager ----

    def __enter__(self) -> "jietngClient":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def close(self) -> None:
        self._http.close()

    # ---- 内部请求方法 ----

    def _request(self, method: str, path: str, *, binary: bool = False, **kwargs: Any) -> Any:
        resp = self._http.request(method, path, **kwargs)
        if binary:
            return _binary_response(resp)
        return _check_response(resp)

    def _request_with_filename(
        self, method: str, path: str, **kwargs: Any,
    ) -> Tuple[bytes, Optional[str]]:
        resp = self._http.request(method, path, **kwargs)
        content = _binary_response(resp)
        return content, _attachment_filename(resp)
