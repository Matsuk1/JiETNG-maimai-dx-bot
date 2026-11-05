from datetime import datetime
from threading import Lock
from unittest.mock import patch

from modules import event_tracker
from modules.task_runtime import summarize_task_activity


def reset_cache():
    event_tracker._stats_cache.update(ts=0.0, data=None)


def test_db_failure_with_cache_is_flagged_and_keeps_snapshot_time():
    reset_cache()
    with patch.object(event_tracker, "_compute_business_stats", return_value=({"dau": 5}, True)):
        fresh = event_tracker.get_business_stats(force_refresh=True)
    assert fresh["business_stats_ok"] is True

    with patch.object(event_tracker, "_compute_business_stats", return_value=({"dau": 0}, False)):
        stale = event_tracker.get_business_stats(force_refresh=True)
    assert stale["dau"] == 5
    assert stale["business_stats_ok"] is False
    assert stale["business_stats_at"] == fresh["business_stats_at"]
    assert event_tracker._stats_cache["data"]["business_stats_ok"] is True
    reset_cache()


def test_db_failure_without_cache_reports_no_snapshot():
    reset_cache()
    with patch.object(event_tracker, "_compute_business_stats", return_value=({"dau": 0}, False)):
        stats = event_tracker.get_business_stats(force_refresh=True)
    assert stats["business_stats_ok"] is False
    assert stats["business_stats_at"] is None
    reset_cache()


def test_hourly_stats_flags_db_failure():
    with patch.object(event_tracker, "database_cursor", side_effect=RuntimeError("down")):
        assert event_tracker.get_hourly_stats("2026-11-05")["ok"] is False


def test_task_activity_summary():
    tracking = {
        "running": [
            {"id": 1, "started_at": "2026-11-05 12:00:00"},
            {"id": 2, "started_at": "2026-11-05 12:01:30"},
            {"id": 3},
        ],
        "completed": [
            {"function": "ok", "error": None},
            {"function": "render", "error": "TimeoutError: slow", "finished_at": "2026-11-05 11:59:00", "user_id": "U1"},
            {"function": "older", "error": "ValueError: x"},
        ],
    }
    summary = summarize_task_activity(tracking, Lock(), now=datetime(2026, 11, 5, 12, 2, 0))
    assert summary == {
        "running_tasks": 3,
        "longest_running_seconds": 120,
        "last_task_failure": {
            "function": "render",
            "error": "TimeoutError: slow",
            "finished_at": "2026-11-05 11:59:00",
        },
    }


def test_task_activity_summary_when_idle():
    summary = summarize_task_activity({"running": [], "completed": []}, Lock())
    assert summary == {"running_tasks": 0, "longest_running_seconds": 0, "last_task_failure": None}
