"""
图片相似度匹配模块 - 混合策略版本
1. 哈希算法：快速匹配完整封面（高准确率）
2. 特征点匹配：处理场景图片和部分截图（高召回率）
"""
import os
import logging
import cv2
import numpy as np
from PIL import Image
import imagehash
from modules.config_loader import COVERS_DIR

logger = logging.getLogger(__name__)

# 全局缓存
_hash_cache = {}  # 哈希缓存
_feature_cache = {}  # 特征点缓存
_cache_loaded = False


def pil_to_cv2(pil_image):
    """将 PIL Image 转换为 OpenCV 格式"""
    if pil_image.mode != 'RGB':
        pil_image = pil_image.convert('RGB')
    return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)


def calculate_image_hash(pil_image):
    """
    计算图片的感知哈希（用于快速匹配完整封面）
    """
    try:
        if pil_image.mode != 'RGB':
            pil_image = pil_image.convert('RGB')

        # 使用感知哈希（对缩放、轻微变形不敏感）
        phash = imagehash.phash(pil_image, hash_size=16)  # 更大的哈希以提高准确率
        return phash
    except Exception as e:
        logger.error(f"计算哈希失败: {e}")
        return None


def extract_sift_features(image_cv2):
    """
    提取 SIFT 特征点（用于场景图片识别）
    """
    try:
        gray = cv2.cvtColor(image_cv2, cv2.COLOR_BGR2GRAY)

        # SIFT 检测器
        sift = cv2.SIFT_create(nfeatures=1500)
        keypoints, descriptors = sift.detectAndCompute(gray, None)

        if descriptors is None or len(keypoints) < 15:
            return None, None

        return keypoints, descriptors

    except Exception as e:
        logger.debug(f"SIFT 特征提取失败: {e}")
        return None, None


def match_sift_features(kp1, desc1, kp2, desc2):
    """
    匹配 SIFT 特征点并返回匹配数量和质量评分

    Returns:
        tuple: (good_matches, geometric_matches, match_quality)
               match_quality: 0-1 的匹配质量分数
    """
    try:
        if desc1 is None or desc2 is None:
            return 0, 0, 0.0

        # FLANN 匹配器
        FLANN_INDEX_KDTREE = 1
        index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
        search_params = dict(checks=50)
        flann = cv2.FlannBasedMatcher(index_params, search_params)

        matches = flann.knnMatch(desc1, desc2, k=2)

        # Lowe's ratio test（更严格，避免误匹配）
        good_matches = []
        for match_pair in matches:
            if len(match_pair) == 2:
                m, n = match_pair
                if m.distance < 0.65 * n.distance:  # 从 0.7 降到 0.65
                    good_matches.append(m)

        if len(good_matches) < 8:  # 降低最小要求（应对部分遮挡）
            return len(good_matches), 0, 0.0

        # 几何验证（更严格的 RANSAC）
        try:
            src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
            dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)

            # 更严格的 RANSAC 阈值（3.0 而不是 5.0）
            M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 3.0)

            if mask is not None:
                geometric_matches = int(np.sum(mask))

                # 计算匹配质量（几何验证通过率）
                geometric_ratio = geometric_matches / len(good_matches) if len(good_matches) > 0 else 0

                return len(good_matches), geometric_matches, geometric_ratio
        except:
            pass

        return len(good_matches), 0, 0.0

    except Exception as e:
        logger.debug(f"特征匹配失败: {e}")
        return 0, 0, 0.0


def load_cover_cache(covers_dir):
    """
    预加载封面的哈希和特征点
    """
    global _hash_cache, _feature_cache, _cache_loaded

    if _cache_loaded:
        return

    logger.info("正在加载封面数据库...")

    cover_files = [f for f in os.listdir(covers_dir) if f.endswith('.png')]
    loaded = 0

    for cover_file in cover_files:
        try:
            cover_path = os.path.join(covers_dir, cover_file)
            cover_name = cover_file.replace('.png', '')

            # 加载图片
            pil_img = Image.open(cover_path)
            cv2_img = cv2.imread(cover_path)

            # 计算哈希
            phash = calculate_image_hash(pil_img)
            if phash:
                _hash_cache[cover_name] = phash

            # 提取特征点
            kp, desc = extract_sift_features(cv2_img)
            if desc is not None:
                _feature_cache[cover_name] = (kp, desc)

            loaded += 1

        except Exception as e:
            logger.debug(f"加载封面 {cover_file} 失败: {e}")
            continue

    _cache_loaded = True
    logger.info(f"✓ 封面数据库加载完成: {loaded}/{len(cover_files)} 张")


def find_similar_cover(input_image, covers_dir=None, hash_threshold=15):
    """
    混合策略匹配封面

    策略：
    1. 先用哈希快速匹配（适合完整封面，速度快准确率高）
    2. 如果哈希匹配失败，使用特征点匹配（适合场景图片和部分遮挡）

    Args:
        input_image: PIL Image 对象
        covers_dir: 封面目录
        hash_threshold: 哈希距离阈值（越小越严格，推荐 15）

    Returns:
        tuple: (cover_name, score, method) 或 (None, None, None)

    特征点匹配采用自适应阈值：
        - 匹配质量 ≥ 60% (几何验证通过率)
        - 绝对数量 ≥ 8 (应对部分遮挡)
    """
    if covers_dir is None:
        covers_dir = COVERS_DIR

    if not os.path.exists(covers_dir):
        logger.warning(f"封面目录不存在: {covers_dir}")
        return None, None, None

    # 加载缓存
    load_cover_cache(covers_dir)

    logger.info("=" * 60)
    logger.info("开始图片识别（混合策略）")

    # ========== 策略 1: 哈希匹配（快速） ==========
    logger.info("→ 阶段 1: 哈希匹配（快速匹配完整封面）")

    input_hash = calculate_image_hash(input_image)
    if input_hash:
        best_hash_match = None
        best_hash_distance = float('inf')

        for cover_name, cover_hash in _hash_cache.items():
            distance = abs(input_hash - cover_hash)  # 使用绝对值确保距离为正
            if distance < best_hash_distance:
                best_hash_distance = distance
                best_hash_match = cover_name

        logger.info(f"  最佳哈希匹配: {best_hash_match}, 距离: {best_hash_distance}")

        # 如果哈希距离很小，直接返回
        if best_hash_distance <= hash_threshold:
            confidence = 100 * (1 - best_hash_distance / (hash_threshold * 2))  # 0-100 分数
            logger.info(f"✓ 哈希匹配成功: {best_hash_match}")
            logger.info(f"  汉明距离: {best_hash_distance} (阈值: {hash_threshold})")
            logger.info(f"  置信度: {confidence:.2f}%")
            logger.info("=" * 60)
            return best_hash_match, confidence, "hash"

    # ========== 策略 2: 特征点匹配（精确） ==========
    logger.info("→ 阶段 2: 特征点匹配（处理场景图片/部分截图）")

    input_cv2 = pil_to_cv2(input_image)
    input_kp, input_desc = extract_sift_features(input_cv2)

    if input_desc is None:
        logger.warning("✗ 输入图片特征点不足")
        logger.info("=" * 60)
        return None, None, None

    logger.info(f"  输入图片特征点: {len(input_kp)} 个")

    best_feature_match = None
    best_feature_score = 0
    best_geometric_matches = 0
    best_match_quality = 0
    best_coverage = 0

    for cover_name, (cover_kp, cover_desc) in _feature_cache.items():
        good_matches, geometric_matches, match_quality = match_sift_features(
            input_kp, input_desc,
            cover_kp, cover_desc
        )

        # 匹配质量阈值：至少 60% 的匹配通过几何验证
        if match_quality < 0.6:
            continue

        # 绝对数量要求：至少 8 个（降低了，应对部分遮挡）
        if geometric_matches < 8:
            continue

        # 计算覆盖率（相对于封面特征点）
        coverage = geometric_matches / len(cover_kp) if len(cover_kp) > 0 else 0

        # 综合评分 = 匹配质量^2 * 几何验证数量 * 覆盖率
        # - 匹配质量最重要（平方权重），确保匹配可靠
        # - 几何验证数量保证足够的支持
        # - 覆盖率确保匹配到足够大的区域
        score = (match_quality ** 2) * geometric_matches * (1 + coverage)

        logger.debug(f"  {cover_name}: 几何={geometric_matches}, 质量={match_quality:.2%}, 覆盖={coverage:.2%}, 分数={score:.2f}")

        if score > best_feature_score:
            best_feature_score = score
            best_feature_match = cover_name
            best_geometric_matches = geometric_matches
            best_match_quality = match_quality
            best_coverage = coverage

    if best_feature_match:
        logger.info(f"  最佳特征匹配: {best_feature_match}")
        logger.info(f"    几何验证: {best_geometric_matches} 个")
        logger.info(f"    匹配质量: {best_match_quality:.2%}")
        logger.info(f"    覆盖率: {best_coverage:.2%}")
        logger.info(f"    综合分数: {best_feature_score:.2f}")

        logger.info(f"✓ 特征匹配成功: {best_feature_match}")
        logger.info("=" * 60)
        return best_feature_match, best_feature_score, "sift"

    # ========== 全部失败 ==========
    logger.warning("✗ 未找到匹配的封面")
    logger.warning(f"  哈希最佳距离: {best_hash_distance if input_hash else 'N/A'}")
    logger.warning(f"  特征点最佳几何验证: {best_geometric_matches}")
    logger.info("=" * 60)

    return None, None, None


def find_song_by_cover(input_image, songs_data, covers_dir=None, hash_threshold=15):
    """
    通过封面图片查找歌曲（混合策略）

    Args:
        input_image: PIL Image 对象
        songs_data: 歌曲数据列表
        covers_dir: 封面目录
        hash_threshold: 哈希距离阈值

    Returns:
        dict: 匹配到的歌曲数据，或 None
    """
    cover_name, score, method = find_similar_cover(
        input_image, covers_dir,
        hash_threshold
    )

    if cover_name is None:
        return None

    # 在歌曲数据中查找
    target_cover_with_ext = f"{cover_name}.png"
    target_cover_without_ext = cover_name

    for song in songs_data:
        song_cover = song.get('cover_name', '')
        if song_cover == target_cover_with_ext or song_cover == target_cover_without_ext:
            logger.info(f"✓ 成功识别歌曲: 《{song.get('title')}》")
            logger.info(f"  艺术家: {song.get('artist')}")
            logger.info(f"  识别方式: {method}")
            return song

    logger.error(f"数据库错误：找到封面 {cover_name}，但数据库中无对应歌曲")
    return None
