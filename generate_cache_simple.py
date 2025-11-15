#!/usr/bin/env python3
"""
简单的缓存生成脚本 - 在bot环境中运行
"""

# 导入主程序中的缓存生成函数
from main import generate_all_level_caches

if __name__ == "__main__":
    print("=" * 50)
    print("开始生成定数表缓存...")
    print("=" * 50)
    generate_all_level_caches()
    print("=" * 50)
    print("完成！请检查 ./data/level_cache/ 目录")
    print("=" * 50)
