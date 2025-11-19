#!/usr/bin/env python3
"""
测试图片匹配功能
"""
import sys
from PIL import Image
from modules.image_matcher import find_similar_cover
import logging

# 设置日志级别
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

def test_image_match(image_path, threshold=15):
    """
    测试图片匹配

    Args:
        image_path: 测试图片路径
        threshold: 匹配阈值
    """
    print(f"\n{'='*60}")
    print(f"测试图片: {image_path}")
    print(f"匹配阈值: {threshold}")
    print(f"{'='*60}\n")

    try:
        # 加载图片
        image = Image.open(image_path)
        print(f"✓ 图片加载成功: {image.size}")

        # 匹配封面
        cover_name, score = find_similar_cover(
            image,
            covers_dir="cache/covers",
            threshold=threshold,
            enable_cache=True
        )

        if cover_name:
            print(f"\n{'='*60}")
            print(f"✓ 匹配成功！")
            print(f"  封面: {cover_name}.png")
            print(f"  分数: {score:.2f}")
            print(f"{'='*60}\n")
        else:
            print(f"\n{'='*60}")
            print(f"✗ 未找到匹配")
            print(f"{'='*60}\n")

    except Exception as e:
        print(f"\n✗ 测试失败: {e}\n")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python3 test_image_matcher.py <图片路径> [阈值]")
        print("示例: python3 test_image_matcher.py test.jpg 15")
        sys.exit(1)

    image_path = sys.argv[1]
    threshold = float(sys.argv[2]) if len(sys.argv) > 2 else 15

    test_image_match(image_path, threshold)
