"""
图片相似度匹配模块
用于识别用户发送的封面图并匹配歌曲
支持部分截图、缩放、裁剪等场景的模糊匹配
"""
import os
import logging
from PIL import Image, ImageOps
import imagehash
from modules.config_loader import COVERS_DIR

logger = logging.getLogger(__name__)


def calculate_multi_hash(image):
    """
    计算图片的多种哈希值（用于提高匹配准确度）

    Args:
        image: PIL Image 对象

    Returns:
        dict: 包含多种哈希算法结果的字典
    """
    try:
        # 转换为 RGB（确保格式一致）
        if image.mode != 'RGB':
            image = image.convert('RGB')

        # 使用多种哈希算法
        hashes = {
            'average': imagehash.average_hash(image, hash_size=8),      # 平均哈希 - 快速
            'phash': imagehash.phash(image, hash_size=8),               # 感知哈希 - 抗变形
            'dhash': imagehash.dhash(image, hash_size=8),               # 差异哈希 - 抗裁剪
        }
        return hashes
    except Exception as e:
        logger.error(f"计算图片哈希失败: {e}")
        return None


def preprocess_image_variants(image):
    """
    生成图片的多个预处理变体（用于模糊匹配）

    Args:
        image: PIL Image 对象

    Returns:
        list: 图片变体列表
    """
    variants = [image]  # 原图

    try:
        # 转换为正方形（填充白边）
        max_side = max(image.size)
        squared = Image.new('RGB', (max_side, max_side), (255, 255, 255))
        paste_x = (max_side - image.width) // 2
        paste_y = (max_side - image.height) // 2
        squared.paste(image, (paste_x, paste_y))
        variants.append(squared)

        # 中心裁剪（应对有边框的情况）
        width, height = image.size
        crop_margin = min(width, height) // 10  # 裁剪 10% 边缘
        if crop_margin > 0:
            cropped = image.crop((
                crop_margin,
                crop_margin,
                width - crop_margin,
                height - crop_margin
            ))
            variants.append(cropped)

    except Exception as e:
        logger.error(f"图片预处理失败: {e}")

    return variants


def calculate_combined_distance(hashes1, hashes2):
    """
    计算两组哈希的综合距离

    Args:
        hashes1: 第一组哈希字典
        hashes2: 第二组哈希字典

    Returns:
        float: 综合距离（加权平均）
    """
    if not hashes1 or not hashes2:
        return float('inf')

    # 权重：phash 最重要（抗变形），其次是 dhash（抗裁剪），最后是 average
    weights = {'average': 0.2, 'phash': 0.5, 'dhash': 0.3}
    total_distance = 0
    total_weight = 0

    for hash_type, weight in weights.items():
        if hash_type in hashes1 and hash_type in hashes2:
            distance = hashes1[hash_type] - hashes2[hash_type]
            total_distance += distance * weight
            total_weight += weight

    if total_weight == 0:
        return float('inf')

    return total_distance / total_weight


def find_similar_cover(input_image, covers_dir=None, threshold=15):
    """
    在封面库中查找与输入图片最相似的封面（支持模糊匹配）

    Args:
        input_image: PIL Image 对象（用户发送的图片）
        covers_dir: 封面缓存目录
        threshold: 相似度阈值（综合距离，越小越相似）

    Returns:
        tuple: (cover_name, similarity_score) 或 (None, None)
               cover_name: 匹配到的封面文件名（不含扩展名）
               similarity_score: 相似度分数（综合距离）
    """
    if covers_dir is None:
        covers_dir = COVERS_DIR

    if not os.path.exists(covers_dir):
        logger.warning(f"封面目录不存在: {covers_dir}")
        return None, None

    # 生成输入图片的多个变体
    input_variants = preprocess_image_variants(input_image)

    # 为每个变体计算哈希
    input_hashes_list = []
    for variant in input_variants:
        hashes = calculate_multi_hash(variant)
        if hashes:
            input_hashes_list.append(hashes)

    if not input_hashes_list:
        logger.error("无法计算输入图片的哈希值")
        return None, None

    best_match = None
    best_score = float('inf')

    # 遍历封面库
    cover_files = [f for f in os.listdir(covers_dir) if f.endswith('.png')]

    logger.info(f"开始模糊匹配，封面库共有 {len(cover_files)} 张图片")

    for cover_file in cover_files:
        try:
            cover_path = os.path.join(covers_dir, cover_file)
            cover_image = Image.open(cover_path)
            cover_hashes = calculate_multi_hash(cover_image)

            if cover_hashes is None:
                continue

            # 对每个输入变体计算距离，取最小值
            min_distance = float('inf')
            for input_hashes in input_hashes_list:
                distance = calculate_combined_distance(input_hashes, cover_hashes)
                min_distance = min(min_distance, distance)

            if min_distance < best_score:
                best_score = min_distance
                best_match = cover_file.replace('.png', '')  # 移除扩展名

        except Exception as e:
            logger.error(f"处理封面 {cover_file} 时出错: {e}")
            continue

    # 检查是否符合阈值
    if best_match and best_score <= threshold:
        logger.info(f"找到匹配: {best_match}, 相似度分数: {best_score:.2f}")
        return best_match, best_score
    else:
        logger.info(f"未找到匹配（最佳分数: {best_score:.2f}, 阈值: {threshold}）")
        return None, None


def find_song_by_cover(input_image, songs_data, covers_dir=None, threshold=15):
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
