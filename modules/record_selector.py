"""
成绩筛选与排序逻辑

将 select_records 及其辅助函数从 main.py 中分离，保持纯数据变换，无 Flask/LINE 依赖。
"""

import math
import re

from modules.config_loader import MAIMAI_VERSION
from modules.maimai_utils import parse_level_value
from modules.record_manager import achievement_value, get_ideal_score, get_single_ra


def _record_level_value(record):
    try:
        return float(record.get("internalLevelValue", 0) or 0)
    except (TypeError, ValueError):
        return 0.0


def _parse_level_filter_values(raw_level):
    values = parse_level_value(str(raw_level).strip())
    if not values:
        return []
    return [float(v) for v in values]


def _filter_records_by_level(song_record, parts):
    if not parts:
        return song_record, None

    if len(parts) == 1:
        level_values = _parse_level_filter_values(parts[0])
        if not level_values:
            return song_record, None
        value_set = {round(v, 1) for v in level_values}
        filtered = [
            x for x in song_record
            if round(_record_level_value(x), 1) in value_set
        ]
        return filtered, str(parts[0])

    start_values = _parse_level_filter_values(parts[0])
    stop_values = _parse_level_filter_values(parts[1])
    if not start_values or not stop_values:
        return song_record, None

    lv_start = min(start_values)
    lv_stop = max(stop_values)
    if lv_start > lv_stop:
        lv_start, lv_stop = lv_stop, lv_start

    filtered = [
        x for x in song_record
        if lv_start <= _record_level_value(x) <= lv_stop
    ]
    return filtered, f'{parts[0]} ~ {parts[1]}'


def _filter_numeric_range(records, values, value_for, *, exact=False):
    start = values[0]
    if len(values) == 1:
        if exact:
            return [record for record in records if value_for(record) == start], start, None
        return [record for record in records if value_for(record) >= start], start, None
    stop = values[1]
    return [record for record in records if start <= value_for(record) <= stop], start, stop


def select_records(song_record, type="best50", command="", ver="jp"):
    page = 1
    times = 1
    sort_rule = lambda x: (x["ra"], float(x["score"][:-1]))
    filter_rules = [
        (lambda x: not x['new_song']),
        (lambda x: x['new_song'])
    ]
    details = {}
    if command:
        cmds = re.findall(r"-(\w+)(?:\s+([^-]+))?", command)
        for cmd, cmd_num in cmds:
            if cmd in ["diff", "difficulty"]:
                aliases = dict(bas='basic', adv='advanced', exp='expert', mas='master', rem='remaster')
                valid = {'basic', 'advanced', 'expert', 'master', 'remaster'}
                difficulties = [aliases.get(value, value) for value in cmd_num.lower().split()]
                difficulties = [value for value in difficulties if value in valid]
                if difficulties:
                    song_record = [x for x in song_record if x.get('difficulty', '').lower() in difficulties]
                    details['Diff'] = ' '.join(difficulties)
            elif cmd in ["lv", "level"]:
                parts = cmd_num.split()
                filtered_records, detail = _filter_records_by_level(song_record, parts)
                song_record = filtered_records
                if detail:
                    details['Lv'] = detail
            elif cmd in ["next", "nxt"]:
                filter_rules = [
                    (lambda x: x['version'] != MAIMAI_VERSION[ver][-1]),
                    (lambda x: x['version'] == MAIMAI_VERSION[ver][-1])
                ]
                details['NextVer'] = 'ON'
            elif cmd in ["ra", "rating"]:
                parts = cmd_num.split()
                song_record, start, stop = _filter_numeric_range(
                    song_record, list(map(int, parts[:2])), lambda record: record['ra'], exact=True)
                details['RA'] = str(start) if stop is None else f'{start} ~ {stop}'
            elif cmd in ["dx", "dxscore"]:
                parts = cmd_num.split()
                if not parts:
                    sort_rule = lambda x: (x["dx_percentage"], float(x["score"][:-1]))
                    details['Sort'] = 'DX Score'
                else:
                    values = [int(re.sub(r"\D", "", value)) for value in parts[:2]]
                    song_record, start, stop = _filter_numeric_range(
                        song_record, values, lambda record: record['dx_percentage'] * 100)
                    details['DxScr'] = (f'≧ {start}%' if stop is None else f'{start}% ~ {stop}%')
            elif cmd in ["dxstar", "star"]:
                parts = cmd_num.split()
                values = [int(re.sub(r"\D", "", value)) for value in parts[:2]]
                song_record, start, stop = _filter_numeric_range(
                    song_record, values, lambda record: record['dx_star'], exact=True)
                details['Star'] = str(start) if stop is None else f'{start} ~ {stop}'
            elif cmd in ["score", "scr"]:
                parts = cmd_num.split()
                values = [float(re.sub(r"[^0-9.]", "", value)) for value in parts[:2]]
                song_record, start, stop = _filter_numeric_range(
                    song_record, values, lambda record: float(record['score'].replace("%", "")))
                details['Scr'] = (f'≧ {start:.4f}%' if stop is None else f'{start}% ~ {stop}%')
            elif cmd in ["ver", "version"]:
                versions = [value.replace("+", " PLUS").lower()
                            .replace("dx", "maimaiでらっくす")
                            .replace("deluxe", "maimaiでらっくす")
                            for value in cmd_num.split()]
                song_record = [x for x in song_record if (x.get('version') or '').lower() in versions]
                details['Ver'] = ' '.join(
                    version.replace("maimaiでらっくす", "dx").replace("plus", "")[:3].strip()
                    + ('+' if 'plus' in version else '') for version in versions)
            elif cmd in ["type", "tp"]:
                valid_types = [value for value in cmd_num.lower().split() if value in ('dx', 'std')]
                if valid_types:
                    song_record = [x for x in song_record if x.get('type', '').lower() in valid_types]
                    details['Type'] = ' / '.join(t.upper() for t in valid_types)
            elif cmd in ["page", "pg"]:
                try:
                    page = max(1, int(cmd_num.strip()))
                    if page > 1:
                        details['Page'] = str(page)
                except ValueError:
                    pass
            elif cmd in ["times", "tm"]:
                parts = cmd_num.split()
                times = min(float(parts[0]), 2.5)
                if times > 0:
                    details['Times'] = times
                else:
                    times = 1

    up_songs = down_songs = []

    up_songs_data = list(filter(filter_rules[0], song_record))
    down_songs_data = list(filter(filter_rules[1], song_record))

    num_50 = math.ceil(50 * times / 5) * 5
    num_35 = math.ceil(35 * times / 5) * 5
    num_25 = math.ceil(25 * times / 5) * 5
    num_15 = math.ceil(15 * times / 5) * 5

    if type == "idlb50":
        for rcd in up_songs_data + down_songs_data:
            ideal_score, score_icon = get_ideal_score(float(rcd['score'][:-1]))
            rcd['score'] = f"{ideal_score:.4f}%"
            if score_icon:
                rcd['score_icon'] = score_icon
            if ideal_score == 101:
                rcd['combo_icon'] = "app"
            rcd['ra'] = get_single_ra(rcd['internalLevelValue'], ideal_score, ideal_score == 101)

    selection_type = "best50" if type == "idlb50" else type
    selection_rules = {
        "best50": (("up", num_35, None, None), ("down", num_15, None, None)),
        "best40": (("up", num_25, None, None), ("down", num_15, None, None)),
        "best35": (("up", num_35, None, None),),
        "best15": (("down", num_15, None, None),),
        "allb35": (("all", num_35, None, None),),
        "allb50": (("all", num_50, None, None),),
        "apb50": (("up", num_35, "combo_icon", {"ap", "app"}), ("down", num_15, "combo_icon", {"ap", "app"})),
        "fdxb50": (("up", num_35, "sync_icon", {"fdx", "fdxp"}), ("down", num_15, "sync_icon", {"fdx", "fdxp"})),
    }

    if selection_type in selection_rules:
        song_sources = {"up": up_songs_data, "down": down_songs_data, "all": song_record}
        selected_songs = {"up": [], "down": []}
        target_side = {"up": "up", "down": "down", "all": "up"}
        for source_key, count, field, allowed_values in selection_rules[selection_type]:
            source = song_sources[source_key]
            filtered_source = source if field is None else [x for x in source if x.get(field) in allowed_values]
            selected_songs[target_side[source_key]] = sorted(
                filtered_source,
                key=sort_rule,
                reverse=True,
            )[(page-1)*count : page*count]
        up_songs = selected_songs["up"]
        down_songs = selected_songs["down"]

    elif type == "unknown":
        up_songs = list(filter(lambda x: x['version'] == "UNKNOWN", song_record))

    elif type == "rct50":
        up_songs = song_record

    elif type == "sun50":
        sun_targets = (
            (100.4000, 100.4999, 100.5000),
            (99.9000, 99.9999, 100.0000),
        )
        sun_candidates = []
        for song in song_record:
            score = achievement_value(song.get("score"))
            target = next(
                (target for low, high, target in sun_targets if low <= score <= high),
                None,
            )
            if target is not None:
                sun_candidates.append((song, score, target))
        selected_sun_candidates = sorted(
            sun_candidates,
            key=lambda item: (
                round(item[2] - item[1], 4),
                -float(item[0].get("internalLevelValue", 0) or 0),
                str(item[0].get("name", "")),
                str(item[0].get("difficulty", "")),
                str(item[0].get("type", "")),
            ),
        )[(page-1)*num_50 : page*num_50]
        sun_groups = {target: [] for _, _, target in sun_targets}
        for song, _, target in selected_sun_candidates:
            sun_groups[target].append(song)
        up_songs = sun_groups[100.5000]
        down_songs = sun_groups[100.0000]

    else:
        return select_records(song_record, "best50", command, ver)

    return up_songs, down_songs, details
