"""
图片相似度匹配模块
用于识别用户发送的封面图并匹配歌曲
"""
import os
import logging
from PIL import Image
import imagehash
from modules.config_loader import COVERS_DIR

logger = logging.getLogger(__name__)


def calculate_image_hash(image):
    """
    计算图片的感知哈希值

    Args:
        image: PIL Image 对象

    Returns:
        ImageHash 对象
    """
    try:
        # 使用平均哈希（aHash）- 速度快
        # 也可以使用 phash (感知哈希) - 更准确但更慢
        return imagehash.average_hash(image, hash_size=16)
    except Exception as e:
        logger.error(f"计算图片哈希失败: {e}")
        return None


def find_similar_cover(input_image, covers_dir=None, threshold=10):
    """
    在封面库中查找与输入图片最相似的封面

    Args:
        input_image: PIL Image 对象（用户发送的图片）
        covers_dir: 封面缓存目录
        threshold: 相似度阈值（哈希距离，越小越相似，0 表示完全相同）

    Returns:
        tuple: (cover_name, similarity_score) 或 (None, None)
               cover_name: 匹配到的封面文件名（不含扩展名）
               similarity_score: 相似度分数（哈希距离）
    """
    if covers_dir is None:
        covers_dir = COVERS_DIR

    if not os.path.exists(covers_dir):
        logger.warning(f"封面目录不存在: {covers_dir}")
        return None, None

    # 计算输入图片的哈希
    input_hash = calculate_image_hash(input_image)
    if input_hash is None:
        return None, None

    best_match = None
    best_score = float('inf')

    # 遍历封面库
    cover_files = [f for f in os.listdir(covers_dir) if f.endswith('.png')]

    logger.info(f"开始匹配，封面库共有 {len(cover_files)} 张图片")

    for cover_file in cover_files:
        try:
            cover_path = os.path.join(covers_dir, cover_file)
            cover_image = Image.open(cover_path)
            cover_hash = calculate_image_hash(cover_image)

            if cover_hash is None:
                continue

            # 计算哈希距离（Hamming 距离）
            distance = input_hash - cover_hash

            if distance < best_score:
                best_score = distance
                best_match = cover_file.replace('.png', '')  # 移除扩展名

        except Exception as e:
            logger.error(f"处理封面 {cover_file} 时出错: {e}")
            continue

    # 检查是否符合阈值
    if best_match and best_score <= threshold:
        logger.info(f"找到匹配: {best_match}, 相似度分数: {best_score}")
        return best_match, best_score
    else:
        logger.info(f"未找到匹配（最佳分数: {best_score}, 阈值: {threshold}）")
        return None, None


def find_song_by_cover(input_image, songs_data, covers_dir=None, threshold=10):
    """
    通过封面图片查找歌曲

    Args:
        input_image: PIL Image 对象
        songs_data: 歌曲数据列表
        covers_dir: 封面缓存目录
        threshold: 相似度阈值

    Returns:
        dict: 匹配到的歌曲数据，或 None
    """
    cover_name, score = find_similar_cover(input_image, covers_dir, threshold)

    if cover_name is None:
        return None

    # 在歌曲数据中查找对应的歌曲
    # cover_name 已经不含 .png 扩展名（在 line 81 已移除）
    # 而 songs_data 中的 cover_name 包含 .png
    target_cover_with_ext = f"{cover_name}.png"
    target_cover_without_ext = cover_name

    for song in songs_data:
        song_cover = song.get('cover_name', '')
        # 同时匹配带扩展名和不带扩展名的情况
        if song_cover == target_cover_with_ext or song_cover == target_cover_without_ext:
            logger.info(f"匹配到歌曲: {song.get('title')}")
            return song

    logger.warning(f"找到封面 {cover_name}，但未在歌曲数据中找到对应歌曲")
    return None
