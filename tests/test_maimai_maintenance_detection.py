import asyncio
from http.cookies import SimpleCookie
from unittest.mock import AsyncMock

import aiohttp
import pytest

from modules import maimai_manager as maimai


class Response:
    def __init__(self, html="", status=200, error=None):
        self.html = html
        self.status = status
        self.error = error

    async def __aenter__(self):
        if self.error:
            raise self.error
        return self

    async def __aexit__(self, *args):
        pass

    def raise_for_status(self):
        pass

    async def text(self):
        return self.html


class Session:
    def __init__(self, response):
        self.response = response
        self.closed = False
        self.requests = []
        self.cookie_jar = self

    def filter_cookies(self, url):
        return SimpleCookie()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        self.closed = True

    def get(self, url, **kwargs):
        self.requests.append(("get", url, kwargs))
        return self.response if url.endswith("/login/") else Response()

    def post(self, url, **kwargs):
        self.requests.append(("post", url, kwargs))
        return Response()


def install_sessions(monkeypatch, responses):
    sessions = []

    def create(*args, **kwargs):
        session = Session(responses[len(sessions)])
        sessions.append(session)
        return session

    monkeypatch.setattr(maimai, "_create_session", create)
    monkeypatch.setattr(maimai.asyncio, "sleep", AsyncMock())
    return sessions


@pytest.mark.parametrize("status", [502, 503, 504])
def test_jp_gateway_outage_is_reported_as_maintenance(monkeypatch, status):
    sessions = install_sessions(monkeypatch, [Response(status=status)])

    assert asyncio.run(maimai.login_to_maimai("test-id", "test-password")) == "MAINTENANCE"
    assert len(sessions) == 1
    assert len(sessions[0].requests) == 1


@pytest.mark.parametrize(
    "html",
    [
        "<html><title>メンテナンス中</title><body>しばらくお待ちください</body></html>",
        "<html><title>Maintenance</title><body>Service temporarily unavailable</body></html>",
    ],
)
def test_jp_success_status_maintenance_page_is_not_rate_limit(monkeypatch, html):
    sessions = install_sessions(monkeypatch, [Response(html=html, status=200)])

    assert asyncio.run(maimai.login_to_maimai("test-id", "test-password")) == "MAINTENANCE"
    assert len(sessions) == 1
    assert not any(method == "post" for method, _, _ in sessions[0].requests)


def test_jp_connection_outage_is_reported_as_maintenance(monkeypatch):
    sessions = install_sessions(
        monkeypatch,
        [Response(error=aiohttp.ClientConnectionError("official site unavailable"))],
    )

    assert asyncio.run(maimai.login_to_maimai("test-id", "test-password")) == "MAINTENANCE"
    assert len(sessions) == 1


def test_generic_login_failure_keeps_existing_retry_and_error_behavior(monkeypatch):
    sessions = install_sessions(monkeypatch, [Response(error=RuntimeError("broken"))] * 3)

    with pytest.raises(RuntimeError, match="after 3 fresh sessions"):
        asyncio.run(maimai.login_to_maimai("test-id", "test-password"))

    assert len(sessions) == 3


def test_fetch_dom_reports_maintenance_html_and_connection_outage(monkeypatch):
    class DirectSession:
        def __init__(self, response):
            self.response = response

        def get(self, *args, **kwargs):
            return self.response

    maintenance_page = Response("<html><body>現在メンテナンス中です</body></html>")
    assert asyncio.run(maimai.fetch_dom(DirectSession(maintenance_page), "https://maimaidx.jp/home/")) == "MAINTENANCE"

    connection_error = Response(error=aiohttp.ClientConnectionError("offline"))
    assert asyncio.run(maimai.fetch_dom(DirectSession(connection_error), "https://maimaidx.jp/home/")) == "MAINTENANCE"


def test_binding_propagates_home_page_maintenance():
    import ast
    from pathlib import Path

    source = Path(__file__).resolve().parents[1] / "main.py"
    function = next(
        node
        for node in ast.parse(source.read_text()).body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "process_sega_credentials"
    )

    class Connector:
        pass

    class ClientSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

    class Aiohttp:
        TCPConnector = staticmethod(lambda **kwargs: Connector())
        ClientTimeout = staticmethod(lambda **kwargs: object())
        ClientSession = staticmethod(lambda **kwargs: ClientSession())

    namespace = {
        "DEFAULT_WEB_LANGUAGE": "zh",
        "login_to_maimai": AsyncMock(return_value={"cookie": "value"}),
        "fetch_dom": AsyncMock(return_value="MAINTENANCE"),
        "aiohttp": Aiohttp,
    }
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(source), "exec"), namespace)

    result = asyncio.run(namespace["process_sega_credentials"]("user", "id", "password"))
    assert result == "MAINTENANCE"
