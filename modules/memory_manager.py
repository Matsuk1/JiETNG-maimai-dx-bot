"""Periodic garbage collection and application-cache cleanup."""

import gc
import logging
import threading
import time
from datetime import datetime

logger = logging.getLogger(__name__)


class MemoryManager:
    def __init__(self, interval_seconds=300):
        self.interval = interval_seconds
        self.running = False
        self.thread = None
        self.last_cleanup_time = None
        self.last_cleanup_stats = None
        self._stop_event = threading.Event()
        self._callbacks = []
        self._lock = threading.Lock()

    def register_cleanup(self, callback):
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def start(self):
        with self._lock:
            if self.running:
                return
            self.running = True
            self._stop_event.clear()
            self.thread = threading.Thread(
                target=self._cleanup_loop,
                daemon=True,
                name="MemoryManager",
            )
            self.thread.start()
        logger.info("[Memory] Manager started: interval=%ss", self.interval)

    def stop(self):
        with self._lock:
            if not self.running:
                return
            self.running = False
            self._stop_event.set()
            thread = self.thread
        if thread:
            thread.join(timeout=5)
        logger.info("[Memory] Manager stopped")

    def _cleanup_loop(self):
        while not self._stop_event.wait(self.interval):
            try:
                self.cleanup()
            except Exception:
                logger.exception("[Memory] Cleanup error")

    def cleanup(self):
        started = time.perf_counter()
        counts_before = gc.get_count()
        collected = gc.collect(2)
        self.last_cleanup_time = datetime.now()
        stats = {
            "timestamp": self.last_cleanup_time.strftime("%Y-%m-%d %H:%M:%S"),
            "collected_objects": collected,
            "collected_by_generation": {"gen2": collected},
            "gc_counts_before": counts_before,
            "elapsed_ms": int((time.perf_counter() - started) * 1000),
        }
        self.last_cleanup_stats = stats
        logger.debug(
            "[Memory] Cleanup completed: collected=%s, elapsed=%sms",
            stats["collected_objects"],
            stats["elapsed_ms"],
        )
        for callback in tuple(self._callbacks):
            try:
                callback()
            except Exception:
                logger.exception("[Memory] Registered cleanup failed: %r", callback)
        return stats

    def get_stats(self):
        current_counts = gc.get_count()
        previous_counts = (
            self.last_cleanup_stats.get("gc_counts_before")
            if self.last_cleanup_stats
            else current_counts
        )
        return {
            "running": self.running,
            "interval_seconds": self.interval,
            "last_cleanup": (
                self.last_cleanup_time.strftime("%Y-%m-%d %H:%M:%S")
                if self.last_cleanup_time else "Never"
            ),
            "gc_counts": previous_counts,
            "gc_counts_current": current_counts,
            "gc_threshold": gc.get_threshold(),
            "last_cleanup_stats": self.last_cleanup_stats,
        }


def cleanup_user_caches(user_manager_module=None):
    if user_manager_module is None or not hasattr(user_manager_module, "nickname_cache"):
        return 0
    now = time.monotonic()
    cache = user_manager_module.nickname_cache
    timeout = user_manager_module.NICKNAME_CACHE_TIMEOUT
    with user_manager_module.nickname_cache_lock:
        expired = [
            user_id
            for user_id, item in cache.items()
            if now - item.get("cached_at", now) >= timeout
        ]
        for user_id in expired:
            cache.pop(user_id, None)
    if expired:
        logger.debug("[Memory] Cleaned nickname cache: count=%s", len(expired))
    return len(expired)


def cleanup_rate_limiter_tracking(rate_limiter_module=None):
    if rate_limiter_module is None or not hasattr(rate_limiter_module, "user_request_tracking"):
        return 0
    now = time.time()
    tracking = rate_limiter_module.user_request_tracking
    window = rate_limiter_module.REQUEST_LIMIT_WINDOW
    cleaned = 0
    with rate_limiter_module.user_request_lock:
        for user_id, task_types in list(tracking.items()):
            for task_type, timestamps in list(task_types.items()):
                valid = [timestamp for timestamp in timestamps if now - timestamp < window]
                cleaned += len(timestamps) - len(valid)
                if valid:
                    task_types[task_type] = valid
                else:
                    task_types.pop(task_type, None)
            if not task_types:
                tracking.pop(user_id, None)
                cleaned += 1
    if cleaned:
        logger.debug("[Memory] Cleaned rate-limit tracking: count=%s", cleaned)
    return cleaned


memory_manager = MemoryManager(interval_seconds=120)
