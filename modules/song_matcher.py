"""
歌曲匹配工具模块

提供优化的歌曲搜索和匹配功能,支持多语言(日语/英语)
"""

import functools
import re
import unicodedata
import difflib
import pykakasi

# 模块级初始化 pykakasi converter（只创建一次）
_kakasi = pykakasi.kakasi()


@functools.lru_cache(maxsize=1024)
def to_romaji(text: str) -> str:
    """
    将日文（假名+汉字）转换为罗马音

    非日文字符保留原样，结果小写无空格

    Args:
        text: 原始文本

    Returns:
        罗马音文本（小写无空格）
    """
    result = _kakasi.convert(text)
    return ''.join(item['hepburn'] for item in result).lower().replace(' ', '')


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


def is_song_match(query: str, song: dict, threshold: float = 0.75, min_query_length: int = 3) -> bool:
    """
    判断查询是否匹配歌曲

    匹配策略:
    1. 检查别名 search_acronyms (strip后完全一致)
    2. 歌名匹配 - 子串匹配 (需要满足最小长度)
    3. 歌名匹配 - 序列相似度匹配 (模糊匹配)

    Args:
        query: 搜索关键词
        song: 歌曲数据字典
        threshold: 相似度阈值 (0-1), 默认0.75
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

    # 策略3: 罗马音匹配
    query_romaji = to_romaji(query.lower())
    title_romaji = to_romaji(song['title'].lower())

    # 罗马音子串匹配
    if len(query_romaji) >= min_query_length and query_romaji in title_romaji:
        return True

    # 罗马音相似度匹配
    romaji_similarity = difflib.SequenceMatcher(
        None, query_romaji, title_romaji
    ).ratio()
    if romaji_similarity >= threshold:
        return True

    # 策略4: 歌名相似度匹配
    # 使用原始文本的小写版本进行相似度计算
    similarity = difflib.SequenceMatcher(
        None,
        query.lower(),
        song['title'].lower()
    ).ratio()

    if similarity >= threshold:
        return True

    # 额外策略: 标准化后的相似度匹配
    normalized_similarity = difflib.SequenceMatcher(
        None,
        normalized_query,
        normalized_title
    ).ratio()

    if normalized_similarity >= threshold:
        return True

    return False


def find_matching_songs(query: str, SONGS: list, max_results: int = 6, threshold: float = 0.75) -> list:
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
    # The official song U+3000 has an intentionally blank display title.
    # A bare ``info``/``record`` command targets only truly blank titles;
    # do not let general normalization turn punctuation-only titles into matches.
    if query == "":
        return [
            song for song in SONGS
            if not str(song.get("title") or "").strip()
        ][:max_results]

    matching_songs = []

    for song in SONGS:
        if is_song_match(query, song, threshold):
            matching_songs.append(song)

            if len(matching_songs) >= max_results:
                break

    return matching_songs


_TITLE_OCR_CONFUSABLES = str.maketrans({
    "极": "極",
    "圈": "圏",
    "園": "圏",
    "雜": "雑",
})


def _normalize_title_for_ocr(text):
    return normalize_text(str(text or "")).translate(_TITLE_OCR_CONFUSABLES)


def _rolling_title_parts(title):
    parts = []
    for part in re.split(r"\s+", str(title or "").strip()):
        normalized = _normalize_title_for_ocr(part)
        if len(normalized) >= 2:
            parts.append(normalized)
    return parts


def _rotated_title_candidates(parts):
    if len(parts) < 2:
        return []
    candidates = []
    seen = set()
    for index in range(1, len(parts)):
        rotated = parts[index:] + parts[:index]
        joined = "".join(rotated)
        if len(joined) < 4 or joined in seen:
            continue
        seen.add(joined)
        candidates.append((rotated, joined))
    return candidates


def _song_matches_rolling_title(normalized_song_title, rotated_parts):
    if len(rotated_parts) < 2 or len(normalized_song_title) < 4:
        return False

    first = rotated_parts[0]
    last = rotated_parts[-1]
    if not normalized_song_title.startswith(first) or not normalized_song_title.endswith(last):
        return False

    cursor = 0
    for part in rotated_parts:
        position = normalized_song_title.find(part, cursor)
        if position < 0:
            return False
        cursor = position + len(part)
    return True


def _title_edit_similarity(left, right):
    if not left or not right:
        return 0.0
    return difflib.SequenceMatcher(None, left, right).ratio()


def _edit_distance_at_most_one(left, right):
    if abs(len(left) - len(right)) > 1:
        return False
    if left == right:
        return True
    if len(left) == len(right):
        return sum(a != b for a, b in zip(left, right)) <= 1

    shorter, longer = (left, right) if len(left) < len(right) else (right, left)
    index_short = 0
    skipped = 0
    for character in longer:
        if index_short < len(shorter) and shorter[index_short] == character:
            index_short += 1
            continue
        skipped += 1
        if skipped > 1:
            return False
    return True


def _title_edge_trim_similarity(normalized_ocr, normalized_song_title):
    """Score cases where OCR adds or drops a leading/trailing character."""
    candidates = [normalized_ocr]
    if len(normalized_ocr) >= 5:
        candidates.extend([
            normalized_ocr[1:],
            normalized_ocr[:-1],
        ])
    if len(normalized_ocr) >= 6:
        candidates.extend([
            normalized_ocr[1:-1],
            normalized_ocr[2:],
            normalized_ocr[:-2],
        ])
    return max(
        _title_edit_similarity(candidate, normalized_song_title)
        for candidate in candidates
        if candidate
    )


def _cyclic_title_similarity(normalized_ocr, normalized_song_title):
    """Score scrolling-title crops such as tail+head without whitespace."""
    if len(normalized_ocr) < 4 or len(normalized_song_title) < 4:
        return 0.0

    doubled_title = normalized_song_title + normalized_song_title
    if normalized_ocr in doubled_title:
        coverage = len(normalized_ocr) / max(1, len(normalized_song_title))
        return min(0.97, 0.72 + coverage * 0.25)

    best = 0.0
    # Compare OCR against the visible prefix of every circular rotation. This
    # catches one-character OCR noise inside a wrapped title crop.
    for index in range(len(normalized_song_title)):
        rotated = normalized_song_title[index:] + normalized_song_title[:index]
        window = rotated[:len(normalized_ocr)]
        if len(window) >= 4:
            best = max(best, _title_edit_similarity(normalized_ocr, window))
        if len(normalized_ocr) > len(rotated):
            best = max(best, _title_edit_similarity(normalized_ocr, rotated))
    return best


def _dedupe_title_matches(ranked_matches, max_results):
    seen = set()
    matches = []
    match_kinds = []
    for rank in sorted(
        ranked_matches,
        key=lambda item: (
            item[0],
            item[1],
            item[2],
            str(item[-1]),
            str(item[-2].get("id") or ""),
            str(item[-2].get("type") or ""),
        ),
    ):
        song = rank[-2]
        match_kind = rank[-1]
        song_key = song_identity_key(song)
        if song_key in seen:
            continue
        seen.add(song_key)
        matches.append(song)
        match_kinds.append(match_kind)
        if len(matches) >= max_results:
            break
    return matches, match_kinds


def song_identity_key(song):
    return (
        str(song.get("id") or ""),
        str(song.get("type") or ""),
        normalize_text(str(song.get("title") or "")),
    )


def match_recognized_song_title(title, songs, max_results=12):
    """Match noisy OCR text while preferring complete canonical song titles."""
    normalized_exact_ocr = normalize_text(str(title or ""))
    normalized_ocr = _normalize_title_for_ocr(title)
    if not normalized_exact_ocr:
        return [], "none"

    exact_matches = [
        song for song in songs
        if normalize_text(str(song.get("title") or "")) == normalized_exact_ocr
    ]
    if exact_matches:
        return exact_matches[:max_results], "exact"

    if normalized_ocr != normalized_exact_ocr:
        confusable_matches = [
            song for song in songs
            if _normalize_title_for_ocr(song.get("title")) == normalized_ocr
        ]
        if confusable_matches:
            return confusable_matches[:max_results], "ocr_confusable"

    rolling_candidates = _rotated_title_candidates(_rolling_title_parts(title))
    if rolling_candidates:
        for _, candidate in rolling_candidates:
            rolling_exact_matches = [
                song for song in songs
                if _normalize_title_for_ocr(song.get("title")) == candidate
            ]
            if rolling_exact_matches:
                return rolling_exact_matches[:max_results], "rolling_exact"

        rolling_partial_matches = []
        matched_song_ids = set()
        for parts, candidate in rolling_candidates:
            for song in songs:
                normalized_song_title = _normalize_title_for_ocr(song.get("title"))
                if _song_matches_rolling_title(normalized_song_title, parts):
                    song_key = song.get("id") or normalized_song_title
                    if song_key in matched_song_ids:
                        continue
                    matched_song_ids.add(song_key)
                    rolling_partial_matches.append((len(candidate), song))
        if rolling_partial_matches:
            longest_length = max(length for length, _ in rolling_partial_matches)
            longest_matches = [
                song for length, song in rolling_partial_matches
                if length == longest_length
            ]
            return longest_matches[:max_results], "rolling_partial"

    def normalize_ocr_kana(value):
        normalized = normalize_text(str(value or ""))
        return "".join(
            character
            for character in unicodedata.normalize("NFD", normalized)
            if character not in {"\u3099", "\u309a"}
        )

    # Japanese OCR often confuses voiced and semi-voiced kana, for example
    # ぱ/ば. Ignore dakuten only when that produces one canonical song title.
    normalized_kana_ocr = normalize_ocr_kana(title)
    if len(normalized_kana_ocr) >= 4:
        kana_matches = [
            song for song in songs
            if normalize_ocr_kana(song.get("title")) == normalized_kana_ocr
        ]
        canonical_titles = {
            normalize_text(str(song.get("title") or ""))
            for song in kana_matches
        }
        if kana_matches and len(canonical_titles) == 1:
            return kana_matches[:max_results], "ocr_kana"

    directional_matches = []
    for song in songs:
        normalized_song_title = _normalize_title_for_ocr(song.get("title"))
        if len(normalized_song_title) < 2:
            continue

        score = None
        match_kind = None
        # OCR may read only the visible prefix of a scrolling long title:
        # "AAABBBCCC" can appear as "CCC AAA" or be cut as "AAABBB".
        if len(normalized_ocr) >= 3 and normalized_song_title.startswith(normalized_ocr):
            score = len(normalized_ocr) / max(1, len(normalized_song_title))
            match_kind = "prefix"
        elif len(normalized_song_title) >= 3 and normalized_song_title in normalized_ocr:
            score = len(normalized_song_title) / max(1, len(normalized_ocr))
            match_kind = "embedded"
        elif (
            min(len(normalized_ocr), len(normalized_song_title)) >= 2
            and _edit_distance_at_most_one(normalized_ocr, normalized_song_title)
        ):
            score = 0.93
            match_kind = "edit_fuzzy"
        elif len(normalized_ocr) >= 3:
            similarity = difflib.SequenceMatcher(
                None,
                normalized_ocr,
                normalized_song_title,
            ).ratio()
            threshold = 0.65 if len(normalized_ocr) <= 4 else 0.60
            if similarity >= threshold:
                score = similarity
                match_kind = "fuzzy"

        cyclic_score = _cyclic_title_similarity(normalized_ocr, normalized_song_title)
        if cyclic_score >= 0.72 and cyclic_score > (score or 0):
            score = cyclic_score
            match_kind = "rolling_fuzzy"

        trim_score = _title_edge_trim_similarity(normalized_ocr, normalized_song_title)
        if trim_score >= 0.88 and trim_score > (score or 0):
            score = trim_score
            match_kind = "edge_fuzzy"

        if score is not None:
            directional_matches.append((
                (
                    0 if match_kind == "edge_fuzzy"
                    else 1 if match_kind == "rolling_fuzzy"
                    else 2 if match_kind == "edit_fuzzy"
                    else 3 if match_kind == "prefix"
                    else 4 if match_kind == "embedded"
                    else 5
                ),
                -score,
                -len(normalized_song_title),
                song,
                match_kind,
            ))
    if directional_matches:
        matches, match_kinds = _dedupe_title_matches(directional_matches, max_results)
        match_types = set(match_kinds)
        if match_types == {"embedded"}:
            longest_length = max(
                len(normalize_text(str(song.get("title") or "")))
                for song in matches
            )
            extra_length = len(normalized_ocr) - longest_length
            match_type = "ocr_embedded" if extra_length <= 2 else "embedded"
        elif "edge_fuzzy" in match_types:
            match_type = "edge_fuzzy"
        elif "rolling_fuzzy" in match_types:
            match_type = "rolling_fuzzy"
        elif "edit_fuzzy" in match_types:
            match_type = "edit_fuzzy"
        elif "prefix" in match_types:
            match_type = "prefix"
        else:
            match_type = "fuzzy"
        return matches, match_type

    return (
        find_matching_songs(title, songs, max_results=max_results, threshold=0.82),
        "fuzzy",
    )
