import requests
import json
import os
import copy
import hashlib
import logging
import threading
import time
from datetime import datetime, timedelta
from modules.config_loader import MAIMAI_VERSION, DXDATA_VERSION_FILE, OVERRIDE_FILE, apply_override

logger = logging.getLogger(__name__)

def merge_json(source, target):
    """递归合并两个 JSON 结构（dict / list / 基础类型）"""
    # dict 合并逻辑
    if isinstance(source, dict) and isinstance(target, dict):
        for key, value in source.items():
            if key not in target:
                target[key] = copy.deepcopy(value)
            else:
                src_val, tgt_val = value, target[key]

                if isinstance(src_val, str) and isinstance(tgt_val, str):
                    if src_val and not tgt_val:
                        target[key] = src_val
                    continue

                elif isinstance(src_val, list) and isinstance(tgt_val, list):
                    if not tgt_val and src_val:
                        target[key] = copy.deepcopy(src_val)
                    elif tgt_val and not src_val:
                        continue
                    else:
                        for i in range(min(len(src_val), len(tgt_val))):
                            merge_json(src_val[i], tgt_val[i])
                        if len(src_val) > len(tgt_val):
                            target[key].extend(copy.deepcopy(src_val[len(tgt_val):]))

                # 递归合并 dict
                elif isinstance(src_val, dict) and isinstance(tgt_val, dict):
                    merge_json(src_val, tgt_val)

                # 类型不一致时以非空值为准
                else:
                    if tgt_val in ('', [], {}):
                        target[key] = copy.deepcopy(src_val)

    # list 合并逻辑
    elif isinstance(source, list) and isinstance(target, list):
        if not target and source:
            target.extend(copy.deepcopy(source))
        elif target and not source:
            return target
        else:
            for i in range(min(len(source), len(target))):
                merge_json(source[i], target[i])
            if len(source) > len(target):
                target.extend(copy.deepcopy(source[len(target):]))

    else:
        if target in (None, '', [], {}):
            target = copy.deepcopy(source)

    return target


def merge_songs_list(source_songs, target_songs, key_field="title"):
    """
    合并两个 songs 列表,按 key_field 去重

    Args:
        source_songs: 源歌曲列表
        target_songs: 目标歌曲列表
        key_field: 用于匹配的键名

    Returns:
        合并后的歌曲列表
    """
    result = copy.deepcopy(target_songs)
    target_index = {item.get(key_field): item for item in result if key_field in item}

    for item in source_songs:
        key_val = item.get(key_field)
        if key_val in target_index:
            merge_json(item, target_index[key_val])
        else:
            result.append(copy.deepcopy(item))

    return result

def load_dxdata(url):
    try:
        with requests.get(url, timeout=(5, 30)) as response:
            response.raise_for_status()
            data = response.json()

        data['songs'] = _split_song_sheets_by_type(data['songs'])
        for song in data['songs']:
            for version in data['versions']:
                if version['version'] == song['version']:
                    for sheet in song.get("sheets", []):
                        if 'count' not in version:
                            version['count'] = 0
                        if sheet['regions']['jp']:
                            version['count'] += 1

        return data

    except requests.RequestException as e:
        return None
    except json.JSONDecodeError as e:
        return None

def _split_song_sheets_by_type(song_list):
    result = []

    for song in song_list:
        base_info = {
            "category": song["category"],
            "title": song["title"],
            "artist": song["artist"],
            "bpm": song["bpm"],
            "version": song.get("version", ""),
            "cover_url": f"https://dp4p6x0xfi5o9.cloudfront.net/maimai/img/cover/{song['imageName']}",
            "cover_name": song["imageName"],
            "search_acronyms": song.get("searchAcronyms", [])
        }

        sheets_by_type = {"dx": [], "std": [], "utage": []}
        version_by_type = {}

        for sheet in song.get("sheets", []):
            sheet_type = sheet.get("type")
            if sheet["difficulty"] not in ["basic", "advanced", "expert", "master", "remaster"]:
                sheet["difficulty"] = "utage"

            if "multiverInternalLevelValue" in sheet:
                sheet["internalLevelValue"] = sheet["multiverInternalLevelValue"].get(MAIMAI_VERSION["jp"][-1], sheet["internalLevelValue"])

            if sheet_type in sheets_by_type:
                new_sheet = copy.deepcopy(sheet)
                version_by_type[sheet_type] = new_sheet.pop("version", base_info["version"])
                new_sheet.pop("type", None)
                sheets_by_type[sheet_type].append(new_sheet)

        for sheet_type, sheets in sheets_by_type.items():
            if sheets:
                entry = copy.deepcopy(base_info)
                entry["type"] = sheet_type
                entry["version"] = version_by_type.get(sheet_type, base_info["version"])
                entry["sheets"] = sheets
                entry["id"] = generate_song_unique_id(base_info["cover_name"], sheet_type, base_info["title"])
                result.append(entry)

    # 根据 id 去重
    seen_ids = set()
    deduplicated_result = []
    for entry in result:
        entry_id = entry.get("id")
        if entry_id not in seen_ids:
            seen_ids.add(entry_id)
            deduplicated_result.append(entry)

    return deduplicated_result


def get_dxdata_stats(data):
    """
    获取 dxdata 的统计信息

    Args:
        data: dxdata JSON 数据

    Returns:
        dict: 包含歌曲数、谱面数等统计信息
    """
    if not data or 'songs' not in data:
        return None

    total_songs = len(data['songs'])
    total_sheets = 0

    for song in data['songs']:
        if 'sheets' in song:
            total_sheets += len(song['sheets'])

    return {
        'total_songs': total_songs,
        'total_sheets': total_sheets,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }


def load_dxdata_version_history():
    """加载 dxdata 版本历史"""
    if not os.path.exists(DXDATA_VERSION_FILE):
        return None

    try:
        with open(DXDATA_VERSION_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def save_dxdata_version_history(stats):
    """保存 dxdata 版本历史"""
    try:
        with open(DXDATA_VERSION_FILE, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def _filter_song_fields(song):
    """
    过滤歌曲对象，只保留指定字段

    Args:
        song: 原始歌曲对象

    Returns:
        dict: 过滤后的歌曲对象
    """
    filtered_song = {
        "title": song.get("title", ""),
        "artist": song.get("artist", ""),
        "id": song.get("id", ""),
        "bpm": song.get("bpm", 0),
        "category": song.get("category", ""),
        "version": song.get("version", ""),
        "cover_url": song.get("cover_url", ""),
        "cover_name": song.get("cover_name", ""),
        "type": song.get("type", ""),
        "search_acronyms": song.get("search_acronyms", []),
        "sheets": []
    }

    for sheet in song.get("sheets", []):
        filtered_sheet = {
            "difficulty": sheet.get("difficulty", ""),
            "level": sheet.get("level", ""),
            "internalLevelValue": sheet.get("internalLevelValue", 0),
            "noteDesigner": sheet.get("noteDesigner", ""),
            "noteCounts": sheet.get("noteCounts", {}),
            "regions": sheet.get("regions", {}),
            "multiverInternalLevelValue": sheet.get("multiverInternalLevelValue", {}),
            "releaseDate": sheet.get("releaseDate", "")
        }
        filtered_song["sheets"].append(filtered_sheet)

    return filtered_song


def update_dxdata_with_comparison(urls, save_to: str = None):
    """
    更新 dxdata 并返回与上次的对比信息

    Args:
        url: dxdata API URL
        save_to: 保存文件路径

    Returns:
        dict: 包含更新结果和对比信息
            {
                'success': bool,
                'new_stats': dict,
                'old_stats': dict,
                'diff': {
                    'songs_added': int,
                    'sheets_added': int
                },
                'message': str
            }
    """
    old_version = load_dxdata_version_history()

    new_datas = []
    for url in urls:
        data = load_dxdata(url)
        if data is not None:
            new_datas.append(data)

    if not new_datas:
        return {
            'success': False
        }

    # 只合并 songs 字段（使用 id 去重）
    for i in range(1, len(new_datas)):
        new_datas[0]['songs'] = merge_songs_list(new_datas[i]['songs'], new_datas[0]['songs'], "id")

    new_data = new_datas[0]

    if save_to:
        filtered_songs = [_filter_song_fields(song) for song in new_data.get("songs", [])]
        apply_override(filtered_songs, OVERRIDE_FILE)
        filtered_data = {
            "songs": filtered_songs,
            "versions": new_data.get("versions", [])
        }

        with open(save_to, "w", encoding="utf-8") as file:
            json.dump(filtered_data, file, ensure_ascii=False, indent=2)

    new_stats = get_dxdata_stats(new_data)

    if not new_stats:
        return {
            'success': False
        }

    save_dxdata_version_history(new_stats)

    # 计算差异
    if old_version:
        songs_diff = new_stats['total_songs'] - old_version['total_songs']
        sheets_diff = new_stats['total_sheets'] - old_version['total_sheets']

        return {
            'success': True,
            'new_stats': new_stats,
            'old_stats': old_version,
            'diff': {
                'songs_added': songs_diff,
                'sheets_added': sheets_diff
            }
        }
    else:
        return {
            'success': True,
            'new_stats': new_stats,
            'old_stats': None,
            'diff': None
        }


def generate_song_unique_id(image_name, chart_type, title):
    """
    生成歌曲唯一ID（6个字符）

    Args:
        image_name: 封面图片文件名（如 "c22d52b387e3f829.png" 或 "c22d52b387e3f829"）
        chart_type: 谱面类型（"dx", "std", 或 "utage"）
        title: 歌曲标题（用于确保ID唯一性）

    Returns:
        str: 6个字符的唯一ID

    Examples:
        >>> generate_song_unique_id("c22d52b387e3f829.png", "dx", "歌曲名")
        'a3f5e2'
        >>> generate_song_unique_id("c22d52b387e3f829", "std", "歌曲名")
        'b7c1d9'
        >>> generate_song_unique_id("c22d52b387e3f829", "utage", "utage: [好]歌曲名")
        'f1a2b3'
    """
    if image_name.endswith('.png'):
        image_name = image_name[:-4]

    # 组合字符串并生成哈希（所有类型都包含 title）
    combined = f"{image_name}_{chart_type}_{title}"
    hash_obj = hashlib.md5(combined.encode())

    # 取前3个字节转为十六进制（6个字符）
    short_id = hash_obj.digest()[:3].hex()

    return short_id


# ----------------------------------------------------------------------------
# 定时更新调度器：每周日 22:00（服务器本地时间）自动跑一次
# ----------------------------------------------------------------------------

_weekly_thread = None
_weekly_thread_lock = threading.Lock()


def _seconds_until_next_sunday_2200() -> float:
    """计算距离下一个 周日 22:00（服务器本地时间）的秒数。"""
    now = datetime.now()
    # weekday(): Monday=0 … Sunday=6
    days_ahead = (6 - now.weekday()) % 7
    target = (now + timedelta(days=days_ahead)).replace(
        hour=22, minute=0, second=0, microsecond=0,
    )
    if target <= now:
        target += timedelta(days=7)  # 今天 22:00 已过，跳到下周日
    return (target - now).total_seconds()


def start_weekly_update_scheduler(urls, save_to=None):
    """启动每周日 22:00 自动跑 update_dxdata_with_comparison 的后台线程。
    幂等：重复调用不会起多个线程。

    Args:
        urls: 传给 update_dxdata_with_comparison 的 url 参数
        save_to: 传给 update_dxdata_with_comparison 的本地保存路径
    """
    global _weekly_thread
    with _weekly_thread_lock:
        if _weekly_thread is not None and _weekly_thread.is_alive():
            return

        def _loop():
            while True:
                try:
                    sleep_s = _seconds_until_next_sunday_2200()
                    target = datetime.now() + timedelta(seconds=sleep_s)
                    logger.info(
                        f"[DxData] Next weekly update at "
                        f"{target.strftime('%Y-%m-%d %H:%M:%S')} ({int(sleep_s)}s)"
                    )
                    time.sleep(sleep_s)
                    logger.info("[DxData] → Running weekly auto-update")
                    result = update_dxdata_with_comparison(urls, save_to)
                    diff = (result or {}).get('diff', {})
                    logger.info(
                        f"[DxData] ✓ Weekly update done: "
                        f"songs +{diff.get('songs_added', 0)}, "
                        f"sheets +{diff.get('sheets_added', 0)}"
                    )
                except Exception as e:
                    logger.error(f"[DxData] ✗ Weekly update failed: {e}", exc_info=True)
                    # 失败后稍睡 60s 再算下一次，避免极端情况下错误循环
                    time.sleep(60)

        _weekly_thread = threading.Thread(
            target=_loop, daemon=True, name="WeeklyDxdataUpdate",
        )
        _weekly_thread.start()
        logger.info("[DxData] ✓ Weekly update scheduler started")
