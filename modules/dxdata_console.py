import requests
import json
import os
import copy
from datetime import datetime
from modules.config_loader import MAIMAI_VERSION, DXDATA_VERSION_FILE

def merge_json(source, target):
    if isinstance(source, dict) and isinstance(target, dict):
        for key, value in source.items():
            if key not in target:
                target[key] = copy.deepcopy(value)
            else:
                # 空字符串逻辑
                if isinstance(value, str) and isinstance(target[key], str):
                    if value and not target[key]:
                        target[key] = value
                    elif target[key] and not value:
                        pass  # 保留 target 的非空值

                # 空列表逻辑
                elif isinstance(value, list) and isinstance(target[key], list):
                    if value and not target[key]:
                        target[key] = copy.deepcopy(value)
                    elif target[key] and not value:
                        pass  # 保留 target 的非空列表
                    else:
                        # 都有内容 -> 递归合并
                        for i in range(min(len(value), len(target[key]))):
                            merge_json(value[i], target[key][i])

                else:
                    # 其他类型递归
                    merge_json(value, target[key])

    elif isinstance(source, list) and isinstance(target, list):
        # 顶层列表合并：先做互补，再递归
        if source and not target:
            target.extend(copy.deepcopy(source))
        elif target and not source:
            pass
        else:
            for i in range(min(len(source), len(target))):
                merge_json(source[i], target[i])

    return target

def merge_json_by_key(source, target, key_field):
    """
    将 source 和 target 中指定 key_field（如 "title"）相同的对象合并。
    假设 source/target 是结构一致的 JSON（顶层为 dict），且 key_field 对应的是 list[dict]
    """
    result = copy.deepcopy(target)

    for k, v in source.items():
        if isinstance(v, list) and all(isinstance(i, dict) for i in v):
            # 是一个对象列表，准备按 key_field 匹配
            target_list = result.get(k, [])
            target_index = {item.get(key_field): item for item in target_list}

            for item in v:
                key = item.get(key_field)
                if key in target_index:
                    merge_json(item, target_index[key])
                else:
                    target_list.append(copy.deepcopy(item))
            result[k] = target_list
        else:
            # 默认使用递归合并
            if k in result:
                merge_json(v, result[k])
            else:
                result[k] = copy.deepcopy(v)

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
            "cover_url": f"https://shama.dxrating.net/images/cover/v2/{song['imageName'].replace('.png', '')}.jpg",
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
                version_by_type[sheet_type] = new_sheet.pop("version", "")
                new_sheet.pop("type", None)
                sheets_by_type[sheet_type].append(new_sheet)

        for sheet_type, sheets in sheets_by_type.items():
            if sheets:
                entry = base_info.copy()
                entry["type"] = sheet_type
                entry["version"] = version_by_type.get(sheet_type, "")
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
    
    for i in range(1, len(new_datas)):
        new_datas[0] = merge_json_by_key(new_datas[i], new_datas[0], "title")

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
