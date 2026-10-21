"""
命令处理器

包含所有 cmd_* 函数（除依赖队列全局状态的 cmd_status 外），以及共用工具函数。
"""

import asyncio
import logging
import re

from modules.bindtoken_manager import (
    generate_bind_token,
    generate_settings_token,
    generate_unbind_token,
)
from modules.commands.command_config import RANK_COMMANDS
from modules.commands.command_parsers import (
    format_bpm_number,
    parse_bpm_query,
    parse_filter_mode,
    parse_level_records_query,
    parse_level_rank_progress as _parse_level_rank_progress_text,
    parse_note_counts,
    parse_paginated_keyword,
    parse_plate_query,
)
from modules.config_loader import DOMAIN, LIFF_ENABLED, LIFF_ID
from modules.i18n import language_catalog
from modules.image_orchestrator import (
    _download_line_message_content,
    generate_level_rank_progress,
    generate_level_records,
    generate_plate_rcd,
    generate_records,
    generate_version_songs,
    random_song,
    search_song,
)
from modules.liff_urls import build_account_action_url
from modules.messages.service import (
    generate_account_action_flex,
    generate_calc_result_flex,
    generate_status_flex,
    input_error,
    song_error,
)
from modules.query_handlers import (
    _private_chat_warning,
    get_user_info,
    handle_export_command,
    handle_rc_command,
    search_by_artist,
    search_by_bpm,
    search_by_designer,
    get_ranking,
)
from modules.rich_menu_manager import link_rich_menu_for_state
from modules.score_calculator import get_note_score
from modules.score_recognition.recognizer import (
    InvalidScoreImageError,
    recognize_score_image_bytes,
)
from modules.user_db import get_user
from modules.user_manager import add_user

logger = logging.getLogger(__name__)


def _account_action_url(action, path, **params):
    return build_account_action_url(
        DOMAIN,
        action,
        path,
        params,
        liff_enabled=LIFF_ENABLED,
        liff_id=LIFF_ID,
    )


def _check_private_or_warn(ctx, warn_text_dict):
    return _private_chat_warning(ctx.user_id, ctx.source_type, warn_text_dict)


def _has_full_account(user_data):
    return all(k in user_data for k in ['sega_id', 'sega_pwd', 'version'])


def _can_open_settings(user_data):
    return _has_full_account(user_data) or bool(
        user_data.get("import_only")
        or user_data.get("auth_type") == "import_token"
        or user_data.get("import_tokens")
    )


def cmd_profile(ctx):
    return get_user_info(ctx.user_id, ctx.source_type)


def cmd_refresh_menu(ctx):
    try:
        link_rich_menu_for_state(ctx.user_id, get_user(ctx.user_id) or {})
    except Exception as e:
        logger.warning("[RichMenu] Silent refresh failed user_id=%s error=%s", ctx.user_id, e)
    return None


def cmd_unbind_prompt(ctx):
    warn = _check_private_or_warn(ctx, language_catalog("messages.unbind_group_warning_text"))
    if warn is not None:
        return warn
    user_data = get_user(ctx.user_id) or {}
    if not _can_open_settings(user_data):
        return generate_status_flex(
            language_catalog("main.not_linked_title"),
            language_catalog("messages.rebind_not_bound_text"),
            ctx.user_id,
            tone="warning",
        )
    url = _account_action_url(
        "unbind",
        "unbind",
        token=generate_unbind_token(ctx.user_id),
    )
    return generate_account_action_flex("unbind", url, ctx.user_id)


def cmd_ranking(ctx):
    ver_arg = ctx.match.group(3) if ctx.match else None
    return get_ranking(ctx.user_id, ctx.id_use, ver_arg)


def cmd_artist(ctx):
    keyword, page = parse_paginated_keyword(ctx.text)
    return search_by_artist(ctx.user_id, keyword, ctx.mai_ver, page, ctx.source_type)


def cmd_designer(ctx):
    keyword, page = parse_paginated_keyword(ctx.text)
    return search_by_designer(ctx.user_id, keyword, ctx.mai_ver, page, ctx.source_type)


def cmd_bpm(ctx):
    query = parse_bpm_query(ctx.text)
    if query is None:
        return input_error(ctx.user_id)
    return search_by_bpm(
        ctx.user_id,
        query.minimum,
        query.maximum,
        ctx.mai_ver,
        query.page,
        ctx.source_type,
    )


def cmd_song_info(ctx):
    keyword = re.sub(r"(^info|\s+info|ってどんな曲)$", "", ctx.text.strip(), flags=re.IGNORECASE).strip()
    if not keyword:
        quoted_message_id = getattr(ctx.event.message, "quoted_message_id", None)
        if quoted_message_id:
            try:
                image_bytes = _download_line_message_content(quoted_message_id)
                recognition = recognize_score_image_bytes(
                    image_bytes,
                    fields=("main_title",),
                )
            except InvalidScoreImageError:
                return song_error(ctx.user_id)
            keyword = str(
                (recognition.get("parsed") or {}).get("title") or ""
            ).strip()
            if not keyword:
                return song_error(ctx.user_id)
            logger.info(
                "[SongInfo] OCR title search: user_id=%s title=%s",
                ctx.user_id,
                keyword,
            )
    return asyncio.run(search_song(ctx.user_id, keyword, ctx.mai_ver))


def cmd_random_song(ctx):
    keyword = re.sub(r"^random", "", ctx.text).strip()
    return asyncio.run(random_song(ctx.user_id, keyword, ctx.mai_ver))


def cmd_rc(ctx):
    return handle_rc_command(ctx.text, ctx.user_id)


def cmd_export(ctx):
    fmt = ctx.match.group(2).lower()
    return handle_export_command(ctx.user_id, fmt)


def cmd_plate(ctx):
    title, filter_mode = parse_plate_query(ctx.text)
    return asyncio.run(generate_plate_rcd(
        ctx.user_id, ctx.id_use, title, ctx.mai_ver_use, filter_mode=filter_mode))


def cmd_level_records(ctx):
    level, page = parse_level_records_query(ctx.text)
    return asyncio.run(generate_level_records(
        ctx.user_id, ctx.id_use, level, ctx.mai_ver_use, page))


def cmd_version_songs(ctx):
    msg = ctx.text
    title = re.sub(r"\s*\+\s*", " PLUS",
                   re.sub(r"\s+ver$", "", msg, flags=re.IGNORECASE)).strip()
    return asyncio.run(generate_version_songs(ctx.user_id, title, ctx.mai_ver))


def cmd_level_rank_list(ctx):
    level = re.sub(r"\s+levels$", "", ctx.text, flags=re.IGNORECASE)
    return asyncio.run(generate_level_rank_progress(
        ctx.user_id, ctx.user_id, level, ver=ctx.mai_ver))


def cmd_level_rank_progress(ctx):
    msg_lower = ctx.text.lower()
    level, rank = _parse_level_rank_progress_text(msg_lower)
    if not level or not rank:
        return input_error(ctx.user_id)
    filter_mode = parse_filter_mode(msg_lower)
    return asyncio.run(generate_level_rank_progress(
        ctx.user_id, ctx.id_use, level, rank, ctx.mai_ver_use,
        filter_mode=filter_mode))


def cmd_b_records(ctx):
    msg_lower = ctx.text.lower()
    splits = re.split(r"[ \n]", msg_lower, 1)
    first = splits[0]
    rest = splits[1] if len(splits) > 1 else ""
    mode = None
    for aliases, mode_value in RANK_COMMANDS.items():
        if first in aliases:
            mode = mode_value
            break
    if mode is None:
        return input_error(ctx.user_id)
    return asyncio.run(generate_records(
        ctx.user_id, ctx.id_use, mode, rest, ctx.mai_ver_use))


def cmd_calc_notes(ctx):
    notes = parse_note_counts(ctx.text)
    if notes is None:
        return input_error(ctx.user_id)
    return generate_calc_result_flex(
        notes,
        get_note_score(notes),
        user_id=ctx.user_id,
    )


def cmd_bind(ctx):
    warn = _check_private_or_warn(ctx, language_catalog("messages.bind_group_warning_text"))
    if warn is not None:
        return warn
    add_user(ctx.user_id)
    if _has_full_account(get_user(ctx.user_id) or {}):
        return generate_status_flex(
            language_catalog("main.already_linked_title"),
            language_catalog("messages.already_bound_text"),
            ctx.user_id,
            tone="warning",
        )
    url = _account_action_url("bind", "sega_bind", token=generate_bind_token(ctx.user_id))
    return generate_account_action_flex("bind", url, ctx.user_id)


def cmd_rebind(ctx):
    warn = _check_private_or_warn(ctx, language_catalog("messages.rebind_group_warning_text"))
    if warn is not None:
        return warn
    if not _has_full_account(get_user(ctx.user_id) or {}):
        return generate_status_flex(
            language_catalog("main.not_linked_title"),
            language_catalog("messages.rebind_not_bound_text"),
            ctx.user_id,
            tone="warning",
        )
    url = _account_action_url(
        "rebind",
        "sega_bind",
        token=generate_bind_token(ctx.user_id),
        mode="rebind",
    )
    return generate_account_action_flex("rebind", url, ctx.user_id)


def cmd_settings(ctx):
    warn = _check_private_or_warn(ctx, language_catalog("messages.settings_group_warning_text"))
    if warn is not None:
        return warn
    if not _can_open_settings(get_user(ctx.user_id) or {}):
        return generate_status_flex(
            language_catalog("main.not_linked_title"),
            language_catalog("messages.rebind_not_bound_text"),
            ctx.user_id,
            tone="warning",
        )
    url = _account_action_url(
        "settings",
        "settings",
        token=generate_settings_token(ctx.user_id),
    )
    return generate_account_action_flex("settings", url, ctx.user_id)
