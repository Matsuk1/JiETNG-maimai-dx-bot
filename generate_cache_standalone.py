#!/usr/bin/env python3
"""
独立的缓存生成脚本 - 避免导入main.py的所有依赖
"""
import os
import sys

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PIL import Image
from modules.config_loader import read_dxdata, SONGS
from modules.record_generator import generate_cover, generate_internallevel_image
from modules.image_manager import compose_images

def _generate_level_cache_for_server(ver):
    """为指定服务器生成所有等级的缓存"""
    from modules.image_cache import batch_download_images

    print(f"[Cache] 开始为 {ver.upper()} 服务器生成等级缓存...")

    # 读取数据
    read_dxdata(ver)

    # 定义所有支持的等级（只生成12及以上）
    valid_levels = ["12", "12+", "13", "13+", "14", "14+", "15"]

    # 创建缓存目录
    cache_dir = "./data/level_cache"
    os.makedirs(cache_dir, exist_ok=True)

    generated_count = 0

    for level in valid_levels:
        try:
            # 收集符合条件的歌曲信息
            song_data_list = []
            region_key = ver

            for song in SONGS:
                if song['type'] == 'utage':
                    continue

                for sheet in song['sheets']:
                    if not sheet['regions'].get(region_key, False):
                        continue

                    # 14+ 包含 14+ 和 15 级别
                    if level == "14+":
                        if sheet['level'] not in ["14+", "15"]:
                            continue
                    else:
                        if sheet['level'] != level:
                            continue

                    song_data_list.append({
                        "cover_url": song['cover_url'],
                        "type": song['type'],
                        "internal_level": sheet['internalLevelValue']
                    })

            if not song_data_list:
                print(f"[Cache] {ver.upper()} Lv.{level}: 无歌曲，跳过")
                continue

            # 批量并发下载所有封面
            print(f"[Cache] {ver.upper()} Lv.{level}: 并发下载 {len(song_data_list)} 首歌曲封面...")
            cover_urls = [s['cover_url'] for s in song_data_list]
            downloaded_covers = batch_download_images(cover_urls, max_workers=20)

            # 生成封面图片（使用已下载的图片）
            target_data = []
            for song_data in song_data_list:
                cover_url = song_data['cover_url']
                if cover_url in downloaded_covers:
                    cover_img = generate_cover(cover_url, song_data['type'], size=135)
                    target_data.append({
                        "img": cover_img,
                        "internal_level": song_data['internal_level']
                    })

            if not target_data:
                print(f"[Cache] {ver.upper()} Lv.{level}: 封面下载失败，跳过")
                continue

            # 生成图片
            level_img = generate_internallevel_image(target_data, level)

            # 按宽度缩小为3/5
            new_width = int(level_img.width * 3 / 5)
            new_height = int(level_img.height * 3 / 5)
            level_img = level_img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # 用compose函数包装
            final_img = compose_images([level_img])

            # 保存到缓存
            cache_filename = f"{ver}_{level.replace('+', 'plus')}.png"
            cache_path = os.path.join(cache_dir, cache_filename)
            final_img.save(cache_path, 'PNG')

            generated_count += 1
            print(f"[Cache] {ver.upper()} Lv.{level}: ✓ ({len(target_data)} 首歌曲)")

        except Exception as e:
            print(f"[Cache] {ver.upper()} Lv.{level}: ✗ 错误: {e}")
            import traceback
            traceback.print_exc()

    print(f"[Cache] {ver.upper()} 服务器缓存生成完成：{generated_count}/{len(valid_levels)} 个等级")

def generate_all_level_caches():
    """后台生成所有服务器的等级缓存"""
    try:
        _generate_level_cache_for_server("jp")
        _generate_level_cache_for_server("intl")
        print("[Cache] 所有等级缓存生成完成")
    except Exception as e:
        print(f"[Cache] 缓存生成失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("=" * 50)
    print("开始生成定数表缓存...")
    print("=" * 50)
    generate_all_level_caches()
    print("=" * 50)
    print("完成！请检查 ./data/level_cache/ 目录")
    print("=" * 50)
