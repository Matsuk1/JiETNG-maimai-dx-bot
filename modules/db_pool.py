"""
数据库连接池模块
使用连接池复用数据库连接，避免频繁创建/关闭连接
"""
import pymysql
from dbutils.pooled_db import PooledDB
from modules.config_loader import HOST, USER, PASSWORD, DATABASE

# 创建连接池（全局单例）
_pool = None

def get_pool():
    """获取数据库连接池"""
    global _pool
    if _pool is None:
        _pool = PooledDB(
            creator=pymysql,
            maxconnections=10,      # 最大连接数
            mincached=2,            # 初始化时至少创建的空闲连接
            maxcached=5,            # 连接池中最多闲置的连接
            blocking=True,          # 连接池满时等待
            ping=0,                 # 检查连接有效性
            host=HOST,
            user=USER,
            password=PASSWORD,
            database=DATABASE,
            charset="utf8mb4"
        )
    return _pool

def get_connection():
    """从连接池获取一个连接"""
    pool = get_pool()
    return pool.connection()
