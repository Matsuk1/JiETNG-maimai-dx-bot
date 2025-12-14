"""
请求限速器
避免同一session短时间内过多请求触发风控

注意：限速功能已禁用，wait_if_needed() 不会进行任何等待
如需启用限速，修改 RATE_LIMIT_ENABLED = True
"""
import time
import threading
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

# 全局开关：是否启用限速
RATE_LIMIT_ENABLED = False

class RateLimiter:
    """
    Per-session 限速器
    每个 session 独立限速，互不影响
    """
    def __init__(self, min_interval_seconds=0.5):
        """
        Args:
            min_interval_seconds: 同一session两次请求的最小间隔（秒）
        """
        self.min_interval = min_interval_seconds
        self.last_call = defaultdict(float)
        self.lock = threading.Lock()

    def wait_if_needed(self, session_id):
        """
        如果请求过快，等待到允许时间

        Args:
            session_id: session 标识符（如 user_id 或 session 对象 id）
        """
        if not RATE_LIMIT_ENABLED:
            return  # 限速已禁用，直接返回

        with self.lock:
            now = time.time()
            elapsed = now - self.last_call[session_id]

            if elapsed < self.min_interval:
                sleep_time = self.min_interval - elapsed
                time.sleep(sleep_time)

            self.last_call[session_id] = time.time()


# 全局限速器实例
# 注意：限速功能已通过 RATE_LIMIT_ENABLED = False 禁用
maimai_limiter = RateLimiter(min_interval_seconds=0.5)

# 通用 API 限速
api_limiter = RateLimiter(min_interval_seconds=0.3)


# ==================== 用户请求频率限制 ====================

# 用户请求频率限制配置
user_request_tracking = {}  # {user_id: {task_type: [timestamp1, timestamp2, ...]}}
user_request_lock = threading.Lock()
REQUEST_LIMIT_WINDOW = 30  # 时间窗口：30秒
MAX_SAME_REQUESTS = 2  # 同一时间窗口内允许的最大相同请求数


def check_rate_limit(user_id: str, task_type: str) -> bool:
    """
    检查用户请求是否超过频率限制

    Args:
        user_id: 用户ID
        task_type: 任务类型（如 'maimai_update', 'b50' 等）

    Returns:
        bool: True 表示超过限制（应该拒绝），False 表示可以继续
    """
    current_time = time.time()

    with user_request_lock:
        # 初始化用户追踪
        if user_id not in user_request_tracking:
            user_request_tracking[user_id] = {}

        if task_type not in user_request_tracking[user_id]:
            user_request_tracking[user_id][task_type] = []

        # 清理过期的请求记录
        user_request_tracking[user_id][task_type] = [
            ts for ts in user_request_tracking[user_id][task_type]
            if current_time - ts < REQUEST_LIMIT_WINDOW
        ]

        # 检查是否超过限制
        if len(user_request_tracking[user_id][task_type]) >= MAX_SAME_REQUESTS:
            logger.warning(f"[RateLimit] ⚠ Limit exceeded: user_id={user_id}, task_type={task_type}")
            return True  # 超过限制

        # 记录本次请求
        user_request_tracking[user_id][task_type].append(current_time)
        return False  # 未超过限制
