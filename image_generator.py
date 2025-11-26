"""
图片生成模块
直接使用 JiETNG 的图片生成代码
"""

import io
import logging
from typing import List, Dict, Any
from PIL import Image, ImageDraw

from modules.record_generator import generate_records_picture
from modules.song_generator import _render_song_info_small_img, wrap_in_rounded_background, _concat_images_grid
from modules.image_manager import compose_images, font_huge, font_large
from modules.image_cache import get_cover_image, get_cached_image

logger = logging.getLogger(__name__)


def generate_b50_image(
    api_client,
    user_id: str,
    record_type: str = "best50",
    command: str = "",
    ver: str = "jp"
) -> bytes:
    """
    生成 b50 图片

    使用 JiETNG 的图片生成模块，通过 API 获取数据

    Args:
        api_client: API 客户端实例
        user_id: 用户 ID
        record_type: 记录类型 (best50/best100/best35/best15等)
        command: 筛选命令（可选）
        ver: 版本 (jp/intl)

    Returns:
        图片的字节数据
    """
    try:
        # 1. 通过 API 获取用户信息
        user_result = api_client.get_user(user_id)
        if not user_result['success']:
            raise ValueError(f"无法获取用户信息：{user_result['data'].get('message', '未知错误')}")

        user_data = user_result['data']['data']
        nickname = user_result['data'].get('nickname', 'Unknown')

        # 2. 通过 API 获取成绩记录
        records_result = api_client.get_records(user_id, record_type=record_type, command=command)
        if not records_result['success']:
            raise ValueError(f"无法获取成绩记录：{records_result['data'].get('message', '未知错误')}")

        old_songs = records_result['data'].get('old_songs', [])
        new_songs = records_result['data'].get('new_songs', [])

        if not old_songs and not new_songs:
            raise ValueError("没有找到符合条件的成绩记录")

        # 3. 使用 JiETNG 的函数生成成绩图片
        records_img = generate_records_picture(
            up_songs=old_songs,
            down_songs=new_songs,
            title=record_type.upper()
        )

        if not records_img:
            raise ValueError("图片生成失败")

        # 4. 使用 compose_images 添加页脚
        final_img = compose_images([records_img])

        # 5. 转换为字节（使用高质量）
        img_byte_arr = io.BytesIO()
        final_img.save(img_byte_arr, format='PNG', optimize=False, quality=100)
        img_byte_arr.seek(0)

        logger.info(f"Successfully generated {record_type} image for user {user_id}")
        return img_byte_arr.getvalue()

    except Exception as e:
        logger.error(f"Failed to generate image: {e}", exc_info=True)
        raise


def generate_search_image(
    songs: List[Dict[str, Any]],
    query: str = ""
) -> bytes:
    """
    生成搜索结果图片

    使用 JiETNG 的 song_generator 模块

    Args:
        songs: 歌曲数据列表
        query: 搜索关键词

    Returns:
        图片的字节数据
    """
    try:
        if not songs:
            raise ValueError("没有歌曲数据")

        # 生成歌曲信息图片列表
        song_imgs = []
        for song in songs[:20]:  # 最多显示 20 个结果
            try:
                cover_url = song.get('cover_url', '')
                cover_name = song.get('cover_name', '')

                # 优先使用本地缓存
                if cover_name:
                    cover_img = get_cover_image(cover_url, cover_name)
                else:
                    cover_img = get_cached_image(cover_url)

                if not cover_img:
                    cover_img = Image.new("RGBA", (200, 200), (200, 200, 200))
                else:
                    cover_img = cover_img.convert("RGBA")

                # 使用 JiETNG 的函数生成歌曲信息卡片
                song_img = wrap_in_rounded_background(_render_song_info_small_img(song, cover_img))
                song_imgs.append(song_img)
            except Exception as e:
                logger.warning(f"Failed to generate song card: {e}")
                continue

        if not song_imgs:
            raise ValueError("无法生成任何歌曲卡片")

        # 使用网格布局拼接
        grid_img = _concat_images_grid(song_imgs, cols=2, margin=30, inner_gap=20)

        # 使用 compose_images 添加页脚
        final_img = compose_images([grid_img])

        # 转换为字节（使用高质量）
        img_byte_arr = io.BytesIO()
        final_img.save(img_byte_arr, format='PNG', optimize=False, quality=100)
        img_byte_arr.seek(0)

        logger.info(f"Successfully generated search image for query: {query}")
        return img_byte_arr.getvalue()

    except Exception as e:
        logger.error(f"Failed to generate search image: {e}", exc_info=True)
        raise


def test_generation():
    """测试图片生成功能"""
    try:
        from api_client import JiETNGAPIClient
        import json

        # 加载配置
        with open('config.json', 'r') as f:
            config = json.load(f)

        # 初始化 API 客户端
        api_client = JiETNGAPIClient(
            base_url=config['api']['base_url'],
            token=config['api']['token']
        )

        # 测试生成
        img_data = generate_b50_image(
            api_client=api_client,
            user_id="5698411607",  # 测试 user_id
            record_type="best50"
        )

        # 保存测试图片
        with open('test_b50.png', 'wb') as f:
            f.write(img_data)

        print(f"✅ 图片生成成功，大小：{len(img_data)} 字节")
        print(f"已保存到 test_b50.png")
        return True
    except Exception as e:
        print(f"❌ 图片生成失败：{e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    test_generation()
