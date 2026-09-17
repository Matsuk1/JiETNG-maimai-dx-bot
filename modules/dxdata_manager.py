import asyncio
import csv
import fcntl
import math
import secrets
import tempfile
from pathlib import Path
from contextlib import contextmanager
from collections import Counter, defaultdict
from modules import config_loader as config
from modules.maimai_manager import normalize, login_to_maimai, get_music_level_lists, get_music_version_lists

import requests
import json
import os
import copy
import hashlib
import logging
import threading
import time
from datetime import datetime, timedelta, timezone
from modules.config_loader import MAIMAI_VERSION, DXDATA_VERSION_FILE

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
        # Keep the stored baseline raw; read_dxdata applies overrides at read time.
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


def _infer_ordered_constant(charts, target_position, level, order):
    """Conditional bounds: omit the target, then reject contradictory anchors."""
    base = int(level.rstrip('+')) * 10
    low = base + (6 if level.endswith('+') else 0)
    high = base + (9 if level.endswith('+') or base < 70 else 5)
    anchors = []
    for row in charts:
        if normalize(row['title']) == 'Link':
            continue
        value = row.get('internalLevelValue')
        if row['position'] == target_position or isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        if not math.isfinite(value) or abs(value * 10 - round(value * 10)) > 1e-8:
            continue
        ticks = round(value * 10)
        if low <= ticks <= high:
            anchors.append((row, ticks if order == 'ascending' else -ticks))
    # Reject every remaining anchor that participates in any inversion, not just
    # adjacent inversions. No inferred values are ever reused as anchors.
    excluded = set()
    maximum = -math.inf
    for row, value in anchors:
        if value < maximum:
            excluded.add(row['position'])
        maximum = max(maximum, value)
    minimum = math.inf
    for row, value in reversed(anchors):
        if value > minimum:
            excluded.add(row['position'])
        minimum = min(minimum, value)
    usable = [row for row, _ in anchors if row['position'] not in excluded]
    before = next((row for row in reversed(usable) if row['position'] < target_position), None)
    after = next((row for row in usable if row['position'] > target_position), None)
    for row, is_lower in ((before, order == 'ascending'), (after, order != 'ascending')):
        if row is not None:
            ticks = round(row['internalLevelValue'] * 10)
            if is_lower:
                low = max(low, ticks)
            else:
                high = min(high, ticks)
    def evidence(row):
        return {key: row[key] for key in ('title', 'type', 'difficulty', 'position', 'internalLevelValue')} if row else None
    return {'min': low / 10, 'max': high / 10,
            'status': 'level_only' if before is None and after is None else ('exact' if low == high else 'range'),
            'before': evidence(before), 'after': evidence(after),
            'excluded_anchors': len(excluded)}


def audit_music_levels(level_lists, dxdata, *, order='ascending', version=None, region='jp'):
    """Equal constants are allowed. Violations identify pairs, not which value is wrong.

    Accept both cached (song.type) and upstream (sheet.type) dxdata schemas.
    Pass version to select a multiverInternalLevelValue override explicitly.
    """
    if order not in ('ascending', 'descending'):
        raise ValueError('order must be ascending or descending')
    if region not in ('jp', 'intl'):
        raise ValueError('region must be jp or intl')
    index = defaultdict(list)
    for song in dxdata['songs']:
        for sheet in song.get('sheets', []):
            key = (normalize(song['title']), sheet.get('type', song.get('type')),
                   sheet['difficulty'])
            index[key].append((song, sheet))

    results, issues = [], []
    matched = total = 0
    for group in level_lists:
        level = group['level']
        if int(level.rstrip('+')) < 12:
            continue
        previous = None
        charts = []
        group_issues = []
        identities = Counter((normalize(r['title']), r['type'], r['difficulty'])
                             for r in group['charts'])
        for position, source in enumerate(group['charts'], 1):
            total += 1
            row = {**source, 'position': position}
            # A saved report may contain enrichment from a different dxdata.
            row.pop('internalLevelValue', None)
            row.pop('song_id', None)
            row.pop('inference', None)
            charts.append(row)
            if normalize(row['title']) == 'Link':
                continue
            key = (normalize(row['title']), row['type'], row['difficulty'])
            candidates = index.get(key, [])
            if len(candidates) != 1 or identities[key] > 1:
                continue
            song, sheet = candidates[0]
            matched += 1
            value = sheet.get('internalLevelValue')
            if version:
                value = sheet.get('multiverInternalLevelValue', {}).get(version, value)
            row.update(song_id=song.get('id'), internalLevelValue=value)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                continue
            if previous is not None:
                prev_value = previous['internalLevelValue']
                inverted = prev_value > value if order == 'ascending' else prev_value < value
                if inverted:
                    group_issues.append({'kind': 'order_conflict', 'level': level,
                                   'before': previous.copy(), 'after': row.copy()})
            # Keep the last known chart across unmatched/unknown entries.
            previous = row
        inferences = {}
        for issue in group_issues:
            for key in ('before', 'after'):
                row = issue[key]
                position = row['position']
                if position not in inferences:
                    inferences[position] = _infer_ordered_constant(charts, position, level, order)
                row['inference'] = inferences[position]
            issue['correction_candidates'] = [
                row for row in (issue['before'], issue['after'])
                if row['inference']['status'] in ('exact', 'range') and
                not row['inference']['min'] <= row['internalLevelValue'] <= row['inference']['max']
            ]
        issues.extend(group_issues)
        results.append({**group, 'charts': charts})
    return {'region': region, 'order': order, 'version': version, 'summary': {
        'levels': len(results), 'charts': total, 'matched': matched,
        'issues': len(issues), 'order_conflicts': sum(i['kind'] == 'order_conflict' for i in issues)},
        'levels': results, 'issues': issues}


def _canonical_music_version(label):
    label = normalize(label)
    return {'でらっくす': 'maimaiでらっくす', 'でらっくす PLUS': 'maimaiでらっくす PLUS',
            'スプラッシュ': 'Splash', 'スプラッシュ PLUS': 'Splash PLUS',
            'maimai DX': 'maimaiでらっくす', 'maimai DX PLUS': 'maimaiでらっくす PLUS'}.get(label, label)


def audit_music_versions(version_lists, dxdata):
    index = defaultdict(list)
    for song in dxdata['songs']:
        for sheet in song.get('sheets', []):
            if sheet['difficulty'] == 'master':
                index[(normalize(song['title']), sheet.get('type', song.get('type')))].append((song, sheet))
    counts = Counter((normalize(row['title']), row['type'])
                     for group in version_lists for row in group['charts'])
    issues = []
    for group in version_lists:
        official = _canonical_music_version(group['version'])
        for source in group['charts']:
            if normalize(source['title']) == 'Link':
                continue
            if source.get('level') and int(source['level'].rstrip('+')) < 12:
                continue
            key = (normalize(source['title']), source['type'])
            candidates = index.get(key, [])
            # Includes the two distinct STD songs named Link; never guess their identities.
            if len(candidates) != 1 or counts[key] != 1:
                continue
            song, sheet = candidates[0]
            current = sheet.get('version', song.get('version', ''))
            if _canonical_music_version(current) != official:
                chart = {**source, 'song_id': song.get('id'), 'version': current}
                issues.append({'kind': 'version_mismatch', 'official_version': official,
                               'chart': chart})
    return issues


_AUDIT_REPORT_PATH = Path('data/dxdata/music_level_audit.json')
_AUDIT_LOCK_PATH = Path('data/dxdata/music_level_audit.lock')
_AUDIT_ANALYSIS_VERSION = 6


def _audit_now():
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def _audit_lock():
    _AUDIT_LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _AUDIT_LOCK_PATH.open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('A check or save is already running') from None
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def _audit_atomic_write(path, write):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=path.parent, prefix='.' + path.name)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='') as stream:
            write(stream)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def _audit_fingerprint():
    digest = hashlib.sha256()
    digest.update(b'constant-order-and-version-v4-level12')
    for path in (config.DXDATA_FILE, config.JP_OVERRIDE_FILE, config.INTL_OVERRIDE_FILE):
        digest.update(str(path).encode())
        digest.update(Path(path).read_bytes() if Path(path).exists() else b'<missing>')
    return digest.hexdigest()


def _persist_audit(report):
    _audit_atomic_write(_AUDIT_REPORT_PATH, lambda stream: json.dump(report, stream, ensure_ascii=False))


def _load_audit_report():
    if not _AUDIT_REPORT_PATH.exists():
        return {'status': 'idle', 'regions': {}}
    return json.loads(_AUDIT_REPORT_PATH.read_text(encoding='utf-8'))


def get_music_level_report():
    report = _load_audit_report()
    if report.get('status') == 'running':
        try:
            with _audit_lock():
                # A live job holds this lock; a free lock means its worker exited.
                report = _load_audit_report()
                if report.get('status') == 'running':
                    for result in report.get('regions', {}).values():
                        if result.get('status') in ('pending', 'running'):
                            result.update(status='failed', error='Check interrupted; please run it again')
                    report['status'] = 'complete'
                    _persist_audit(report)
        except ValueError:
            pass
    if report.get('status') == 'complete' and report.get('analysis_version') != _AUDIT_ANALYSIS_VERSION:
        try:
            with _audit_lock():
                report = _load_audit_report()
                if report.get('status') == 'complete' and report.get('analysis_version') != _AUDIT_ANALYSIS_VERSION:
                    for region, old in list(report.get('regions', {}).items()):
                        if old.get('status') == 'complete' and 'levels' in old:
                            updated = _recheck_music_levels(region, old['levels'],
                                report.get('corrections', {}).get(region, []), old.get('version_lists', []))
                            updated.update(status='complete', fetched_at=old.get('fetched_at'))
                            report['regions'][region] = updated
                    report.update(analysis_version=_AUDIT_ANALYSIS_VERSION,
                                  revision=secrets.token_urlsafe(18), fingerprint=_audit_fingerprint(), checked_at=_audit_now())
                    _persist_audit(report)
        except ValueError:
            pass
    report['stale'] = bool(report.get('fingerprint') and report['fingerprint'] != _audit_fingerprint())
    for result in report.get('regions', {}).values():
        result.pop('levels', None)
        result.pop('version_lists', None)
    return report


def _recheck_music_levels(region, levels, corrections=(), version_lists=None):
    # Each run reviews the baseline anew, not corrections left by an older run.
    songs, versions = config.read_dxdata(region, include_generated=False, include_manual=False)
    if corrections:
        songs = copy.deepcopy(songs)
        config.apply_override_rows(songs, corrections)
    result = audit_music_levels(levels, {'songs': songs, 'versions': versions}, region=region)
    result['version_lists'] = version_lists or []
    version_issues = audit_music_versions(result['version_lists'], {'songs': songs})
    result['issues'].extend(version_issues)
    result['summary']['version_mismatches'] = len(version_issues)
    result['summary']['issues'] = len(result['issues'])
    return result


def start_music_level_check(sega_id, password, aime=0):
    if not isinstance(sega_id, str) or not sega_id.strip() or not isinstance(password, str) or not password:
        raise ValueError('Enter SEGA ID and password to check both versions')
    if isinstance(aime, bool) or not isinstance(aime, int) or not 0 <= aime <= 2:
        raise ValueError('Aime index must be 0, 1 or 2')
    # Acquire before dispatch so separate server workers cannot start duplicate jobs.
    guard = _audit_lock()
    guard.__enter__()
    try:
        report = {'id': secrets.token_urlsafe(18), 'revision': secrets.token_urlsafe(18),
                  'analysis_version': _AUDIT_ANALYSIS_VERSION,
                  'status': 'running', 'started_at': _audit_now(), 'fingerprint': _audit_fingerprint(),
                  'regions': {r: {'status': 'pending'} for r in ('jp', 'intl')},
                  'corrections': {'jp': [], 'intl': []}}
        _persist_audit(report)
        thread = threading.Thread(target=_run_check, args=(report, sega_id.strip(), password, aime, guard), daemon=True)
        thread.start()
    except BaseException:
        guard.__exit__(None, None, None)
        raise
    return report['id']


def _run_check(report, sega_id, password, aime, guard):
    async def run():
        for region in ('jp', 'intl'):
            report['regions'][region] = {'status': 'running'}
            _persist_audit(report)
            try:
                cookies = await asyncio.wait_for(login_to_maimai(sega_id, password, ver=region, aime=aime), 90)
                if cookies == 'MAINTENANCE':
                    raise RuntimeError('Official site is under maintenance')
                if not cookies:
                    raise RuntimeError('Login failed')
                levels = await get_music_level_lists(cookies, ver=region)
                version_lists = await get_music_version_lists(cookies, ver=region)
                result = _recheck_music_levels(region, levels, version_lists=version_lists)
                result.update(status='complete', fetched_at=_audit_now())
                report['regions'][region] = result
            except Exception as exc:
                # No credential, cookie or raw network exception in persisted errors.
                message = str(exc) if isinstance(exc, (RuntimeError, ValueError)) else type(exc).__name__
                report['regions'][region] = {'status': 'failed', 'error': message}
            _persist_audit(report)
    try:
        asyncio.run(run())
        report['status'] = 'complete'
        report['finished_at'] = _audit_now()
        _persist_audit(report)
    finally:
        guard.__exit__(None, None, None)


def save_music_level_correction(revision, region, issue_index, song_id, difficulty, field, value):
    if region not in ('jp', 'intl') or field not in ('internalLevelValue', 'version'):
        raise ValueError('Invalid region or field')
    if isinstance(issue_index, bool) or not isinstance(issue_index, int) or issue_index < 0:
        raise ValueError('Invalid issue index')
    with _audit_lock():
        report = _load_audit_report()
        if report.get('status') != 'complete' or report.get('revision') != revision:
            raise ValueError('Report changed; refresh before saving')
        if report.get('fingerprint') != _audit_fingerprint():
            raise ValueError('DXData or overrides changed; run the check again')
        result = report['regions'].get(region, {})
        if result.get('status') != 'complete' or issue_index >= len(result['issues']):
            raise ValueError('Issue no longer available')
        issue = result['issues'][issue_index]
        if field != ('version' if issue['kind'] == 'version_mismatch' else 'internalLevelValue'):
            raise ValueError('Field does not match this issue')
        allowed = [issue.get(key, {}) for key in ('chart', 'before', 'after')]
        if not song_id or not any(row.get('song_id') == song_id and row.get('difficulty') == difficulty for row in allowed):
            raise ValueError('Select an unambiguous chart from this issue')
        songs, _ = config.read_dxdata(region, include_generated=False, include_manual=False)
        candidates = [song for song in songs if song.get('id') == song_id]
        if len(candidates) != 1:
            raise ValueError('Chart is ambiguous')
        song = candidates[0]
        # CSV schema addresses title/type, so same-name songs cannot safely be edited.
        if sum(s['title'] == song['title'] and s['type'] == song['type'] for s in songs) != 1:
            raise ValueError('Override format cannot distinguish these same-name songs')
        indices = [i for i, sheet in enumerate(song['sheets']) if sheet['difficulty'] == difficulty]
        if len(indices) != 1:
            raise ValueError('Chart difficulty is ambiguous')
        if field == 'internalLevelValue':
            if isinstance(value, bool):
                raise ValueError('Invalid constant')
            try:
                value = float(value)
            except (ValueError, TypeError):
                raise ValueError('Enter a numeric constant') from None
            if not math.isfinite(value) or not 1 <= value <= 15.9 or abs(value * 10 - round(value * 10)) > 1e-8:
                raise ValueError('Constant must have at most one decimal place, between 1 and 15.9')
            value = str(round(value, 1))
        else:
            value = str(value)
            if value != issue.get('official_version'):
                raise ValueError('Choose the official version from this issue')
        # Rewrite only this run's selected set. Never import or append old CSV rows.
        selected = report.setdefault('corrections', {'jp': [], 'intl': []})
        rows = selected.get(region, [])
        key = ([song['title'], song['type'], 'version'] if field == 'version' else
               [song['title'], song['type'], 'sheets', str(indices[0]), field])
        rows = [row for row in rows if row[:-1] != key]
        rows.append(key + [value])
        _save_audit_selection(report, region, rows)
    return get_music_level_report()


def _save_audit_selection(report, region, rows):
    path = Path(config.INTL_OVERRIDE_FILE if region == 'intl' else config.JP_OVERRIDE_FILE)
    selected = report.setdefault('corrections', {'jp': [], 'intl': []})
    rows.sort(key=lambda row: row[:-1])
    _audit_atomic_write(path, lambda stream: csv.writer(stream).writerows(rows))
    selected[region] = rows
    with config._dxdata_cache_lock:
        config._dxdata_cache.clear()
    # Re-evaluate raw dxdata with only this run's selected corrections.
    for name, old in list(report['regions'].items()):
        if old.get('status') == 'complete':
            updated = _recheck_music_levels(name, old['levels'], selected.get(name, []), old.get('version_lists', []))
            updated.update(status='complete', fetched_at=old.get('fetched_at'))
            report['regions'][name] = updated
    report.update(analysis_version=_AUDIT_ANALYSIS_VERSION,
                  revision=secrets.token_urlsafe(18), fingerprint=_audit_fingerprint(), checked_at=_audit_now())
    _persist_audit(report)


def save_music_version_corrections(revision, region):
    """Approve all version mismatches for one region in a single CSV rewrite."""
    if region not in ('jp', 'intl'):
        raise ValueError('Invalid region')
    with _audit_lock():
        report = _load_audit_report()
        if report.get('status') != 'complete' or report.get('revision') != revision:
            raise ValueError('Report changed; refresh before saving')
        if report.get('fingerprint') != _audit_fingerprint():
            raise ValueError('DXData or overrides changed; run the check again')
        result = report.get('regions', {}).get(region, {})
        if result.get('status') != 'complete':
            raise ValueError('Region check is not complete')
        issues = [issue for issue in result['issues'] if issue['kind'] == 'version_mismatch']
        if not issues:
            raise ValueError('No version corrections available')
        songs, _ = config.read_dxdata(region, include_generated=False, include_manual=False)
        replacements = {}
        for issue in issues:
            chart = issue['chart']
            candidates = [song for song in songs if song.get('id') == chart.get('song_id')]
            if not chart.get('song_id') or len(candidates) != 1:
                raise ValueError('Chart is ambiguous')
            song = candidates[0]
            if sum(s['title'] == song['title'] and s['type'] == song['type'] for s in songs) != 1:
                raise ValueError('Override format cannot distinguish these same-name songs')
            if sum(sheet['difficulty'] == chart.get('difficulty') for sheet in song['sheets']) != 1:
                raise ValueError('Chart difficulty is ambiguous')
            value = issue.get('official_version')
            if not isinstance(value, str) or not value:
                raise ValueError('Official version is missing')
            key = (song['title'], song['type'], 'version')
            if key in replacements and replacements[key] != value:
                raise ValueError('Conflicting official versions')
            replacements[key] = value
        rows = [row for row in report.get('corrections', {}).get(region, [])
                if tuple(row[:-1]) not in replacements]
        rows.extend(list(key) + [value] for key, value in replacements.items())
        _save_audit_selection(report, region, rows)
    return get_music_level_report()
