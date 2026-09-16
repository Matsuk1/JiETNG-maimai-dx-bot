import asyncio
from http.cookies import SimpleCookie
from unittest.mock import AsyncMock

import pytest

from modules import maimai_manager as maimai


class Response:
    def __init__(self, html='', status=200, error=None):
        self.html, self.status, self.error = html, status, error

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
        self.requests.append(('get', url, kwargs))
        if url.endswith('/login/'):
            assert kwargs['timeout'].total == 15
            assert kwargs['timeout'].connect == 5
            return self.response
        return Response('<html></html>')

    def post(self, url, **kwargs):
        assert not self.closed
        self.requests.append(('post', url, kwargs))
        return Response()


def install_sessions(monkeypatch, responses):
    sessions = []

    def create(*args, **kwargs):
        assert kwargs["timeout"].total == 15
        assert kwargs["timeout"].connect == 5
        assert all(session.closed for session in sessions)
        session = Session(responses[len(sessions)])
        sessions.append(session)
        return session

    monkeypatch.setattr(maimai, '_create_session', create)
    monkeypatch.setattr(maimai.asyncio, 'sleep', AsyncMock())
    return sessions


@pytest.mark.parametrize('entrypoint', [maimai.login_to_maimai, maimai.get_aime_candidates])
@pytest.mark.parametrize('first', [Response('<html>No token</html>'), Response(error=TimeoutError())])
def test_failed_session_is_closed_and_fresh_session_used_for_post(monkeypatch, entrypoint, first):
    sessions = install_sessions(monkeypatch, [first, Response('<input name="token" value="fresh">')])
    asyncio.run(entrypoint('test-id', 'test-password'))
    assert len(sessions) == 2
    assert all(session.closed for session in sessions)
    assert not any(method == 'post' for method, _, _ in sessions[0].requests)
    posts = [kwargs for method, _, kwargs in sessions[1].requests if method == 'post']
    assert len(posts) == 1
    assert posts[0]['data']['token'] == 'fresh'


def test_exhaustion_closes_all_three_sessions(monkeypatch):
    sessions = install_sessions(monkeypatch, [Response()] * 3)
    with pytest.raises(RuntimeError, match='after 3 fresh sessions'):
        asyncio.run(maimai.login_to_maimai('test-id', 'test-password'))
    assert len(sessions) == 3
    assert all(session.closed for session in sessions)


@pytest.mark.parametrize('entrypoint', [maimai.login_to_maimai, maimai.get_aime_candidates])
def test_maintenance_does_not_retry_or_submit(monkeypatch, entrypoint):
    sessions = install_sessions(monkeypatch, [Response(status=503)])
    assert asyncio.run(entrypoint('test-id', 'test-password')) == 'MAINTENANCE'
    assert len(sessions) == 1 and sessions[0].closed
    assert len(sessions[0].requests) == 1


@pytest.mark.parametrize('error', [RuntimeError('caller failed'), asyncio.CancelledError()])
def test_caller_failure_or_cancellation_closes_session_without_retry(monkeypatch, error):
    sessions = install_sessions(monkeypatch, [Response('<input name="token" value="fresh">')])

    async def run():
        async with maimai._jp_login_session({}):
            raise error

    with pytest.raises(type(error)):
        asyncio.run(run())
    assert len(sessions) == 1 and sessions[0].closed


def test_cancelled_token_fetch_closes_session_without_retry(monkeypatch):
    sessions = install_sessions(monkeypatch, [Response(error=asyncio.CancelledError())])
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(maimai.login_to_maimai('test-id', 'test-password'))
    assert len(sessions) == 1 and sessions[0].closed


@pytest.mark.parametrize('ver', ['jp', 'intl'])
@pytest.mark.parametrize('failed_page', [None, 'MAINTENANCE'])
def test_friend_records_reject_partial_results(monkeypatch, ver, failed_page):
    sessions = install_sessions(monkeypatch, [Response()])
    page = maimai.etree.HTML('<html></html>')
    fetch = AsyncMock(side_effect=[page, page, failed_page, page, page])
    monkeypatch.setattr(maimai, 'fetch_dom', fetch)
    result = asyncio.run(maimai.get_friend_records({}, 'test-friend', ver))
    assert result == failed_page
    assert fetch.await_count == 5
    assert sessions[0].closed


def test_friend_info_request_timeout_closes_session(monkeypatch):
    sessions = install_sessions(monkeypatch, [Response()])
    monkeypatch.setattr(Session, 'get', lambda *args, **kwargs: Response(error=TimeoutError()))
    assert asyncio.run(maimai.get_friend_info({}, 'test-friend')) == {}
    assert sessions[0].closed


def test_friend_records_request_timeouts_do_not_return_empty_success(monkeypatch):
    sessions = install_sessions(monkeypatch, [Response()])
    monkeypatch.setattr(Session, 'get', lambda *args, **kwargs: Response(error=TimeoutError()))
    assert asyncio.run(maimai.get_friend_records({}, 'test-friend')) is None
    assert sessions[0].closed
