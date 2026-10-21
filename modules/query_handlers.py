"""
查询类业务逻辑处理

包含排名、搜索、RC 计算、导出、用户信息等不依赖 Flask/LINE 队列全局状态的查询函数。
"""

import re

from linebot.v3.messaging import TextMessage

from modules.config_loader import read_dxdata
from modules.export_manager import export_records
from modules.i18n import (
    select_text as get_multilingual_text,
    select_text,
    get_user_language,
    DEFAULT_WEB_LANGUAGE,
    format_catalog,
    language_catalog,
)
from modules.messages.service import (
    generate_calc_carousel,
    generate_export_flex,
    generate_ranking_flex,
    generate_rc_flex,
    generate_song_list_flex,
    generate_status_flex,
    generate_user_info_flex,
    song_error,
)
from modules.commands.command_parsers import format_bpm_number, parse_bpm_number
from modules.record_manager import get_single_ra
from modules.score_calculator import get_note_score
from modules.user_db import get_user, get_user_field, load_all_users

import logging

logger = logging.getLogger(__name__)


def handle_export_command(user_id: str, fmt: str):
    try:
        meta = export_records(user_id, fmt)
    except Exception as e:
        logger.error(f"[Export] ✗ Handler error: user_id={user_id}, fmt={fmt}, error={e}", exc_info=True)
        return TextMessage(text=get_multilingual_text(language_catalog("messages.export_failed_text"), user_id))

    status = meta.get("status")
    if status == "empty":
        return TextMessage(text=get_multilingual_text(language_catalog("messages.export_empty_text"), user_id))
    if status != "ok":
        return TextMessage(text=get_multilingual_text(language_catalog("messages.export_failed_text"), user_id))

    logger.info(f"[Export] ✓ Export delivered: user_id={user_id}, fmt={fmt}, "
                f"size={meta['size']}, best={meta['best_count']}, recent={meta['recent_count']}")
    return generate_export_flex(user_id, meta)


def handle_rc_command(msg: str, user_id: str):
    level_str = re.sub(r"^rc\b[ 　]*", "", msg, flags=re.IGNORECASE).strip()

    try:
        level = float(level_str)
    except ValueError:
        language = get_user_language(user_id)
        error_texts = language_catalog("main.invalid_constant")
        return TextMessage(text=select_text(error_texts, language=language, default_language=DEFAULT_WEB_LANGUAGE))

    if level < 1.0 or level > 15.0:
        language = get_user_language(user_id)
        error_texts = format_catalog("main.constant_out_of_range", level=level)
        return TextMessage(text=select_text(error_texts, language=language, default_language=DEFAULT_WEB_LANGUAGE))

    if round(level, 1) != level:
        language = get_user_language(user_id)
        error_texts = format_catalog("main.constant_precision", level=level)
        return TextMessage(text=select_text(error_texts, language=language, default_language=DEFAULT_WEB_LANGUAGE))

    return get_rc(level, user_id)


def get_rc(level: float, user_id=None):
    rc_data = []
    last_ra = 0

    for i in range(970000, 1005001):
        score = i / 10000
        ra = get_single_ra(level, score)
        if ra != last_ra:
            rc_data.append((score, ra))
            last_ra = ra

    return generate_rc_flex(level, rc_data, user_id)


def get_ranking(user_id, id_use, ver=None):
    user_ver = ver or (get_user(id_use) or {}).get('version', 'jp')

    ranked_users = []
    for uid, data in load_all_users().items():
        if data.get('version', 'jp') != user_ver:
            continue
        if data.get("participate_global_ranking", True) is False:
            continue
        info = data.get('personal_info')
        if info and info.get('rating') and info['rating'] != 'ERROR':
            try:
                rating_val = int(info['rating'])
            except (ValueError, TypeError):
                continue
            ranked_users.append({
                "user_id": uid,
                "name": info.get('name', 'N/A'),
                "rating_int": rating_val,
                "rating": info['rating']
            })

    if not ranked_users:
        return TextMessage(text=get_multilingual_text(language_catalog("messages.ranking_no_data_text"), user_id))

    ranked_users.sort(key=lambda x: x["rating_int"], reverse=True)

    for i, u in enumerate(ranked_users):
        if i == 0:
            u["rank"] = 1
        elif u["rating_int"] == ranked_users[i - 1]["rating_int"]:
            u["rank"] = ranked_users[i - 1]["rank"]
        else:
            u["rank"] = i + 1

    def display_entry(user, highlight=True):
        entry = {key: user[key] for key in ("rank", "name", "rating")}
        if highlight and user["user_id"] == id_use:
            entry["is_user"] = True
        return entry

    if ver is not None:
        return generate_ranking_flex(
            user_id, [display_entry(user, False) for user in ranked_users[:15]],
            nearby_entries=None, ver=user_ver,
        )

    user_idx = next((i for i, user in enumerate(ranked_users)
                     if user["user_id"] == id_use), None)
    top5 = [display_entry(user) for user in ranked_users[:5]]
    user_in_top5 = user_idx is not None and user_idx < 5

    nearby_entries = None
    if not user_in_top5 and user_idx is not None:
        nearby_start = max(5, user_idx - 3)
        nearby_end = min(len(ranked_users), user_idx + 4)
        nearby_entries = [display_entry(user)
                          for user in ranked_users[nearby_start:nearby_end]]

    return generate_ranking_flex(
        user_id, top5, nearby_entries=nearby_entries, ver=user_ver,
    )


def _private_chat_warning(user_id, source_type, message):
    if source_type != 'user':
        return generate_status_flex(
            language_catalog("main.private_chat_title"),
            message, user_id, tone="warning")


def search_by_artist(user_id, artist_query, ver="jp", page=1, source_type="user"):
    warning = _private_chat_warning(
        user_id, source_type, language_catalog("messages.search_group_warning_text"))
    if warning:
        return warning

    songs, _ = read_dxdata(ver)

    matching_songs = []
    query_lower = artist_query.lower()
    for song in songs:
        artist = song.get('artist') or ''
        if query_lower in artist.lower():
            matching_songs.append(song)

    if not matching_songs:
        return song_error(user_id)

    title = f"Artist: {artist_query}"
    return generate_song_list_flex(user_id, title, matching_songs, page, "artist", artist_query)


def search_by_designer(user_id, designer_query, ver="jp", page=1, source_type="user"):
    warning = _private_chat_warning(
        user_id, source_type, language_catalog("messages.search_group_warning_text"))
    if warning:
        return warning

    songs, _ = read_dxdata(ver)

    matching_songs = []
    matched_sheets_map = {}
    query_lower = designer_query.lower()

    for song in songs:
        matched_sheets = []
        for sheet in song.get('sheets', []):
            designer = sheet.get('noteDesigner', '')
            if designer and query_lower in designer.lower():
                matched_sheets.append(sheet)
        if matched_sheets:
            matching_songs.append(song)
            matched_sheets_map[song.get('id', '')] = matched_sheets

    if not matching_songs:
        return song_error(user_id)

    title = f"Designer: {designer_query}"
    return generate_song_list_flex(user_id, title, matching_songs, page, "designer", designer_query, matched_sheets_map)


def search_by_bpm(user_id, bpm_min, bpm_max=None, ver="jp", page=1, source_type="user"):
    warning = _private_chat_warning(
        user_id, source_type, language_catalog("messages.search_group_warning_text"))
    if warning:
        return warning

    songs, _ = read_dxdata(ver)
    exact_match = bpm_max is None
    bpm_max = bpm_min if bpm_max is None else bpm_max
    if bpm_min > bpm_max:
        bpm_min, bpm_max = bpm_max, bpm_min

    matching_songs = []
    for song in songs:
        song_bpm = parse_bpm_number(song.get('bpm'))
        if song_bpm is None:
            continue
        if bpm_min <= song_bpm <= bpm_max:
            matching_songs.append(song)

    if not matching_songs:
        return song_error(user_id)

    matching_songs.sort(key=lambda song: (
        parse_bpm_number(song.get('bpm')) or 0,
        song.get('title') or '',
        song.get('type') or ''
    ))

    if exact_match:
        query = format_bpm_number(bpm_min)
        title = f"BPM: {query}"
    else:
        query = f"{format_bpm_number(bpm_min)}-{format_bpm_number(bpm_max)}"
        title = f"BPM: {query}"

    return generate_song_list_flex(user_id, title, matching_songs, page, "bpm", query)


def calc_by_id(user_id, song_id, ver="jp"):
    songs, _ = read_dxdata(ver)
    matching_song = next((song for song in songs if song.get('id') == song_id), None)

    if not matching_song:
        return song_error(user_id)

    calc_data = []
    for sheet in matching_song.get('sheets', []):
        difficulty = sheet.get('difficulty', 'unknown')

        if difficulty not in ['master', 'remaster']:
            continue

        notes_counts = sheet.get('noteCounts', {})
        level = sheet.get('internalLevelValue', 0)
        notes = {
            'tap': notes_counts.get('tap', 0),
            'hold': notes_counts.get('hold', 0),
            'slide': notes_counts.get('slide', 0),
            'touch': notes_counts.get('touch', 0),
            'break': notes_counts.get('break', 0)
        }

        scores = get_note_score(notes)
        calc_data.append((notes, scores, difficulty, level))

    return generate_calc_carousel(calc_data, user_id)


def get_user_info(user_id, source_type):
    if source_type != "user":
        return generate_status_flex(
            language_catalog("main.private_chat_title"),
            language_catalog("messages.private_info_group_warning_text"),
            user_id,
            tone="warning",
        )

    return generate_user_info_flex(user_id)
