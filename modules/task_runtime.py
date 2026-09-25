"""Request throttling, bounded task execution, and admin tracking."""

import logging
import queue
import sys
import threading
import time
import traceback
from dataclasses import dataclass
from datetime import datetime
from typing import Any


logger = logging.getLogger(__name__)

# Per-user, per-task timestamps; reads and cleanup share this lock.
user_request_tracking = {}
user_request_lock = threading.Lock()
REQUEST_LIMIT_WINDOW = 20
MAX_SAME_REQUESTS = 4


def _format_thread_stack(thread: threading.Thread | None) -> str:
    """Capture where a still-running task was blocked when it timed out."""
    if thread is None or thread.ident is None:
        return "Task timed out before its execution thread could be inspected."
    frame = sys._current_frames().get(thread.ident)
    if frame is None:
        return "Task execution thread exited before its stack could be inspected."
    return (
        "Task timed out while its execution thread was still running.\n"
        "Stack snapshot at timeout (most recent call last):\n"
        + "".join(traceback.format_stack(frame))
    )


@dataclass(frozen=True, slots=True)
class TaskContext:
    user_id: str | None = None
    reply_token: str | None = None
    source_type: str = "user"


@dataclass(frozen=True, slots=True)
class TaskOutcome:
    status: str
    duration: float
    error: str | None = None


def task_context(args: tuple[Any, ...]) -> TaskContext:
    if not args:
        return TaskContext()
    first = args[0]
    if hasattr(first, "user_id") and hasattr(first, "source_type"):
        return TaskContext(first.user_id, first.reply_token, first.source_type)
    if hasattr(first, "source"):
        source = first.source
        return TaskContext(
            user_id=getattr(source, "user_id", None),
            reply_token=getattr(first, "reply_token", None),
            source_type=getattr(source, "type", "user"),
        )
    if isinstance(first, str) and first.startswith("U"):
        reply_token = args[1] if len(args) > 1 and isinstance(args[1], str) else None
        return TaskContext(user_id=first, reply_token=reply_token)
    return TaskContext()


def track_queued(tracking: dict, lock: threading.Lock, task: dict) -> None:
    with lock:
        tracking["queued"].append(task)


def discard_queued(tracking: dict, lock: threading.Lock, task_id: str) -> None:
    with lock:
        tracking["queued"] = [
            item for item in tracking["queued"] if item.get("id") != task_id
        ]


def _start_tracking(task_id, func, context, tracking, lock):
    if not task_id:
        return
    with lock:
        queued = next(
            (dict(item) for item in tracking["queued"] if item.get("id") == task_id),
            {},
        )
        tracking["queued"] = [item for item in tracking["queued"] if item.get("id") != task_id]
        tracking["running"].append(
            {
                **queued,
                "id": task_id,
                "function": queued.get("function", func.__name__),
                "user_id": queued.get("user_id", context.user_id or "Unknown"),
                "started_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        )


def _finish_tracking(task_id, outcome, tracking, lock, max_completed):
    if not task_id:
        return
    with lock:
        completed = next(
            (dict(item) for item in tracking["running"] if item.get("id") == task_id),
            None,
        )
        tracking["running"] = [item for item in tracking["running"] if item.get("id") != task_id]
        if completed:
            completed.update(
                {
                    "status": outcome.status,
                    "duration": round(outcome.duration, 3),
                    "error": outcome.error,
                    "finished_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
            )
            tracking["completed"].insert(0, completed)
            del tracking["completed"][max_completed:]


def execute_task(
    func,
    args,
    semaphore,
    *,
    task_id=None,
    tracking,
    tracking_lock,
    max_completed=20,
    timeout=120,
    logger,
    on_error=None,
    on_complete=None,
):
    context = task_context(args)
    _start_tracking(task_id, func, context, tracking, tracking_lock)
    started = time.monotonic()
    deadline = started + max(0, timeout)
    errors = []
    done = threading.Event()
    thread = None

    def target():
        try:
            func(*args)
        except Exception as exc:
            errors.append((exc, traceback.format_exc()))
            logger.exception("[Task] Execution error: function=%s", func.__name__)
        finally:
            # A timed-out Python thread may still be executing. It owns its
            # capacity until it exits; releasing here prevents unbounded work.
            semaphore.release()
            done.set()

    acquired = semaphore.acquire(timeout=max(0, deadline - time.monotonic()))
    if acquired:
        thread = threading.Thread(target=target, daemon=True)
        try:
            thread.start()
        except Exception:
            semaphore.release()
            raise
        finished = done.wait(max(0, deadline - time.monotonic()))
    else:
        finished = False

    error = None
    error_traceback = ""
    if not finished:
        status = "timed_out"
        phase = "execution" if acquired else "capacity wait"
        error = TimeoutError(f"Task {phase} exceeded {timeout}s")
        if acquired:
            error_traceback = _format_thread_stack(thread)
        else:
            error_traceback = (
                "Task timed out waiting for worker capacity; its function did not start.\n"
                "Another task is still holding this queue's concurrency slot."
            )
        logger.warning("[Task] %s: function=%s", error, func.__name__)
    elif errors:
        status = "failed"
        error, error_traceback = errors[0]
    else:
        status = "completed"
    outcome = TaskOutcome(
        status=status,
        duration=time.monotonic() - started,
        error=f"{type(error).__name__}: {error}" if error else None,
    )
    _finish_tracking(task_id, outcome, tracking, tracking_lock, max_completed)
    if on_complete:
        on_complete(func, outcome)
    if error and on_error:
        on_error(func, error, context, error_traceback)
    return outcome


def queue_worker(task_queue: queue.Queue, run_item) -> None:
    while True:
        item = task_queue.get()
        try:
            run_item(item)
        finally:
            task_queue.task_done()


def check_rate_limit(user_id: str, task_type: str) -> bool:
    """
    检查用户请求是否超过频率限制

    Args:
        user_id: 用户ID
        task_type: 任务类型（如 'maimai_update', 'b50' 等）

    Returns:
        bool: True 表示超过限制（应该拒绝），False 表示可以继续
    """
    now = time.time()

    with user_request_lock:
        requests_by_type = user_request_tracking.setdefault(user_id, {})
        timestamps = requests_by_type.setdefault(task_type, [])
        timestamps[:] = [
            timestamp
            for timestamp in timestamps
            if now - timestamp < REQUEST_LIMIT_WINDOW
        ]

        if len(timestamps) >= MAX_SAME_REQUESTS:
            logger.warning(
                "[RateLimit] Limit exceeded: user_id=%s task_type=%s",
                user_id,
                task_type,
            )
            return True

        timestamps.append(now)
        return False


def cleanup_rate_limiter_tracking() -> int:
    """Discard expired request timestamps and empty user entries."""
    now = time.time()
    tracking = user_request_tracking
    window = REQUEST_LIMIT_WINDOW
    cleaned = 0
    with user_request_lock:
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
