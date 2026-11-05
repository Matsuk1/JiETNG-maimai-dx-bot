"""
事件追踪与业务指标聚合模块

记录业务事件（webhook 调用、图片生成、绑定、同步任务等），
并提供 DAU/WAU/MAU 等指标聚合查询。
"""

import json
import logging
import queue
import threading
import time
from datetime import datetime, timedelta
from modules.dbpool_manager import database_cursor

# events 表保留天数（超过后由后台任务清理）
EVENTS_RETENTION_DAYS = 90

# 批量 flush 参数
_BATCH_MAX_SIZE = 100
_BATCH_MAX_WAIT = 1.0  # 秒

# get_business_stats 结果 TTL 缓存（秒）
_STATS_CACHE_TTL = 60

logger = logging.getLogger(__name__)

_init_lock = threading.Lock()
_initialized = False

# 后台事件写入队列：避免在 webhook / API 热路径上阻塞 DB
_event_queue = queue.Queue(maxsize=10000)
_worker_started = False
_worker_lock = threading.Lock()
_worker_thread = None
_purge_thread = None
_stop_event = threading.Event()
_STOP = object()
_health_lock = threading.Lock()
_retried_events = 0
_dropped_events = 0
_last_write_error = None
_MAX_WRITE_ATTEMPTS = 3


def _record_health(*, retried=0, dropped=0, error=None):
    global _retried_events, _dropped_events, _last_write_error
    with _health_lock:
        _retried_events += retried
        _dropped_events += dropped
        if error is not None:
            _last_write_error = str(error)[:300]


def get_tracker_health():
    with _health_lock:
        return {
            "event_queue_size": _event_queue.qsize(),
            "event_retried": _retried_events,
            "event_dropped": _dropped_events,
            "event_last_error": _last_write_error,
        }


def _flush_batch(batch):
    """批量写入一组事件；失败时记录日志，行丢弃。"""
    if not batch:
        return
    # 元组顺序对齐 INSERT 列：(user_id, event_type, metadata)
    rows = [(uid, event_type, metadata) for event_type, uid, metadata, _ in batch]
    try:
        with database_cursor(write=True) as (_, cursor):
            cursor.executemany(
                "INSERT INTO events (user_id, event_type, metadata) VALUES (%s, %s, %s)",
                rows,
            )
    except Exception as error:
        retried = dropped = 0
        for event_type, uid, metadata, attempts in batch:
            if attempts < _MAX_WRITE_ATTEMPTS and not _stop_event.is_set():
                try:
                    _event_queue.put_nowait((event_type, uid, metadata, attempts + 1))
                    retried += 1
                    continue
                except queue.Full:
                    pass
            dropped += 1
        _record_health(retried=retried, dropped=dropped, error=error)
        logger.error(
            "[EventTracker] batch insert failed: size=%s retried=%s dropped=%s error=%s",
            len(batch), retried, dropped, error,
        )
        if retried:
            time.sleep(min(2 ** max(item[3] for item in batch), 8))


def _event_worker():
    """后台线程：从队列取事件，按 batch 合并后写入 DB。"""
    while True:
        first = _event_queue.get()
        if first is _STOP:
            _event_queue.task_done()
            return
        batch = [first]
        stop_after_batch = False
        deadline = time.monotonic() + _BATCH_MAX_WAIT
        while len(batch) < _BATCH_MAX_SIZE:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            try:
                item = _event_queue.get(timeout=remaining)
                if item is _STOP:
                    _event_queue.task_done()
                    stop_after_batch = True
                    break
                batch.append(item)
            except queue.Empty:
                break
        try:
            _flush_batch(batch)
        finally:
            for _ in batch:
                _event_queue.task_done()
        if stop_after_batch:
            return


def _purge_loop():
    """每 24 小时清理一次历史 events。"""
    while not _stop_event.is_set():
        try:
            purge_old_events()
        except Exception as e:
            logger.error("[EventTracker] purge loop error: %s", e)
        _stop_event.wait(24 * 3600)


def _ensure_worker():
    global _worker_started, _worker_thread
    if _worker_started:
        return
    with _worker_lock:
        if _worker_started:
            return
        _worker_thread = threading.Thread(
            target=_event_worker,
            name="event-tracker-worker",
            daemon=True,
        )
        _worker_thread.start()
        _worker_started = True


def init_events_table():
    """初始化 events 表（启动时调用）"""
    global _initialized, _purge_thread
    with _init_lock:
        if _initialized:
            return
        try:
            with database_cursor(write=True) as (_, cursor):
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS events (
                        id BIGINT AUTO_INCREMENT PRIMARY KEY,
                        user_id VARCHAR(64) NULL,
                        event_type VARCHAR(32) NOT NULL,
                        metadata JSON NULL,
                        ts DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_ts (ts),
                        INDEX idx_event_ts (event_type, ts),
                        INDEX idx_user_ts (user_id, ts)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)
            _initialized = True
            logger.info("[EventTracker] events table ready")
            _purge_thread = threading.Thread(
                target=_purge_loop,
                name="event-tracker-purge",
                daemon=True,
            )
            _purge_thread.start()
        except Exception as e:
            logger.error("[EventTracker] init table failed: %s", e)


def purge_old_events(retention_days: int = EVENTS_RETENTION_DAYS) -> int:
    """删除超过保留期的 events 行，返回删除行数。分批删除避免长事务。"""
    total = 0
    try:
        with database_cursor(write=True) as (connection, cursor):
            while True:
                cursor.execute(
                    "DELETE FROM events WHERE ts < DATE_SUB(NOW(), INTERVAL %s DAY) LIMIT 5000",
                    (retention_days,),
                )
                connection.commit()
                affected = cursor.rowcount or 0
                total += affected
                if affected < 5000:
                    break
        if total:
            logger.info(
                "[EventTracker] purged %s old events (> %sd)", total, retention_days
            )
    except Exception as e:
        logger.error("[EventTracker] purge_old_events failed: %s", e)
    return total


def track_event(
    event_type: str, user_id: str | None = None, metadata: dict | None = None
):
    """记录一个业务事件（非阻塞）。队列满或序列化失败时静默丢弃。"""
    if _stop_event.is_set():
        return
    try:
        metadata_json = json.dumps(metadata, ensure_ascii=False) if metadata else None
        _ensure_worker()
        _event_queue.put_nowait((event_type, user_id, metadata_json, 0))
    except queue.Full:
        _record_health(dropped=1, error="event queue full")
        logger.warning("[EventTracker] queue full, dropping event: %s", event_type)
    except Exception as e:
        _record_health(dropped=1, error=e)
        logger.error("[EventTracker] track_event(%s) enqueue failed: %s", event_type, e)


def shutdown_event_tracker(timeout: float = 5.0) -> None:
    """Flush queued events and stop tracker background threads."""
    _stop_event.set()
    if _worker_started and _worker_thread is not None:
        try:
            _event_queue.put(_STOP, timeout=timeout)
        except queue.Full:
            logger.warning("[EventTracker] queue remained full during shutdown")
        _worker_thread.join(timeout=timeout)
        if _worker_thread.is_alive():
            logger.warning("[EventTracker] worker did not stop within %.1fs", timeout)
    if _purge_thread is not None:
        _purge_thread.join(timeout=timeout)


def _scalar(cursor, sql, args=()):
    cursor.execute(sql, args)
    row = cursor.fetchone()
    return row[0] if row else 0


def _activity_stats(cursor, date_filter, args=()):
    def count(event_type, *, distinct=False, success=False):
        field = "DISTINCT user_id" if distinct else "*"
        success_filter = (
            " AND JSON_UNQUOTE(JSON_EXTRACT(metadata, '$.success')) = 'true'"
            if success
            else ""
        )
        return _scalar(
            cursor,
            f"SELECT COUNT({field}) FROM events WHERE event_type=%s AND {date_filter}{success_filter}",
            (event_type, *args),
        )

    sync_total = count("sync_task")
    sync_success = count("sync_task", success=True)
    bindings = _scalar(
        cursor,
        "SELECT COUNT(DISTINCT user_id) FROM events "
        f"WHERE event_type IN ('user_bind','user_rebind') AND user_id IS NOT NULL AND {date_filter}",
        args,
    )
    return {
        "image_calls": count("image_gen"),
        "webhook_msgs": count("line_webhook"),
        "record_exports": count("record_export"),
        "record_imports": count("record_import"),
        "bindings": bindings,
        "unbinds": count("user_unbind", distinct=True),
        "sync_total": sync_total,
        "sync_success": sync_success,
        "sync_success_rate": round(sync_success / sync_total * 100, 1) if sync_total else 0.0,
        "sync_failures": _sync_failures(cursor, date_filter, args),
    }


def _sync_failures(cursor, date_filter, args=()):
    # JSON null 经 JSON_UNQUOTE 后是字符串 'null'
    cursor.execute(
        "SELECT NULLIF(JSON_UNQUOTE(JSON_EXTRACT(metadata, '$.error')), 'null') AS reason, COUNT(*) AS cnt "
        "FROM events WHERE event_type='sync_task' "
        f"AND JSON_UNQUOTE(JSON_EXTRACT(metadata, '$.success')) = 'false' AND {date_filter} "
        "GROUP BY reason ORDER BY cnt DESC LIMIT 5",
        args,
    )
    return [{"reason": reason or "Unknown", "count": count} for reason, count in cursor.fetchall()]


def _hourly_distribution(cursor, date_filter, args=()):
    cursor.execute(
        f"SELECT HOUR(ts), COUNT(*) FROM events WHERE {date_filter} GROUP BY HOUR(ts)",
        args,
    )
    hourly = [0] * 24
    for hour, count in cursor.fetchall():
        hourly[int(hour)] = count
    return hourly


def _image_command_breakdown(cursor, date_filter, args=()):
    cursor.execute(
        "SELECT JSON_UNQUOTE(JSON_EXTRACT(metadata, '$.command')) AS cmd, COUNT(*) AS cnt "
        f"FROM events WHERE event_type='image_gen' AND {date_filter} "
        "GROUP BY cmd ORDER BY cnt DESC",
        args,
    )
    return [
        {"command": command or "unknown", "count": count}
        for command, count in cursor.fetchall()
    ]


_stats_cache_lock = threading.Lock()
_stats_cache = {"ts": 0.0, "data": None}


def get_business_stats(force_refresh: bool = False) -> dict:
    """带 TTL 缓存的业务指标查询（默认 60s）。force_refresh=True 跳过 TTL 检查。
    DB 错误时不污染缓存；若有任何旧缓存可用则返回旧值（哪怕已过期），无缓存才返回零数据。
    返回 dict 含 'business_stats_at'（数据真实生成时间，无可用数据时为 None）与
    'business_stats_ok'（本次是否取到最新数据，False 时调用方看到的是旧值或零值）。
    """
    now = time.monotonic()
    if not force_refresh:
        cached = _stats_cache["data"]
        if cached is not None and (now - _stats_cache["ts"]) < _STATS_CACHE_TTL:
            return {**cached, **get_tracker_health()}
    data, ok = _compute_business_stats()
    if ok:
        data["business_stats_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data["business_stats_ok"] = True
        with _stats_cache_lock:
            _stats_cache["ts"] = time.monotonic()
            _stats_cache["data"] = data
        return {**data, **get_tracker_health()}
    # 失败：优先返回任何已有缓存（可能过期），否则返回零数据
    if _stats_cache["data"] is not None:
        return {**_stats_cache["data"], "business_stats_ok": False, **get_tracker_health()}
    data["business_stats_at"] = None
    data["business_stats_ok"] = False
    return {**data, **get_tracker_health()}


def _compute_business_stats() -> tuple[dict, bool]:
    """
    聚合返回业务指标。返回 (data, ok) —— ok=False 时调用方不应缓存结果。
      dau / dau_same_time_yesterday / wau / mau / stickiness
      today_new_users / today_image_calls / today_webhook_msgs
      today_bindings / today_unbinds / today_sync_total / today_sync_success / sync_success_rate
      today_sync_failures  (失败原因 Top 5)
      image_command_breakdown
      dau_30d  (日期 → DAU、新用户数，近 30 天)
      hourly_today  (0-23 小时 → 调用量)
    """
    ok = True
    out = {
        "dau": 0,
        "dau_same_time_yesterday": 0,
        "wau": 0,
        "mau": 0,
        "stickiness": 0.0,
        "today_new_users": 0,
        "today_image_calls": 0,
        "today_sync_cmd_calls": 0,
        "today_webhook_msgs": 0,
        "today_record_exports": 0,
        "today_record_imports": 0,
        "today_bindings": 0,
        "today_unbinds": 0,
        "today_sync_total": 0,
        "today_sync_success": 0,
        "sync_success_rate": 0.0,
        "today_sync_failures": [],
        "image_command_breakdown": [],
        "dau_30d": [],
        "hourly_today": [0] * 24,
    }
    try:
        with database_cursor() as (_, cursor):

            # DAU / WAU / MAU（active = 产生任意事件的 distinct user_id）
            # 今日数据是部分日，昨日同一时刻才是可比的基线
            out["dau_same_time_yesterday"] = _scalar(
                cursor,
                "SELECT COUNT(DISTINCT user_id) FROM events WHERE user_id IS NOT NULL "
                "AND ts >= DATE_SUB(CURDATE(), INTERVAL 1 DAY) AND ts < DATE_SUB(NOW(), INTERVAL 1 DAY)",
            )
            out["dau"] = _scalar(
                cursor,
                "SELECT COUNT(DISTINCT user_id) FROM events WHERE user_id IS NOT NULL AND ts >= CURDATE()",
            )
            out["wau"] = _scalar(
                cursor,
                "SELECT COUNT(DISTINCT user_id) FROM events WHERE user_id IS NOT NULL AND ts >= DATE_SUB(CURDATE(), INTERVAL 6 DAY)",
            )
            out["mau"] = _scalar(
                cursor,
                "SELECT COUNT(DISTINCT user_id) FROM events WHERE user_id IS NOT NULL AND ts >= DATE_SUB(CURDATE(), INTERVAL 29 DAY)",
            )
            if out["mau"]:
                out["stickiness"] = round(out["dau"] / out["mau"] * 100, 1)

            # 今日分事件统计
            out["today_sync_cmd_calls"] = _scalar(
                cursor,
                "SELECT COUNT(*) FROM events WHERE event_type='sync_cmd' AND ts >= CURDATE()",
            )
            activity = _activity_stats(cursor, "ts >= CURDATE()")
            out.update(
                today_image_calls=activity["image_calls"],
                today_webhook_msgs=activity["webhook_msgs"],
                today_record_exports=activity["record_exports"],
                today_record_imports=activity["record_imports"],
                today_bindings=activity["bindings"],
                today_unbinds=activity["unbinds"],
                today_sync_total=activity["sync_total"],
                today_sync_success=activity["sync_success"],
                sync_success_rate=activity["sync_success_rate"],
                today_sync_failures=activity["sync_failures"],
            )
            out["image_command_breakdown"] = _image_command_breakdown(
                cursor, "ts >= CURDATE()"
            )

            # DAU 近 30 天（按日聚合，日期全部由 DB 侧生成以避免进程与 DB 时区错位）
            cursor.execute("""
            SELECT DATE(ts) AS d, COUNT(DISTINCT user_id) AS c
            FROM events
            WHERE user_id IS NOT NULL AND ts >= DATE_SUB(CURDATE(), INTERVAL 29 DAY)
            GROUP BY d
            ORDER BY d
        """)
            by_date = {str(r[0]): r[1] for r in cursor.fetchall()}
            # 新用户：首次 user_bind 落在当天、且此前从未 bind 过的 distinct 用户
            cursor.execute("""
            SELECT DATE(first_bind) AS d, COUNT(*) FROM (
                SELECT user_id, MIN(ts) AS first_bind
                FROM events
                WHERE event_type='user_bind' AND user_id IS NOT NULL
                GROUP BY user_id
                HAVING first_bind >= DATE_SUB(CURDATE(), INTERVAL 29 DAY)
            ) t
            GROUP BY d
        """)
            new_by_date = {str(r[0]): r[1] for r in cursor.fetchall()}
            cursor.execute("SELECT CURDATE()")
            today = cursor.fetchone()[0]
            series = []
            for i in range(29, -1, -1):
                d = today - timedelta(days=i)
                series.append(
                    {
                        "date": d.strftime("%m-%d"),
                        "full_date": str(d),
                        "dau": by_date.get(str(d), 0),
                        "new_users": new_by_date.get(str(d), 0),
                    }
                )
            out["dau_30d"] = series
            out["today_new_users"] = new_by_date.get(str(today), 0)

            out["hourly_today"] = _hourly_distribution(cursor, "ts >= CURDATE()")
    except Exception as e:
        ok = False
        logger.error("[EventTracker] get_business_stats failed: %s", e)

    return out, ok


def get_hourly_stats(date_str):
    """
    获取指定日期的小时分布和图片命令分布

    Args:
        date_str: 日期字符串，格式 YYYY-MM-DD

    Returns:
        dict: {'hourly': [0]*24, 'image_command_breakdown': [...]}
    """
    result = {
        "ok": True,
        "hourly": [0] * 24,
        "image_command_breakdown": [],
        "image_calls": 0,
        "webhook_msgs": 0,
        "record_exports": 0,
        "record_imports": 0,
        "bindings": 0,
        "unbinds": 0,
        "sync_total": 0,
        "sync_success": 0,
        "sync_success_rate": 0.0,
        "sync_failures": [],
    }
    try:
        with database_cursor() as (_, cursor):
            date_filter = "DATE(ts) = %s"
            args = (date_str,)
            result["hourly"] = _hourly_distribution(cursor, date_filter, args)
            result["image_command_breakdown"] = _image_command_breakdown(
                cursor, date_filter, args
            )
            result.update(_activity_stats(cursor, date_filter, args))
    except Exception as e:
        result["ok"] = False
        logger.error(
            "[EventTracker] get_hourly_stats failed: date=%s error=%s", date_str, e
        )

    return result
