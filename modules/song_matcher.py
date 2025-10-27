"""
歌曲匹配工具模块

提供优化的歌曲搜索和匹配功能,支持多语言(日语/英语)
"""

import difflib
import re
import unicodedata


def remove_special_chars(text: str) -> str:
    """
    移除特殊符号和标点
    保留字母、数字、日文假名和汉字

    Args:
        text: 原始文本

    Returns:
        移除特殊符号后的文本
    """
    # 保留:
    # a-z, A-Z, 0-9 (ASCII字母和数字)
    # \u3040-\u309F (平假名)
    # \u30A0-\u30FF (片假名)
    # \u4E00-\u9FFF (CJK统一汉字)
    # 移除: 标点符号、特殊字符、音乐符号、希腊字母等
    pattern = r'[^a-zA-Z0-9\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]'
    return re.sub(pattern, '', text)


def normalize_text(text: str) -> str:
    """
    标准化文本用于匹配
    - 转小写
    - 全角转半角
    - 移除空格
    - 移除特殊符号

    Args:
        text: 原始文本

    Returns:
        标准化后的文本
    """
    # 转小写
    text = text.lower()

    # 全角转半角 (Unicode NFKC normalization)
    text = unicodedata.normalize('NFKC', text)

    # 移除空格
    text = text.replace(' ', '').replace('　', '')

    # 移除特殊符号 (★☆♪♫※etc.)
    text = remove_special_chars(text)

    return text


def is_song_match(query: str, song: dict, threshold: float = 0.85, min_query_length: int = 3) -> bool:
    """
    判断查询是否匹配歌曲

    匹配策略:
    1. 检查别名 search_acronyms (strip后完全一致)
    2. 歌名匹配 - 子串匹配 (需要满足最小长度)
    3. 歌名匹配 - 序列相似度匹配 (模糊匹配)

    Args:
        query: 搜索关键词
        song: 歌曲数据字典
        threshold: 相似度阈值 (0-1), 默认0.85
        min_query_length: 子串匹配的最小查询长度, 默认3

    Returns:
        bool: 是否匹配
    """
    # 策略1: 检查别名 - 采用strip后完全一致的匹配方案
    if 'search_acronyms' in song:
        query_stripped = query.strip().lower()
        for acronym in song['search_acronyms']:
            if query_stripped == acronym.strip().lower():
                return True

    # 标准化处理 (用于歌名匹配)
    normalized_query = normalize_text(query)
    normalized_title = normalize_text(song['title'])

    # 如果查询太短,只在以下情况匹配:
    # - 标准化后的查询和标题完全相同 (处理单字符歌名的情况)
    if len(normalized_query) < min_query_length:
        return normalized_query == normalized_title

    # 策略2: 歌名子串匹配 (标准化后)
    if normalized_query in normalized_title:
        return True

    # 策略3: 歌名相似度匹配
    # 使用原始文本的小写版本进行相似度计算 (保留空格,提高准确度)
    similarity = difflib.SequenceMatcher(
        None,
        query.lower(),
        song['title'].lower()
    ).ratio()

    if similarity >= threshold:
        return True

    # 额外策略: 标准化后的相似度匹配 (更宽松)
    normalized_similarity = difflib.SequenceMatcher(
        None,
        normalized_query,
        normalized_title
    ).ratio()

    if normalized_similarity >= threshold:
        return True

    return False


def find_matching_songs(query: str, SONGS: list, max_results: int = 6, threshold: float = 0.85) -> list:
    """
    查找匹配的歌曲列表

    Args:
        query: 搜索关键词
        SONGS: 歌曲列表
        max_results: 最大返回数量
        threshold: 相似度阈值

    Returns:
        list: 匹配的歌曲列表
    """
    matching_songs = []

    for song in SONGS:
        if is_song_match(query, song, threshold):
            matching_songs.append(song)

            # 达到最大数量就停止
            if len(matching_songs) >= max_results:
                break

    return matching_songs


def is_exact_song_title_match(record_name: str, song_title: str) -> bool:
    """
    判断记录中的歌曲名是否与歌曲数据中的标题完全匹配
    用于匹配用户游玩记录和歌曲数据

    Args:
        record_name: 用户记录中的歌曲名
        song_title: 歌曲数据中的标题

    Returns:
        bool: 是否完全匹配
    """
    # 策略1: 精确匹配
    if record_name == song_title:
        return True

    # 策略2: 标准化后匹配 (处理全角半角问题)
    normalized_record = normalize_text(record_name)
    normalized_song = normalize_text(song_title)

    if normalized_record == normalized_song:
        return True

    # 策略3: 序列相似度 >= 1.0 (difflib精确匹配)
    # 保留原有逻辑兼容性
    similarity = difflib.SequenceMatcher(None, record_name, song_title).ratio()
    if similarity >= 1.0:
        return True

    # 策略4: 非常高的相似度 (>= 0.98) 且标准化后相同
    # 处理细微差异 (如空格、标点)
    if similarity >= 0.98 and normalized_record == normalized_song:
        return True

    return False
