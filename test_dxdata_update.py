"""
测试 dxdata update 对比功能
"""

from modules.dxdata_console import update_dxdata_with_comparison, get_dxdata_stats, load_dxdata
from modules.config_loader import DXDATA_URL, dxdata_list

print("=" * 60)
print("测试 dxdata update 对比功能")
print("=" * 60)

# 模拟第一次更新
print("\n[测试1] 模拟首次更新...")
print("-" * 60)

# 先删除版本历史文件（如果存在）
import os
version_file = "./data/dxdata_version.json"
if os.path.exists(version_file):
    os.remove(version_file)
    print("✓ 已删除旧版本历史")

# 执行更新
result = update_dxdata_with_comparison(DXDATA_URL, dxdata_list)

print("\n返回结果:")
print(f"成功: {result['success']}")
print(f"\n消息内容:\n{result['message']}")

if result['new_stats']:
    print(f"\n新数据统计:")
    print(f"  - 歌曲数: {result['new_stats']['total_songs']}")
    print(f"  - 谱面数: {result['new_stats']['total_sheets']}")
    print(f"  - 时间戳: {result['new_stats']['timestamp']}")

# 模拟第二次更新（无变化）
print("\n" + "=" * 60)
print("[测试2] 模拟第二次更新（数据无变化）...")
print("-" * 60)

import time
time.sleep(1)  # 等待1秒，确保时间戳不同

result2 = update_dxdata_with_comparison(DXDATA_URL, dxdata_list)

print("\n返回结果:")
print(f"成功: {result2['success']}")
print(f"\n消息内容:\n{result2['message']}")

if result2['diff']:
    print(f"\n变化统计:")
    print(f"  - 新增歌曲: {result2['diff']['songs_added']}")
    print(f"  - 新增谱面: {result2['diff']['sheets_added']}")

print("\n" + "=" * 60)
print("测试完成！")
print("=" * 60)

# 显示预期的用户界面效果
print("\n\n📱 用户看到的消息示例:")
print("┌" + "─" * 40 + "┐")
for line in result2['message'].split('\n'):
    print(f"│ {line:<38} │")
print("└" + "─" * 40 + "┘")
