"""
图片相似度匹配模块
用于识别用户发送的封面图并匹配歌曲
支持部分截图、缩放、裁剪等场景的模糊匹配
"""
import os
import logging
from PIL import Image, ImageOps, ImageFilter, ImageChops
import imagehash
import numpy as np
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


def detect_content_region(image, threshold=30):
    """
    检测图片中的主要内容区域（去除大面积单色边框）

    Args:
        image: PIL Image 对象
        threshold: 边缘检测阈值

    Returns:
        PIL.Image: 裁剪后的图片，或原图（如果检测失败）
    """
    try:
        # 转换为 RGB
        if image.mode != 'RGB':
            img_rgb = image.convert('RGB')
        else:
            img_rgb = image.copy()

        # 转换为 numpy 数组
        img_array = np.array(img_rgb)

        # 计算每行和每列的标准差（用于检测内容丰富度）
        row_std = np.std(img_array, axis=(1, 2))  # 每行的标准差
        col_std = np.std(img_array, axis=(0, 2))  # 每列的标准差

        # 找到内容区域的边界（标准差大于阈值的区域）
        content_rows = np.where(row_std > threshold)[0]
        content_cols = np.where(col_std > threshold)[0]

        if len(content_rows) > 0 and len(content_cols) > 0:
            # 获取内容区域的边界
            top = content_rows[0]
            bottom = content_rows[-1]
            left = content_cols[0]
            right = content_cols[-1]

            # 添加小边距（5%）避免裁剪过度
            height, width = img_array.shape[:2]
            margin_h = int((bottom - top) * 0.05)
            margin_w = int((right - left) * 0.05)

            top = max(0, top - margin_h)
            bottom = min(height, bottom + margin_h)
            left = max(0, left - margin_w)
            right = min(width, right + margin_w)

            # 确保裁剪区域有效
            if bottom > top and right > left:
                cropped = img_rgb.crop((left, top, right, bottom))
                logger.debug(f"检测到内容区域: ({left}, {top}, {right}, {bottom})")
                return cropped

        # 如果检测失败，返回原图
        return image

    except Exception as e:
        logger.error(f"内容区域检测失败: {e}")
        return image


def extract_center_region(image, ratio=0.8):
    """
    提取图片中心区域

    Args:
        image: PIL Image 对象
        ratio: 保留中心区域的比例 (0-1)

    Returns:
        PIL.Image: 中心区域图片
    """
    width, height = image.size
    new_width = int(width * ratio)
    new_height = int(height * ratio)

    left = (width - new_width) // 2
    top = (height - new_height) // 2
    right = left + new_width
    bottom = top + new_height

    return image.crop((left, top, right, bottom))


def preprocess_image_variants(image):
    """
    生成图片的多个预处理变体（用于模糊匹配）

    Args:
        image: PIL Image 对象

    Returns:
        list: 图片变体列表
    """
    variants = []

    try:
        # 1. 原图
        variants.append(image)

        # 2. 智能裁剪 - 去除大面积单色边框
        content_region = detect_content_region(image, threshold=30)
        if content_region.size != image.size:  # 确实裁剪了
            variants.append(content_region)
            logger.debug(f"添加内容区域变体: {content_region.size}")

        # 3. 提取中心区域（80%）
        center_80 = extract_center_region(image, ratio=0.8)
        variants.append(center_80)

        # 4. 提取中心区域（60% - 应对大边框）
        center_60 = extract_center_region(image, ratio=0.6)
        variants.append(center_60)

        # 5. 转换为正方形（填充白边）- 应对比例不同
        max_side = max(image.size)
        squared = Image.new('RGB', (max_side, max_side), (255, 255, 255))
        paste_x = (max_side - image.width) // 2
        paste_y = (max_side - image.height) // 2
        if image.mode != 'RGB':
            image_rgb = image.convert('RGB')
        else:
            image_rgb = image
        squared.paste(image_rgb, (paste_x, paste_y))
        variants.append(squared)

    except Exception as e:
        logger.error(f"图片预处理失败: {e}")
        # 至少返回原图
        if not variants:
            variants.append(image)

    logger.debug(f"生成了 {len(variants)} 个图片变体")
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


def calculate_sliding_window_match(small_img, large_img, step=20):
    """
    使用滑动窗口检测小图是否在大图中（应对部分截图）

    Args:
        small_img: 小图片（可能是封面的一部分）
        large_img: 大图片（完整封面）
        step: 滑动步长（像素）

    Returns:
        float: 最佳匹配分数（越小越好）
    """
    try:
        # 确保都是 RGB
        if small_img.mode != 'RGB':
            small_img = small_img.convert('RGB')
        if large_img.mode != 'RGB':
            large_img = large_img.convert('RGB')

        small_w, small_h = small_img.size
        large_w, large_h = large_img.size

        # 如果小图比大图还大，交换
        if small_w > large_w or small_h > large_h:
            small_img, large_img = large_img, small_img
            small_w, small_h = small_img.size
            large_w, large_h = large_img.size

        # 小图必须足够小才使用滑动窗口
        if small_w > large_w * 0.9 or small_h > large_h * 0.9:
            return float('inf')

        # 计算小图的哈希
        small_hashes = calculate_multi_hash(small_img)
        if not small_hashes:
            return float('inf')

        best_score = float('inf')

        # 滑动窗口遍历
        for y in range(0, large_h - small_h + 1, step):
            for x in range(0, large_w - small_w + 1, step):
                # 裁剪窗口区域
                window = large_img.crop((x, y, x + small_w, y + small_h))
                window_hashes = calculate_multi_hash(window)

                if window_hashes:
                    score = calculate_combined_distance(small_hashes, window_hashes)
                    if score < best_score:
                        best_score = score

        return best_score

    except Exception as e:
        logger.error(f"滑动窗口匹配失败: {e}")
        return float('inf')


def find_similar_cover(input_image, covers_dir=None, threshold=15, enable_partial_match=True):
    """
    在封面库中查找与输入图片最相似的封面（支持模糊匹配和部分匹配）

    Args:
        input_image: PIL Image 对象（用户发送的图片）
        covers_dir: 封面缓存目录
        threshold: 相似度阈值（综合距离，越小越相似）
        enable_partial_match: 是否启用部分匹配（滑动窗口，用于检测部分截图）

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

            # 方法1: 对每个输入变体计算距离，取最小值
            min_distance = float('inf')
            for input_hashes in input_hashes_list:
                distance = calculate_combined_distance(input_hashes, cover_hashes)
                min_distance = min(min_distance, distance)

            # 方法2: 如果启用部分匹配，尝试滑动窗口
            if enable_partial_match and min_distance > threshold * 0.7:
                # 只有当常规匹配分数不够好时才尝试滑动窗口（节省性能）
                try:
                    # 尝试输入图片在封面中的匹配
                    partial_score1 = calculate_sliding_window_match(input_image, cover_image, step=30)
                    # 尝试封面在输入图片中的匹配（反向）
                    partial_score2 = calculate_sliding_window_match(cover_image, input_image, step=30)

                    partial_score = min(partial_score1, partial_score2)
                    if partial_score < min_distance:
                        min_distance = partial_score
                        logger.debug(f"滑动窗口找到更好的匹配: {partial_score:.2f}")
                except Exception as e:
                    logger.debug(f"滑动窗口匹配失败: {e}")

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


def find_song_by_cover(input_image, songs_data, covers_dir=None, threshold=15, enable_partial_match=True):
    """
    通过封面图片查找歌曲（支持部分截图）

    Args:
        input_image: PIL Image 对象
        songs_data: 歌曲数据列表
        covers_dir: 封面缓存目录
        threshold: 相似度阈值
        enable_partial_match: 是否启用部分匹配（用于部分截图场景）

    Returns:
        dict: 匹配到的歌曲数据，或 None
    """
    cover_name, score = find_similar_cover(input_image, covers_dir, threshold, enable_partial_match)

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
