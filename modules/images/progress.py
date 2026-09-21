"""Shared plate and achievement image data builders."""

from modules.images.records import generate_cover
from modules.record_manager import achievement_value, find_chart_record, index_records_by_chart
from modules.song_matcher import normalize_text

PLATE_DIFFICULTIES = ("basic", "advanced", "expert", "master")


def build_plate_entries(songs, records, versions, target_type, target_icons, region):
    record_index = index_records_by_chart(records, normalize_text)
    headers = {difficulty: {'all': 0, 'clear': 0} for difficulty in PLATE_DIFFICULTIES}
    entries = []
    for song in songs:
        if song['version'] not in versions or song['type'] == 'utage':
            continue
        title, chart_type = song['title'], song['type']
        for sheet in song['sheets']:
            difficulty = sheet['difficulty']
            if not sheet['regions'].get(region, False) or difficulty not in headers:
                continue
            headers[difficulty]['all'] += 1
            record = find_chart_record(record_index, title, difficulty, chart_type, normalize_text)
            icon = record[f'{target_type}_icon'] if record else 'back'
            achieved = icon in target_icons
            if achieved:
                headers[difficulty]['clear'] += 1
            if difficulty != 'master':
                continue
            complete_info = {
                diff: bool(item := find_chart_record(record_index, title, diff, chart_type, normalize_text))
                and item[f'{target_type}_icon'] in target_icons
                for diff in PLATE_DIFFICULTIES
            }
            entries.append({
                'img': generate_cover(song['cover_url'], chart_type, icon, target_type,
                                      cover_name=song.get('cover_name'),
                                      complete_info=complete_info, achieved=achieved),
                'level': sheet['level'],
                'achieved': achieved,
                'achievement_rate': achievement_value(record.get('score')) if record else 0.0,
            })
    return entries, headers


def build_progress_entries(songs, records, level, category, rank, region, rank_rule):
    record_index = index_records_by_chart(records, normalize_text)
    target_type, target_icons = rank_rule if rank_rule else (None, ())
    entries = []
    stats = {'achieved': 0, 'unachieved': 0, 'unplayed': 0, 'total': 0}
    for song in songs:
        if song['type'] == 'utage' or category and song.get('category') != category:
            continue
        title, chart_type = song['title'], song['type']
        for sheet in song['sheets']:
            if not sheet['regions'].get(region, False):
                continue
            if level and sheet['level'] not in (("14+", "15") if level == "14+" else (level,)):
                continue
            difficulty = sheet['difficulty']
            stats['total'] += 1
            record = find_chart_record(record_index, title, difficulty, chart_type, normalize_text)
            icon = record.get(f'{target_type}_icon', 'back') if record and rank else 'back'
            achieved = bool(record) and (not rank or icon in target_icons)
            if not record:
                stats['unplayed'] += 1
            elif achieved:
                stats['achieved'] += 1
            else:
                stats['unachieved'] += 1
            entries.append({
                'img': generate_cover(
                    song['cover_url'], chart_type, icon if rank else None,
                    target_type if rank else None, cover_name=song.get('cover_name'),
                    difficulty=difficulty, achieved=achieved if rank else None,
                    song_title=title),
                'level': sheet['level'],
                'internal_level': sheet['internalLevelValue'],
                'achieved': achieved,
                'difficulty': difficulty,
                'achievement_rate': achievement_value(record.get('score')) if record else 0.0,
            })
    return entries, stats
