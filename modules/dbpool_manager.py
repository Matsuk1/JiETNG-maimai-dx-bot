"""
数据库连接池模块
使用连接池复用数据库连接，避免频繁创建/关闭连接
"""
import pymysql
from dbutils.pooled_db import PooledDB
from modules.config_loader import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME

# 创建连接池（全局单例）
_pool = None

def get_pool():
    """获取数据库连接池（优化后配置）"""
    global _pool
    if _pool is None:
        _pool = PooledDB(
            creator=pymysql,
            maxconnections=5,       # 最大连接数（降低：10 → 5）
            mincached=1,            # 初始化时至少创建的空闲连接（降低：2 → 1）
            maxcached=3,            # 连接池中最多闲置的连接（降低：5 → 3）
            maxshared=3,            # 最大共享连接数（新增）
            blocking=True,          # 连接池满时等待
            ping=1,                 # 每次取连接时检查有效性（优化：0 → 1）
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            charset="utf8mb4"
        )
    return _pool

def get_connection():
    """从连接池获取一个连接"""
    pool = get_pool()
    return pool.connection()
