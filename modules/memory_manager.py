"""Periodic garbage collection and application-cache cleanup."""

import gc
import logging
import threading
import time
from datetime import datetime

import psutil

logger = logging.getLogger(__name__)


def get_process_memory_stats():
    """Sample component RSS for this worker and its descendants."""
    root = psutil.Process()
    complete = True
    try:
        children = root.children(recursive=True)
    except psutil.Error:
        children = []
        complete = False
    processes = {}
    for process in [root, *children]:
        if process.pid in processes:
            continue
        ppid, rss, component = None, None, None
        try:
            with process.oneshot():
                ppid = process.ppid()
                rss = process.memory_info().rss
        except psutil.NoSuchProcess:
            continue
        except psutil.AccessDenied:
            complete = False
        try:
            argv = process.cmdline()
            if any(arg.replace(chr(92), '/').split('/')[-1] == 'table_model.py' for arg in argv):
                component = 'ocr'
            elif any('playwright' in arg.lower() for arg in argv[:2]):
                component = 'playwright'
            elif argv and any(name in argv[0].lower() for name in ('chrome', 'chromium')):
                component = 'playwright'
        except psutil.Error:
            pass
        processes[process.pid] = dict(ppid=ppid, rss=rss, component=component)

    components = {
        key: dict(key=key, name=name, description=description, rss=0, complete=complete)
        for key, name, description in [
            ('service', 'Service', 'Main service including in-process OCR and YOLO; their RSS cannot be separated.'),
            ('ocr', 'OCR', 'Dedicated table OCR process. Main OCR and YOLO are included in Service.'),
            ('playwright', 'Playwright', 'Playwright driver and all browser processes.'),
            ('other', 'Other', 'Other service subprocesses.'),
        ]
    }
    for pid, process in processes.items():
        component = 'service' if pid == root.pid else 'other'
        current, seen = pid, set()
        while current in processes and current not in seen and pid != root.pid:
            seen.add(current)
            ancestor = processes[current]
            if ancestor['component']:
                component = ancestor['component']
                break
            current = ancestor['ppid']
        group = components[component]
        if process['rss'] is None:
            group['complete'] = False
        else:
            group['rss'] += process['rss']
    total = sum(group['rss'] for group in components.values())
    rows = []
    for group in components.values():
        rss = group.pop('rss')
        group['memory_mb'] = round(rss / 1024 ** 2, 1) if group['complete'] else None
        group['percent'] = round(rss / total * 100, 1) if total else 0
        rows.append(group)
    main_rss = processes.get(root.pid, {}).get('rss')
    return dict(process_memory_mb=round(main_rss / 1024 ** 2, 1) if main_rss is not None else None,
                process_tree_memory_mb=round(total / 1024 ** 2, 1),
                process_memory_complete=complete, memory_components=rows)


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


memory_manager = MemoryManager(interval_seconds=120)
