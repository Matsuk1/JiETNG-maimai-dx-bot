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

# LSH 索引缓存
_lsh_index = {}  # {bucket_key: [cover_name, ...]}
_lsh_initialized = False


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
        logger.error(f"Failed to calculate hash: {e}")
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
        logger.error(f"SIFT feature extraction failed: {e}")
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
        logger.error(f"Feature matching failed: {e}")
        return 0, 0, 0.0


def _hash_to_lsh_bucket(hash_value, num_bands=32, band_size=8):
    """
    将哈希值转换为 LSH bucket keys

    Args:
        hash_value: imagehash.ImageHash 对象 (16x16 = 256 bits)
        num_bands: 分段数量（32 bands × 8 bits，保守策略确保高召回率）
        band_size: 每段的比特数（8 bits 更短，更容易匹配相似图片）

    Returns:
        list: bucket keys

    说明：
        - 更多的 bands (32) + 更短的 band_size (8) = 更高召回率
        - 即使图片有轻微差异，也能通过多个 bands 中的某几个匹配上
        - 避免漏掉正确结果（假阴性）
    """
    hash_array = hash_value.hash.flatten()  # 16x16 -> 256 元素的一维数组
    bucket_keys = []

    for band_id in range(num_bands):
        start = band_id * band_size
        end = min(start + band_size, len(hash_array))
        band_bits = hash_array[start:end]
        # 转换为整数作为 bucket key
        bucket_key = (band_id, int(''.join(map(str, band_bits.astype(int))), 2))
        bucket_keys.append(bucket_key)

    return bucket_keys


def _build_lsh_index():
    """构建 LSH 索引"""
    global _lsh_index, _lsh_initialized

    if _lsh_initialized:
        return

    logger.info("Building LSH index...")
    _lsh_index.clear()

    for cover_name, cover_hash in _hash_cache.items():
        bucket_keys = _hash_to_lsh_bucket(cover_hash)
        for bucket_key in bucket_keys:
            if bucket_key not in _lsh_index:
                _lsh_index[bucket_key] = []
            _lsh_index[bucket_key].append(cover_name)

    _lsh_initialized = True
    logger.info(f"✓ LSH index built: {len(_lsh_index)} buckets")


def load_cover_cache(covers_dir):
    """
    预加载封面的哈希和特征点
    """
    global _hash_cache, _feature_cache, _cache_loaded

    if _cache_loaded:
        return

    logger.info("Loading cover database...")

    cover_files = [f for f in os.listdir(covers_dir) if f.endswith('.png')]
    loaded = 0

    for cover_file in cover_files:
        try:
            cover_path = os.path.join(covers_dir, cover_file)
            cover_name = cover_file.replace('.png', '')

            # Load image
            pil_img = Image.open(cover_path)
            cv2_img = cv2.imread(cover_path)

            # Calculate hash
            phash = calculate_image_hash(pil_img)
            if phash:
                _hash_cache[cover_name] = phash

            # Extract features
            kp, desc = extract_sift_features(cv2_img)
            if desc is not None:
                _feature_cache[cover_name] = (kp, desc)

            loaded += 1

        except Exception as e:
            logger.error(f"Failed to load cover {cover_file}: {e}")
            continue

    _cache_loaded = True
    logger.info(f"✓ Cover database loaded: {loaded}/{len(cover_files)} covers")

    # Build LSH index
    _build_lsh_index()


def find_similar_cover(input_image, covers_dir=None, hash_threshold=15, return_multiple=False, max_results=3):
    """
    混合策略匹配封面

    策略：
    1. 先用哈希快速匹配（适合完整封面，速度快准确率高）
    2. 如果哈希匹配失败，使用特征点匹配（适合场景图片和部分遮挡）

    Args:
        input_image: PIL Image 对象
        covers_dir: 封面目录
        hash_threshold: 哈希距离阈值（越小越严格，推荐 15）
        return_multiple: 是否返回多个匹配结果（用于图片中有多个封面的场景）
        max_results: 最多返回多少个结果（仅当 return_multiple=True 时有效）

    Returns:
        如果 return_multiple=False:
            tuple: (cover_name, score, method) 或 (None, None, None)
        如果 return_multiple=True:
            list: [(cover_name, score, method), ...] 按分数降序排列

    特征点匹配采用自适应阈值：
        - 匹配质量 ≥ 75% (几何验证通过率)
        - 绝对数量 ≥ 8 (应对部分遮挡)
    """
    if covers_dir is None:
        covers_dir = COVERS_DIR

    if not os.path.exists(covers_dir):
        logger.warning(f"Cover directory does not exist: {covers_dir}")
        if return_multiple:
            return []
        else:
            return None, None, None

    # 加载缓存
    load_cover_cache(covers_dir)

    logger.info("=" * 60)
    logger.info("Starting image recognition (hybrid strategy)")

    # ========== Strategy 1: Hash matching (fast) ==========
    logger.info("→ Phase 1: Hash matching (fast full cover matching)")

    input_hash = calculate_image_hash(input_image)
    if input_hash:
        # Use LSH index for fast candidate search
        bucket_keys = _hash_to_lsh_bucket(input_hash)
        candidates = set()

        for bucket_key in bucket_keys:
            if bucket_key in _lsh_index:
                candidates.update(_lsh_index[bucket_key])

        logger.info(f"  LSH candidates: {len(candidates)} covers (filtered from {len(_hash_cache)})")

        # Calculate exact distance only for candidates
        hash_matches = []

        for cover_name in candidates:
            if cover_name not in _hash_cache:
                continue

            cover_hash = _hash_cache[cover_name]
            distance = abs(input_hash - cover_hash)
            if distance <= hash_threshold:
                confidence = 100 * (1 - distance / (hash_threshold * 2))
                hash_matches.append({
                    'cover_name': cover_name,
                    'distance': distance,
                    'confidence': confidence
                })

        # Sort by distance (ascending, smaller is better)
        hash_matches.sort(key=lambda x: x['distance'])

        if hash_matches:
            if return_multiple:
                # Smart filtering: only return results close to the best match
                best_distance = hash_matches[0]['distance']
                distance_threshold = 3  # Only allow distance difference ≤ 3

                # Filter matches with similar quality
                filtered_matches = []
                for match in hash_matches:
                    if match['distance'] - best_distance <= distance_threshold:
                        filtered_matches.append(match)
                    else:
                        # Quality gap too large, skip
                        logger.debug(f"  Skip low-quality match: {match['cover_name']} (distance: {match['distance']}, gap: {match['distance'] - best_distance})")

                # Take top max_results
                results = []
                for i, match in enumerate(filtered_matches[:max_results]):
                    results.append((match['cover_name'], match['confidence'], 'hash'))
                    logger.info(f"  Match #{i+1}: {match['cover_name']}")
                    logger.info(f"    Hamming distance: {match['distance']}")
                    logger.info(f"    Confidence: {match['confidence']:.2f}%")

                logger.info(f"✓ Hash matching success: found {len(results)} possible covers (filtered from {len(hash_matches)} candidates)")
                logger.info("=" * 60)
                return results
            else:
                # Return only the best match
                best = hash_matches[0]
                logger.info(f"  Best hash match: {best['cover_name']}, distance: {best['distance']}")
                logger.info(f"✓ Hash matching success: {best['cover_name']}")
                logger.info(f"  Hamming distance: {best['distance']} (threshold: {hash_threshold})")
                logger.info(f"  Confidence: {best['confidence']:.2f}%")
                logger.info("=" * 60)
                return best['cover_name'], best['confidence'], "hash"

    # ========== Strategy 2: Feature matching (precise) ==========
    logger.info("→ Phase 2: Feature matching (handle scene images/partial captures)")

    input_cv2 = pil_to_cv2(input_image)
    input_kp, input_desc = extract_sift_features(input_cv2)

    if input_desc is None:
        logger.warning("✗ Input image has insufficient feature points")
        logger.info("=" * 60)
        if return_multiple:
            return []
        else:
            return None, None, None

    logger.info(f"  Input image feature points: {len(input_kp)}")

    # 收集所有合格的匹配
    feature_matches = []

    for cover_name, (cover_kp, cover_desc) in _feature_cache.items():
        good_matches, geometric_matches, match_quality = match_sift_features(
            input_kp, input_desc,
            cover_kp, cover_desc
        )

        # 匹配质量阈值：至少 75% 的匹配通过几何验证
        if match_quality < 0.75:
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

        logger.debug(f"  {cover_name}: geometric={geometric_matches}, quality={match_quality:.2%}, coverage={coverage:.2%}, score={score:.2f}")

        # 添加到结果列表
        feature_matches.append({
            'cover_name': cover_name,
            'score': score,
            'geometric_matches': geometric_matches,
            'match_quality': match_quality,
            'coverage': coverage
        })

    # 按分数降序排序
    feature_matches.sort(key=lambda x: x['score'], reverse=True)

    if feature_matches:
        if return_multiple:
            # 智能过滤：只返回与最佳匹配质量接近的结果
            best_score = feature_matches[0]['score']
            score_threshold_ratio = 0.7  # 只允许分数 ≥ 最佳分数的 70%

            # 过滤出质量接近的匹配
            filtered_matches = []
            for match in feature_matches:
                if match['score'] >= best_score * score_threshold_ratio:
                    filtered_matches.append(match)
                else:
                    # 质量差距太大，跳过
                    logger.debug(f"  Skip low-quality match: {match['cover_name']} (score: {match['score']:.2f}, ratio: {match['score']/best_score:.2%})")

            # 取前 max_results 个
            results = []
            for i, match in enumerate(filtered_matches[:max_results]):
                results.append((match['cover_name'], match['score'], 'sift'))
                logger.info(f"  Match #{i+1}: {match['cover_name']}")
                logger.info(f"    Geometric matches: {match['geometric_matches']}")
                logger.info(f"    Match quality: {match['match_quality']:.2%}")
                logger.info(f"    Coverage: {match['coverage']:.2%}")
                logger.info(f"    Composite score: {match['score']:.2f}")

            logger.info(f"✓ Feature matching success: found {len(results)} possible covers (filtered from {len(feature_matches)} candidates)")
            logger.info("=" * 60)
            return results
        else:
            # 只返回最佳匹配
            best = feature_matches[0]
            logger.info(f"  Best feature match: {best['cover_name']}")
            logger.info(f"    Geometric matches: {best['geometric_matches']}")
            logger.info(f"    Match quality: {best['match_quality']:.2%}")
            logger.info(f"    Coverage: {best['coverage']:.2%}")
            logger.info(f"    Composite score: {best['score']:.2f}")

            logger.info(f"✓ Feature matching success: {best['cover_name']}")
            logger.info("=" * 60)
            return best['cover_name'], best['score'], "sift"

    # ========== 全部失败 ==========
    logger.warning("✗ No matching cover found")
    logger.info("=" * 60)

    if return_multiple:
        return []  # 返回空列表
    else:
        return None, None, None  # 返回三个 None


def find_song_by_cover(input_image, songs_data, covers_dir=None, hash_threshold=15, return_multiple=False, max_results=3):
    """
    通过封面图片查找歌曲（混合策略，支持识别多个封面）

    Args:
        input_image: PIL Image 对象
        songs_data: 歌曲数据列表
        covers_dir: 封面目录
        hash_threshold: 哈希距离阈值
        return_multiple: 是否返回多个结果（用于图片中有多个封面的场景）
        max_results: 最多返回多少个结果

    Returns:
        如果 return_multiple=False:
            dict: 匹配到的歌曲数据，或 None
        如果 return_multiple=True:
            list: [dict, ...] 歌曲列表，按匹配分数降序排列
    """
    # 调用封面匹配
    result = find_similar_cover(
        input_image, covers_dir,
        hash_threshold,
        return_multiple=return_multiple,
        max_results=max_results
    )

    if return_multiple:
        # 处理多个结果
        if not result or len(result) == 0:
            return []

        songs = []

        for cover_name, score, method in result:
            song = _find_song_by_cover_name(cover_name, songs_data, method)
            if song:
                songs.extend(song)

        if songs:
            if len(songs) > 5:
                songs = [s for s in songs if s['type'] in ['dx', 'std']]
            songs = songs[:5]
            logger.info(f"✓ Successfully identified {len(songs)} songs")

        return songs
    else:
        # 处理单个结果
        cover_name, score, method = result
        if cover_name is None:
            return None

        return _find_song_by_cover_name(cover_name, songs_data, method)


def _find_song_by_cover_name(cover_name, songs_data, method):
    """
    根据封面名称在歌曲数据中查找歌曲

    Args:
        cover_name: 封面文件名（不含扩展名）
        songs_data: 歌曲数据列表
        method: 识别方法（hash 或 sift）

    Returns:
        dict: 匹配到的歌曲数据，或 None
    """
    target_cover_with_ext = f"{cover_name}.png"
    target_cover_without_ext = cover_name

    result = []

    for song in songs_data:
        song_cover = song.get('cover_name', '')
        if song_cover == target_cover_with_ext or song_cover == target_cover_without_ext:
            logger.info(f"✓ Successfully identified song: {song.get('title')}")
            logger.info(f"  Artist: {song.get('artist')}")
            logger.info(f"  Method: {method}")
            result.append(song)

    if result:
        return result

    logger.error(f"Database error: found cover {cover_name}, but no corresponding song in database")
    return None
