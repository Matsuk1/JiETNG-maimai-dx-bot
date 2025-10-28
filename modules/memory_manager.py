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
        self.last_cleanup_stats = None  # 保存最后一次清理的详细统计

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

        # 获取清理前的 gc 计数（用于统计）
        gc_counts_before = gc.get_count()

        # 执行垃圾回收（分别收集每一代并统计）
        collected_gen0 = gc.collect(0)  # 收集 generation 0
        collected_gen1 = gc.collect(1)  # 收集 generation 1
        collected_gen2 = gc.collect(2)  # 收集 generation 2
        total_collected = collected_gen0 + collected_gen1 + collected_gen2

        # 记录清理时间
        self.last_cleanup_time = datetime.now()
        elapsed_time = time.time() - start_time

        stats = {
            'timestamp': self.last_cleanup_time.strftime('%Y-%m-%d %H:%M:%S'),
            'collected_objects': total_collected,
            'collected_by_generation': {
                'gen0': collected_gen0,
                'gen1': collected_gen1,
                'gen2': collected_gen2
            },
            'gc_counts_before': gc_counts_before,
            'elapsed_ms': int(elapsed_time * 1000)
        }

        logger.info(
            f"Memory cleanup completed: "
            f"collected {total_collected} objects "
            f"(gen0: {collected_gen0}, gen1: {collected_gen1}, gen2: {collected_gen2}) "
            f"in {stats['elapsed_ms']}ms"
        )

        # 保存清理统计信息
        self.last_cleanup_stats = stats

        return stats

    def get_stats(self) -> dict:
        """
        获取内存管理器状态

        Returns:
            dict: 状态信息
        """
        # 获取当前 gc 计数
        current_gc_counts = gc.get_count()

        # 如果有上次清理的统计，使用清理前的计数（更有意义）
        # 否则使用当前计数
        display_gc_counts = current_gc_counts
        if self.last_cleanup_stats and 'gc_counts_before' in self.last_cleanup_stats:
            display_gc_counts = self.last_cleanup_stats['gc_counts_before']

        return {
            'running': self.running,
            'interval_seconds': self.interval,
            'last_cleanup': self.last_cleanup_time.strftime('%Y-%m-%d %H:%M:%S') if self.last_cleanup_time else 'Never',
            'gc_counts': display_gc_counts,  # 显示清理前的计数
            'gc_counts_current': current_gc_counts,  # 当前实时计数
            'gc_threshold': gc.get_threshold(),  # (threshold0, threshold1, threshold2)
            'last_cleanup_stats': self.last_cleanup_stats  # 最后一次清理的详细信息
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
