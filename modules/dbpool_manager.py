"""
数据库连接池模块
使用连接池复用数据库连接，避免频繁创建/关闭连接
"""

import os
import logging
import threading
from contextlib import contextmanager
from typing import Iterator

import pymysql
from dbutils.pooled_db import PooledDB

logger = logging.getLogger(__name__)

_pool = None
_pool_lock = threading.Lock()


def _env_int(name: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(name, default)))
    except (TypeError, ValueError):
        return default


def _create_pool() -> PooledDB:
    from modules.config_loader import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME

    maxconnections = _env_int("JIETNG_DB_MAX_CONNECTIONS", 20)
    maxcached = min(_env_int("JIETNG_DB_MAX_CACHED", 8), maxconnections)
    mincached = min(_env_int("JIETNG_DB_MIN_CACHED", 2), maxcached)

    return PooledDB(
        creator=pymysql,
        maxconnections=maxconnections,
        mincached=mincached,
        maxcached=maxcached,
        maxshared=0,
        blocking=True,
        ping=4,
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset="utf8mb4",
    )


def get_pool():
    """Return the process-wide connection pool, creating it once."""
    global _pool
    if _pool is not None:
        return _pool
    with _pool_lock:
        if _pool is None:
            _pool = _create_pool()
    return _pool


def get_connection():
    """从连接池获取一个连接"""
    return get_pool().connection()


@contextmanager
def database_cursor(*, write: bool = False) -> Iterator[tuple[object, object]]:
    """Yield a pooled connection/cursor and manage its transaction lifecycle."""
    connection = get_connection()
    cursor = connection.cursor()
    try:
        yield connection, cursor
        if write:
            connection.commit()
    except Exception:
        if write:
            try:
                connection.rollback()
            except Exception:
                logger.warning(
                    "[DBPool] Failed to roll back database transaction", exc_info=True
                )
        raise
    finally:
        try:
            cursor.close()
        except Exception:
            logger.warning("[DBPool] Failed to close database cursor", exc_info=True)
        try:
            connection.close()
        except Exception:
            logger.warning("[DBPool] Failed to return database connection", exc_info=True)


def close_pool() -> None:
    """Close cached connections and reset the pool."""
    global _pool
    with _pool_lock:
        pool, _pool = _pool, None
    if pool is not None:
        pool.close()
