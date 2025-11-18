import requests
import json
import os
import copy
from datetime import datetime
from modules.config_loader import MAIMAI_VERSION, DXDATA_VERSION_FILE

def merge_json(source, target):
    """递归合并两个 JSON 结构（dict / list / 基础类型）"""
    # dict 合并逻辑
    if isinstance(source, dict) and isinstance(target, dict):
        for key, value in source.items():
            if key not in target:
                target[key] = copy.deepcopy(value)
            else:
                src_val, tgt_val = value, target[key]

                # 字符串互补逻辑
                if isinstance(src_val, str) and isinstance(tgt_val, str):
                    if src_val and not tgt_val:
                        target[key] = src_val
                    # 若 target 非空则保留，不动
                    continue

                # 列表逻辑
                elif isinstance(src_val, list) and isinstance(tgt_val, list):
                    if not tgt_val and src_val:
                        target[key] = copy.deepcopy(src_val)
                    elif tgt_val and not src_val:
                        continue
                    else:
                        for i in range(min(len(src_val), len(tgt_val))):
                            merge_json(src_val[i], tgt_val[i])
                        # 如果 source 比 target 长，追加剩余部分
                        if len(src_val) > len(tgt_val):
                            target[key].extend(copy.deepcopy(src_val[len(tgt_val):]))

                # 递归合并 dict
                elif isinstance(src_val, dict) and isinstance(tgt_val, dict):
                    merge_json(src_val, tgt_val)

                # 类型不一致时以非空值为准
                else:
                    if tgt_val in (None, '', [], {}):
                        target[key] = copy.deepcopy(src_val)

    # list 合并逻辑（顶层）
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

    # 其他类型互补
    else:
        if target in (None, '', [], {}):
            target = copy.deepcopy(source)

    return target


def merge_json_by_key(source, target, key_field):
    """
    按 key_field 匹配并合并 source 与 target。
    适用于顶层结构类似 {"songs": [ {...}, {...} ]}
    """
    result = copy.deepcopy(target)

    for k, v in source.items():
        if isinstance(v, list) and all(isinstance(i, dict) for i in v):
            # 处理列表中的字典（带 key_field）
            target_list = result.get(k, [])
            target_index = {item.get(key_field): item for item in target_list if key_field in item}

            for item in v:
                key_val = item.get(key_field)
                if key_val in target_index:
                    merge_json(item, target_index[key_val])
                else:
                    target_list.append(copy.deepcopy(item))
            result[k] = target_list

        elif isinstance(v, dict):
            # 递归合并 dict
            if k in result and isinstance(result[k], dict):
                merge_json(v, result[k])
            else:
                result[k] = copy.deepcopy(v)

        else:
            # 简单类型：仅在目标为空时更新
            if k not in result or result[k] in (None, '', [], {}):
                result[k] = copy.deepcopy(v)

    return result

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
            # 如果已存在,合并数据
            merge_json(item, target_index[key_val])
        else:
            # 如果不存在,添加新项
            result.append(copy.deepcopy(item))

    return result

def load_dxdata(url):
    try:
        response = requests.get(url)
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
            "cover_url": f"https://dp4p6x0xfi5o9.cloudfront.net/maimai/img/cover/{song['imageName']}.png",
            "cover_name": f"{song['imageName']}",
            "search_acronyms": song.get("searchAcronyms", [])
        }

        sheets_by_type = {"dx": [], "std": [], "utage": []}
        version_by_type = {}

        for sheet in song.get("sheets", []):
            sheet_type = sheet.get("type")
            if "multiverInternalLevelValue" in sheet:
                sheet["internalLevelValue"] = sheet["multiverInternalLevelValue"].get(MAIMAI_VERSION["jp"][-1], sheet["internalLevelValue"])

            if sheet_type in sheets_by_type:
                new_sheet = sheet.copy()
                version_by_type[sheet_type] = new_sheet.pop("version", base_info["version"])
                new_sheet.pop("type", None)
                sheets_by_type[sheet_type].append(new_sheet)

        for sheet_type, sheets in sheets_by_type.items():
            if sheets:
                entry = base_info.copy()
                entry["type"] = sheet_type
                entry["version"] = version_by_type.get(sheet_type, base_info["version"])
                entry["sheets"] = sheets
                result.append(entry)

    return result


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
        # 确保 data 目录存在
        os.makedirs(os.path.dirname(DXDATA_VERSION_FILE), exist_ok=True)

        with open(DXDATA_VERSION_FILE, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


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
    # 加载旧版本信息
    old_version = load_dxdata_version_history()

    # 加载新数据
    new_datas = []
    for url in urls:
        new_datas.append(load_dxdata(url))

    # 只合并 songs 字段
    for i in range(1, len(new_datas)):
        new_datas[0]['songs'] = merge_songs_list(new_datas[i]['songs'], new_datas[0]['songs'], "title")

    new_data = new_datas[0]

    if not new_data:
        return {
            'success': False,
            'message': '❌ データ取得失敗！'
        }


    if save_to:
        with open(save_to, "w", encoding="utf-8") as file:
            json.dump(new_data, file, ensure_ascii=False, indent=2)

    # 获取新数据统计
    new_stats = get_dxdata_stats(new_data)

    if not new_stats:
        return {
            'success': False,
            'message': '❌ データ解析失敗！'
        }

    # 保存新版本信息
    save_dxdata_version_history(new_stats)

    # 计算差异
    if old_version:
        songs_diff = new_stats['total_songs'] - old_version['total_songs']
        sheets_diff = new_stats['total_sheets'] - old_version['total_sheets']

        # 构建消息
        message_parts = ['✅ Dxdata Updated!', '']

        if songs_diff > 0:
            message_parts.append(f'🎵 新曲: +{songs_diff}首')
        elif songs_diff < 0:
            message_parts.append(f'🎵 楽曲: {songs_diff}首')
        else:
            message_parts.append('🎵 新曲: なし')

        if sheets_diff > 0:
            message_parts.append(f'📊 新譜面: +{sheets_diff}個')
        elif sheets_diff < 0:
            message_parts.append(f'📊 譜面: {sheets_diff}個')
        else:
            message_parts.append('📊 新譜面: なし')

        message_parts.append('')
        message_parts.append(f'📅 前回更新: {old_version["timestamp"]}')
        message_parts.append(f'📈 現在: 楽曲{new_stats["total_songs"]}首 / 譜面{new_stats["total_sheets"]}個')

        return {
            'success': True,
            'new_stats': new_stats,
            'old_stats': old_version,
            'diff': {
                'songs_added': songs_diff,
                'sheets_added': sheets_diff
            },
            'message': '\n'.join(message_parts)
        }
    else:
        # 第一次更新
        message_parts = [
            '✅ Dxdata Updated!',
            '',
            f'📈 楽曲: {new_stats["total_songs"]}首',
            f'📊 譜面: {new_stats["total_sheets"]}個',
            '',
            '(初回更新完了！)'
        ]

        return {
            'success': True,
            'new_stats': new_stats,
            'old_stats': None,
            'diff': None,
            'message': '\n'.join(message_parts)
        }
