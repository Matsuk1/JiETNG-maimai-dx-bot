"""
内存管理模块

定期清理不必要的内存，优化内存使用
"""

import gc
import threading
import logging
import time
from datetime import datetime

logger = logging.getLogger(__name__)


class MemoryManager:
    """
    内存管理器
    定期执行垃圾回收和缓存清理
    """

    def __init__(self, interval_seconds: int = 300):
        """
        初始化内存管理器

        Args:
            interval_seconds: 清理间隔（秒），默认300秒（5分钟）
        """
        self.interval = interval_seconds
        self.running = False
        self.thread = None
        self.last_cleanup_time = None

    def start(self):
        """启动内存管理器"""
        if self.running:
            logger.warning("Memory manager is already running")
            return

        self.running = True
        self.thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.thread.start()
        logger.info(f"Memory manager started (interval: {self.interval}s)")

    def stop(self):
        """停止内存管理器"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Memory manager stopped")

    def _cleanup_loop(self):
        """清理循环"""
        while self.running:
            try:
                time.sleep(self.interval)
                if self.running:  # 再次检查，避免在sleep期间被停止
                    self.cleanup()
            except Exception as e:
                logger.error(f"Memory cleanup error: {e}", exc_info=True)

    def cleanup(self):
        """
        执行内存清理

        Returns:
            dict: 清理统计信息
        """
        start_time = time.time()

        # 执行垃圾回收
        collected_counts = gc.collect()

        # 记录清理时间
        self.last_cleanup_time = datetime.now()
        elapsed_time = time.time() - start_time

        stats = {
            'timestamp': self.last_cleanup_time.strftime('%Y-%m-%d %H:%M:%S'),
            'collected_objects': collected_counts,
            'elapsed_ms': int(elapsed_time * 1000)
        }

        logger.info(
            f"Memory cleanup completed: "
            f"collected {collected_counts} objects in {stats['elapsed_ms']}ms"
        )

        return stats

    def get_stats(self) -> dict:
        """
        获取内存管理器状态

        Returns:
            dict: 状态信息
        """
        return {
            'running': self.running,
            'interval_seconds': self.interval,
            'last_cleanup': self.last_cleanup_time.strftime('%Y-%m-%d %H:%M:%S') if self.last_cleanup_time else 'Never',
            'gc_counts': gc.get_count(),  # (count0, count1, count2)
            'gc_threshold': gc.get_threshold()  # (threshold0, threshold1, threshold2)
        }


def cleanup_user_caches(user_console_module=None):
    """
    清理用户相关的缓存

    Args:
        user_console_module: user_console模块的引用（可选）
    """
    cleaned_items = 0

    # 清理用户昵称缓存（如果提供了模块引用）
    if user_console_module and hasattr(user_console_module, 'nickname_cache'):
        try:
            from datetime import datetime
            current_time = datetime.now()

            # 获取缓存和锁
            cache = user_console_module.nickname_cache
            lock = user_console_module.nickname_cache_lock
            timeout = user_console_module.NICKNAME_CACHE_TIMEOUT

            with lock:
                expired_keys = []
                for user_id, cached_data in cache.items():
                    # 检查是否过期
                    if (current_time - cached_data['time']).seconds >= timeout:
                        expired_keys.append(user_id)

                # 删除过期条目
                for key in expired_keys:
                    del cache[key]
                    cleaned_items += 1

            if cleaned_items > 0:
                logger.info(f"Cleaned {cleaned_items} expired nickname cache entries")
        except Exception as e:
            logger.error(f"Failed to clean nickname cache: {e}")

    return cleaned_items


def cleanup_rate_limiter_tracking(rate_limiter_module=None):
    """
    清理频率限制追踪数据

    Args:
        rate_limiter_module: rate_limiter模块的引用（可选）
    """
    cleaned_items = 0

    if rate_limiter_module and hasattr(rate_limiter_module, 'user_request_tracking'):
        try:
            import time
            current_time = time.time()

            tracking = rate_limiter_module.user_request_tracking
            lock = rate_limiter_module.user_request_lock
            window = rate_limiter_module.REQUEST_LIMIT_WINDOW

            with lock:
                # 清理过期的请求记录
                users_to_remove = []

                for user_id, task_types in tracking.items():
                    for task_type, timestamps in list(task_types.items()):
                        # 过滤过期的时间戳
                        valid_timestamps = [
                            ts for ts in timestamps
                            if current_time - ts < window
                        ]

                        cleaned_items += len(timestamps) - len(valid_timestamps)

                        if valid_timestamps:
                            task_types[task_type] = valid_timestamps
                        else:
                            # 如果该任务类型没有有效时间戳，删除
                            del task_types[task_type]

                    # 如果用户没有任何任务类型记录，标记为删除
                    if not task_types:
                        users_to_remove.append(user_id)

                # 删除空用户记录
                for user_id in users_to_remove:
                    del tracking[user_id]
                    cleaned_items += 1

            if cleaned_items > 0:
                logger.info(f"Cleaned {cleaned_items} expired rate limit tracking entries")
        except Exception as e:
            logger.error(f"Failed to clean rate limit tracking: {e}")

    return cleaned_items


# 全局内存管理器实例
memory_manager = MemoryManager(interval_seconds=300)  # 5分钟清理一次
