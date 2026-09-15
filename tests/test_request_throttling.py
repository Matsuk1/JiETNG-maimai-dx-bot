"""Request admission and cleanup share the same state and lock."""
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import pytest

from modules import task_runtime as runtime


@pytest.fixture(autouse=True)
def isolated_tracking():
    with patch.object(runtime, 'user_request_tracking', {}):
        yield


def test_concurrent_requests_admit_only_the_limit():
    with patch.object(runtime.time, 'time', return_value=100):
        with ThreadPoolExecutor(max_workers=8) as pool:
            rejected = list(pool.map(lambda _: runtime.check_rate_limit('user', 'info'), range(20)))
        assert rejected.count(False) == runtime.MAX_SAME_REQUESTS
        assert runtime.check_rate_limit('user', 'record') is False
        assert runtime.check_rate_limit('other', 'info') is False


def test_expiry_and_cleanup_preserve_active_requests():
    with patch.object(runtime.time, 'time', return_value=100):
        for _ in range(runtime.MAX_SAME_REQUESTS):
            assert runtime.check_rate_limit('expired', 'info') is False
        assert runtime.check_rate_limit('expired', 'info') is True
    with patch.object(runtime.time, 'time', return_value=110):
        assert runtime.check_rate_limit('active', 'record') is False
    with patch.object(runtime.time, 'time', return_value=120):
        assert runtime.cleanup_rate_limiter_tracking() == runtime.MAX_SAME_REQUESTS + 1
        assert runtime.user_request_tracking == {'active': {'record': [110]}}
        assert runtime.check_rate_limit('expired', 'info') is False
        assert runtime.cleanup_rate_limiter_tracking() == 0
