"""
图片生成编排层

将 main.py 中所有图片生成和查询函数集中于此，消除对 Flask/队列全局变量的依赖。
LINE configuration 对象在此模块内懒加载，避免循环引用。
"""

import asyncio
import logging
import random

from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    ImageMessage,
    MessagingApi,
    MessagingApiBlob,
    TextMessage,
)

from modules.config_loader import LINE_CHANNEL_ACCESS_TOKEN, TEMP_VERSION, read_dxdata
from modules.images.composition import compose_generated_images, generate_profile_image
from modules.images.records import (
    build_plate_entries,
    build_progress_entries,
    generate_level_rank_progress_image,
    generate_plate_image,
    generate_records_picture,
)
from modules.images.skins import user_image
from modules.images.songs import generate_version_list, song_info_generate
from modules.images.upload import upload_generated_image
from modules.maimai_manager import (
    get_friend_info,
    get_friend_records,
    get_single_record,
    login_to_maimai,
)
from modules.maimai_utils import parse_level_value
from modules.messages.service import (
    friend_rcd_error,
    generate_search_results_flex,
    generate_song_image_message,
    info_error,
    level_not_supported,
    level_record_not_found,
    level_record_page_hint,
    maintenance_error,
    mention_error,
    mention_no_matching_data,
    mention_record_error,
    no_matching_data,
    plate_error,
    record_error,
    segaid_error,
    song_error,
    system_error,
    version_error,
)
from modules.commands.command_config import MAX_SEARCH_RESULTS
from modules.commands.command_parsers import resolve_progress_category as _resolve_progress_category
from modules.i18n import language_catalog, select_text as get_multilingual_text
from modules.record_manager import (
    PLATE_RULES,
    PROGRESS_RANKS,
    SUPPORTED_PROGRESS_LEVELS,
    filter_progress_entries,
    get_detailed_info,
    read_record,
)
from modules.record_selector import select_records
from modules.song_matcher import find_matching_songs
from modules.user_db import get_user
from modules.user_manager import get_user_timezone

logger = logging.getLogger(__name__)

# LINE API configuration — lazily created to avoid import-time side effects.
_line_configuration: Configuration | None = None


def _get_line_configuration() -> Configuration:
    global _line_configuration
    if _line_configuration is None:
        _line_configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
    return _line_configuration


# ==================== 小工具 ====================

def login_rate_limit_message(user_id):
    return TextMessage(text=get_multilingual_text(language_catalog("main.login_rate_limited"), user_id))


def _get_user_bg_filter(user_id):
    udata = get_user(user_id) or {}
    if not udata.get('bg_enabled', False):
        return None
    bg_files = udata.get('bg_files', [])
    try:
        bg_blur = int(udata.get('bg_blur', 20))
    except (ValueError, TypeError):
        bg_blur = 20
    try:
        bg_overlay = int(udata.get('bg_overlay', 40))
    except (ValueError, TypeError):
        bg_overlay = 40
    return {
        "files": bg_files,
        "blur": max(0, min(40, bg_blur)),
        "overlay": max(0, min(120, bg_overlay)),
    }


@user_image
def _compose_user_images(images, user_id):
    return compose_generated_images(
        images,
        timezone_offset=get_user_timezone(user_id),
        bg_filter=_get_user_bg_filter(user_id),
    )


def _record_user_or_error(user_id, target_user_id):
    user_data = get_user(target_user_id)
    if user_data and "personal_info" in user_data:
        return user_data, None
    if target_user_id != user_id:
        return None, mention_error(user_id)
    return None, segaid_error(user_id) if not user_data else info_error(user_id)


def _missing_record_error(user_id, target_user_id):
    return mention_record_error(user_id) if target_user_id != user_id else record_error(user_id)


async def _upload_image_message(image, user_id):
    original_url, preview_url = await upload_generated_image(image, user_id)
    if original_url and preview_url:
        return ImageMessage(original_content_url=original_url, preview_image_url=preview_url)
    logger.error("[Image] Upload failed")
    return system_error(user_id)


def _download_line_message_content(message_id: str) -> bytes:
    with ApiClient(_get_line_configuration()) as api_client:
        content = MessagingApiBlob(api_client).get_message_content(message_id)
    return bytes(content)


# ==================== 歌曲信息 / 图片生成 ====================

@user_image
def generate_profile(user_info, scale=1, user_id=None):
    icon_url = user_info.get("icon_url") or ""
    rounded_icon = False
    if user_id and any(name in icon_url for name in ("80e228baead19c06.png", "c22d52b387e3f829.png")):
        try:
            with ApiClient(_get_line_configuration()) as api_client:
                profile = MessagingApi(api_client).get_profile(user_id)
                if profile.picture_url:
                    user_info = {**user_info, "icon_url": profile.picture_url}
                    rounded_icon = True
        except Exception as e:
            logger.error("[Image] ✗ Failed to load user profile image: %s", e)
    return generate_profile_image(user_info, scale=scale, rounded_icon=rounded_icon)


@user_image
async def random_song(user_id, key="", ver="jp"):
    songs, _ = read_dxdata(ver)
    valid_songs = []

    if key:
        level_values = parse_level_value(key)
        if not level_values:
            return song_error(user_id)

    for song in songs:
        for sheet in song['sheets']:
            if sheet['regions'][ver]:
                if not key or sheet['internalLevelValue'] in level_values:
                    valid_songs.append(song)
                    break

    if not valid_songs:
        return song_error(user_id)

    song = random.choice(valid_songs)
    song_id = song.get('id')

    user_tz = get_user_timezone(user_id)
    song_img = song_info_generate(
        song,
        timezone_offset=user_tz,
        ver=ver,
        bg_filter=_get_user_bg_filter(user_id),
    )
    original_url, preview_url = await upload_generated_image(song_img, user_id)
    return generate_song_image_message(song_id, original_url, preview_url, user_id, mode='info')


@user_image
async def search_song(user_id, acronym, ver="jp"):
    songs, _ = read_dxdata(ver)

    matching_songs = find_matching_songs(acronym, songs, max_results=MAX_SEARCH_RESULTS)

    if not matching_songs:
        return song_error(user_id)

    if len(matching_songs) > 1:
        return generate_search_results_flex(user_id, matching_songs, 'song')

    song = matching_songs[0]
    song_id = song.get('id')
    return await search_song_by_id(user_id, song_id, ver)


@user_image
async def search_song_by_id(user_id, song_id, ver="jp"):
    songs, _ = read_dxdata(ver)
    matching_song = next((song for song in songs if song.get('id') == song_id), None)

    if not matching_song:
        return song_error(user_id)

    user_tz = get_user_timezone(user_id)
    song_img = song_info_generate(
        matching_song,
        timezone_offset=user_tz,
        ver=ver,
        bg_filter=_get_user_bg_filter(user_id),
    )
    original_url, preview_url = await upload_generated_image(song_img, user_id)
    return generate_song_image_message(song_id, original_url, preview_url, user_id, mode='info')


@user_image
async def get_song_record(user_id, id_use, acronym, ver="jp"):
    _, error = _record_user_or_error(user_id, id_use)
    if error:
        return error

    song_record = read_record(id_use, ver=ver)

    if not song_record:
        return _missing_record_error(user_id, id_use)

    songs, _ = read_dxdata(ver)
    matching_songs = find_matching_songs(acronym, songs, max_results=MAX_SEARCH_RESULTS)

    if not matching_songs:
        return song_error(user_id)

    recorded_charts = {(record["cover_name"], record["type"]) for record in song_record}
    songs_with_records = [
        song
        for song in matching_songs
        if (song["cover_name"], song["type"]) in recorded_charts
    ]

    if not songs_with_records:
        return song_error(user_id)

    if len(songs_with_records) > 1:
        return generate_search_results_flex(user_id, songs_with_records, "record", id_use)

    song_id = songs_with_records[0].get("id")
    return await get_song_record_by_id(user_id, id_use, song_id, ver)


@user_image
async def get_song_record_by_id(user_id, id_use, song_id, ver="jp"):
    _, error = _record_user_or_error(user_id, id_use)
    if error:
        return error

    song_record = read_record(id_use, ver=ver)

    if not song_record:
        return _missing_record_error(user_id, id_use)

    songs, _ = read_dxdata(ver)
    matching_song = next((song for song in songs if song.get('id') == song_id), None)

    if not matching_song:
        return song_error(user_id)

    played_data = [
        record for record in song_record
        if record['cover_name'] == matching_song['cover_name']
        and record['type'] == matching_song['type']
    ]
    if not played_data:
        return song_error(user_id)

    try:
        target_user = get_user(id_use) if user_id == id_use else None
        if target_user and 'sega_id' in target_user and 'sega_pwd' in target_user:
            cookies = await login_to_maimai(
                target_user['sega_id'], target_user['sega_pwd'],
                ver=ver, aime=target_user.get('aime', 0),
            )
            if cookies == "RATE_LIMITED":
                return login_rate_limit_message(user_id)
            if cookies is None:
                logger.warning("[Song Record] Login failed: user_id=%s", user_id)

            if cookies:
                detailed_records = await get_single_record(
                    played_data[0]['name'], matching_song['type'], cookies, ver=ver)
                if detailed_records and detailed_records != "MAINTENANCE":
                    details = {record['difficulty']: record for record in detailed_records}
                    fields = ('score', 'dx_score', 'score_icon', 'combo_icon', 'sync_icon',
                              'play_count', 'last_play_time')
                    for record in played_data:
                        detail = details.get(record['difficulty'])
                        if detail:
                            record.update({field: detail[field] for field in fields})
                    get_detailed_info(played_data, ver)
    except Exception:
        logger.exception("[Song Record] Failed to get details for %s", matching_song.get('title', 'unknown'))

    user_tz = get_user_timezone(user_id)
    song_img = song_info_generate(
        matching_song,
        played_data,
        timezone_offset=user_tz,
        ver=ver,
        bg_filter=_get_user_bg_filter(user_id),
    )
    original_url, preview_url = await upload_generated_image(song_img, user_id)
    return generate_song_image_message(song_id, original_url, preview_url, user_id, mode='record')


@user_image
async def generate_plate_rcd(user_id, id_use, title, ver="jp", filter_mode=None):
    _id_use_data, error = _record_user_or_error(user_id, id_use)
    if error:
        return error

    if len(title) not in (2, 3):
        return plate_error(user_id)

    song_record = read_record(id_use, ver=ver)

    if not song_record:
        return _missing_record_error(user_id, id_use)

    title = title.replace("晓", "暁").replace("极", "極")

    version_name = title[0]
    plate_type = title[1:]

    songs, versions = read_dxdata(ver)

    target_version = [version['version'] for version in versions if version_name in version['abbr']]
    if version_name in TEMP_VERSION["abbr"]:
        target_version.insert(0, TEMP_VERSION["title"])
    if not target_version:
        return version_error(user_id)

    if plate_type not in PLATE_RULES:
        return plate_error(user_id)
    target_type, target_icon = PLATE_RULES[plate_type]

    version_rcd_data = [record for record in song_record if record['version'] in target_version]
    if not version_rcd_data:
        return version_error(user_id)

    target_data, target_num = build_plate_entries(
        songs, version_rcd_data, target_version, target_type, target_icon, ver)

    target_data = filter_progress_entries(target_data, filter_mode)

    if not target_data:
        return mention_no_matching_data(user_id) if id_use != user_id else no_matching_data(user_id)

    plate_img = generate_plate_image(target_data, title, headers=target_num)

    user_info = _id_use_data.get('personal_info')
    profile_img = generate_profile(user_info, user_id=id_use)
    img = _compose_user_images([profile_img, plate_img], user_id)

    return await _upload_image_message(img, user_id)


@user_image
async def generate_level_rank_progress(user_id, id_use, level, rank=None, ver="jp", filter_mode=None):
    _id_use_data, error = _record_user_or_error(user_id, id_use)
    if error:
        return error

    songs, _ = read_dxdata(ver)
    target_category = None
    is_level_target = level in SUPPORTED_PROGRESS_LEVELS
    if not is_level_target:
        target_category = _resolve_progress_category(level)
        if not target_category:
            return level_not_supported(user_id)

    if rank is not None and rank not in PROGRESS_RANKS:
        return song_error(user_id)

    song_record = read_record(id_use, ver=ver)

    if not song_record:
        return _missing_record_error(user_id, id_use)

    target_data, stats = build_progress_entries(
        songs, song_record, level if is_level_target else None, target_category,
        rank, ver, PROGRESS_RANKS.get(rank))

    if not target_data:
        return mention_no_matching_data(user_id) if id_use != user_id else no_matching_data(user_id)

    target_data = filter_progress_entries(target_data, filter_mode)

    if not target_data:
        return mention_no_matching_data(user_id) if id_use != user_id else no_matching_data(user_id)

    level_display = level.replace("+", "⁺") if is_level_target else target_category
    rank_display = rank.upper().replace("+", "⁺") if rank else ""

    record_img = generate_level_rank_progress_image(
        target_data,
        level_display,
        rank_display,
        stats,
        group_by="internal_level" if is_level_target else "level",
        show_progress_suffix=is_level_target,
        ver=ver,
    )

    user_info = _id_use_data.get('personal_info')
    profile_img = generate_profile(user_info, user_id=id_use)
    img = _compose_user_images([profile_img, record_img], user_id)

    return await _upload_image_message(img, user_id)


@user_image
async def generate_records(user_id, id_use, type="best50", command="", ver="jp"):
    _id_use_data, error = _record_user_or_error(user_id, id_use)
    if error:
        return error

    recent = (type == "rct50")
    recent_type = (type == "best40")
    song_record = read_record(id_use, recent, recent_type, ver=ver)
    if not song_record:
        return _missing_record_error(user_id, id_use)

    up_songs, down_songs, details = select_records(song_record, type, command, ver)
    if not up_songs and not down_songs:
        return song_error(user_id)

    if type == "unknown":
        type = "未だ知らず"

    record_img = generate_records_picture(
        up_songs,
        down_songs,
        type.upper(),
        ver,
        details,
    )

    user_info = _id_use_data.get('personal_info')
    profile_img = generate_profile(user_info, user_id=id_use)
    img = _compose_user_images([profile_img, record_img], user_id)

    return await _upload_image_message(img, user_id)


@user_image
async def generate_friend_record(user_id, friend_code, type="best50", cmd="", ver="jp"):
    _udata = get_user(user_id)
    if not _udata or 'sega_id' not in _udata or 'sega_pwd' not in _udata:
        return segaid_error(user_id)

    sega_id = _udata['sega_id']
    sega_pwd = _udata['sega_pwd']

    async def fetch_friend_data():
        cookies = await login_to_maimai(sega_id, sega_pwd, ver)
        if cookies is None or cookies in ("MAINTENANCE", "RATE_LIMITED"):
            return cookies, None, None
        tasks = [
            get_friend_info(cookies, friend_code, ver),
            get_friend_records(cookies, friend_code, ver)
        ]
        friend_info, friend_records = await asyncio.gather(*tasks)
        return None, friend_info, friend_records

    error, friend_info, friend_records = await fetch_friend_data()

    if error == "RATE_LIMITED":
        return login_rate_limit_message(user_id)
    if error == "MAINTENANCE":
        return maintenance_error(user_id)
    if error is None and friend_records is None:
        return segaid_error(user_id)

    if isinstance(friend_info, dict) and friend_info.get("error") == "MAINTENANCE":
        return maintenance_error(user_id)

    if friend_records == "MAINTENANCE":
        return maintenance_error(user_id)

    if not friend_info or not friend_records:
        return friend_rcd_error(user_id)

    recent_type = (type == "best40")
    friend_records = get_detailed_info(friend_records, ver, recent_type)

    up_songs, down_songs, details = select_records(friend_records, type, cmd, ver)

    if not (len(up_songs) + len(down_songs)):
        return song_error(user_id)

    user_info_img = generate_profile(friend_info)
    rcd_img = generate_records_picture(
        up_songs,
        down_songs,
        type.upper(),
        ver,
        details,
    )
    img = _compose_user_images([user_info_img, rcd_img], user_id)

    original_url, preview_url = await upload_generated_image(img, user_id)
    message = [
        TextMessage(text=get_multilingual_text(language_catalog("messages.friend_rcd_text"), user_id).format(name=friend_info["name"])),
        ImageMessage(original_content_url=original_url, preview_image_url=preview_url)
    ]

    return message


@user_image
async def generate_level_records(user_id, id_use, level, ver="jp", page=1):
    _id_use_data, error = _record_user_or_error(user_id, id_use)
    if error:
        return error

    song_record = read_record(id_use, ver=ver)

    if not song_record:
        return _missing_record_error(user_id, id_use)

    level_values = parse_level_value(level)
    if not level_values:
        return song_error(user_id)

    lv_min = min(level_values)
    lv_max = max(level_values)
    command = f"-lv {lv_min} {lv_max} -page {page}"

    up_level_list, down_level_list, _ = select_records(song_record, "best50", command, ver)

    if not up_level_list and not down_level_list:
        return level_record_not_found(level, page, user_id)

    title = f"Lv {level}"

    record_img = generate_records_picture(
        up_level_list,
        down_level_list,
        title.replace("+", "⁺"),
        ver,
    )

    user_info = _id_use_data.get('personal_info')
    profile_img = generate_profile(user_info, user_id=id_use)
    img = _compose_user_images([profile_img, record_img], user_id)

    original_url, preview_url = await upload_generated_image(img, user_id)
    message = [
        ImageMessage(original_content_url=original_url, preview_image_url=preview_url),
        level_record_page_hint(page, user_id) if page == 1 else None
    ]
    message = [m for m in message if m]
    return message


@user_image
async def generate_version_songs(user_id, version_title, ver="jp"):
    songs, versions = read_dxdata(ver)

    version_title = version_title.lower().replace("dx", "maimaiでらっくす").replace("deluxe", "maimaiでらっくす")
    target_version_info = next(
        (version for version in versions if version_title == version["version"].lower()),
        None,
    )
    target_versions = [target_version_info["version"]] if target_version_info else []
    if not target_versions:
        return version_error(user_id)

    songs_data = [
        song
        for song in songs
        if song["version"] in target_versions and song["type"] != "utage"
    ]
    version_list_img = generate_version_list(
        songs_data,
        version_info=target_version_info,
        ver=ver,
    )

    try:
        img = compose_generated_images(
            [version_list_img],
            timezone_offset=get_user_timezone(user_id),
            bg_filter=_get_user_bg_filter(user_id),
        )
    finally:
        version_list_img.close()

    return await _upload_image_message(img, user_id)
