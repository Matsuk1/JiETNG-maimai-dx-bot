"""Command-help lookup and message generation."""

import re

from modules.i18n import (
    localized_catalog,
    language_catalog,
    select_text as get_multilingual_text,
)
from modules.messages.layout import (
    body_row,
    help_filter_row,
    flex_text,
    help_ui,
    standard_help_bubble,
)

COMMAND_HELP = localized_catalog("command_help")

EXACT_HELP_ALIASES = {
    "maimai update": "maimai_update",
    "update": "maimai_update",
    "friend list": "friend_list",
    "friends": "friend_list",
    "unbind": "unbind_prompt",
    "bind": "bind",
    "rebind": "rebind",
    "settings": "settings",
    "profile": "profile",
    "getme": "profile",
    "status": "status",
    "refreshmenu": "refreshmenu",
    "rank": "ranking",
    "ranking": "ranking",
    "random": "random_song",
    "rec": "score_recognition",
    "ai-rec": "ai_score_recognition",
}

FIRST_WORD_HELP_ALIASES = {
    "artist": "search_by_artist",
    "designer": "search_by_designer",
    "bpm": "search_by_bpm",
    "rc": "rc",
    "export": "export",
    "成績エクスポート": "export",
    "成绩导出": "export",
    "calc": "calc_notes",
}

SUFFIX_HELP_ALIASES = {
    "record": "song_record",
    "info": "song_info",
    "ver": "version_songs",
    "levels": "level_rank_list",
    "records": "level_records",
    "plate": "plate",
    "prog": "level_rank_progress",
}

REQUIRED_PARAM_HELP_WORDS = (
    set(FIRST_WORD_HELP_ALIASES)
    | (set(SUFFIX_HELP_ALIASES) - {"info", "record"})
)
HIDDEN_HELP_COMMAND_WORDS = {"unknown"}
HELP_INDEX_WORDS = {"help", "commands", "command", "帮助", "幫助", "ヘルプ", "コマンド"}


def command_help_message(help_key, user_id=None):
    if help_key == "help_index":
        return generate_help_index_flex(user_id)
    if help_key == "b_records":
        return generate_b_records_help_flex(user_id)
    category_help = generate_help_category_flex(help_key, user_id)
    if category_help is not None:
        return category_help
    help_data = COMMAND_HELP.get(help_key)
    return generate_standard_help_flex(help_data, user_id) if help_data else None


def detect_command_help_key(text, *, b_command_words=(), progress_rank_pattern=""):
    lowered = re.sub(r"\s+", " ", text.strip()).lower()
    if not lowered:
        return None

    direct_match = EXACT_HELP_ALIASES.get(lowered)
    if direct_match:
        return direct_match
    if lowered in HELP_INDEX_WORDS:
        return "help_index"
    if lowered in SUFFIX_HELP_ALIASES:
        return SUFFIX_HELP_ALIASES[lowered]

    first_word = lowered.split(maxsplit=1)[0]
    if first_word in {"rank", "ranking"}:
        return "ranking"
    if first_word == "random":
        return "random_song"
    if first_word in b_command_words:
        return "b_records"
    if first_word in FIRST_WORD_HELP_ALIASES:
        return FIRST_WORD_HELP_ALIASES[first_word]

    if re.match(r"^.+\s+record$", lowered):
        return "song_record"
    if re.match(r"^.+\s+info$", lowered):
        return "song_info"
    if re.match(r"^.+\s+ver$", lowered):
        return "version_songs"
    if re.match(r"^.+\s+levels$", lowered):
        return "level_rank_list"
    if re.match(r"^.+\s+records(?:[ 　]*\d*)?$", lowered):
        return "level_records"
    if re.match(r"^.+\s+plate(\s*-(uc|up|c))?$", lowered):
        return "plate"
    if progress_rank_pattern and re.match(
        fr"^.+\s*{progress_rank_pattern}\s*prog\s*(?:-(uc|up|c))?$",
        lowered,
    ):
        return "level_rank_progress"
    return detect_missing_param_help_key(lowered)


def detect_missing_param_help_key(text):
    lowered = text.strip().lower()
    if lowered not in REQUIRED_PARAM_HELP_WORDS:
        return None
    return SUFFIX_HELP_ALIASES.get(lowered) or FIRST_WORD_HELP_ALIASES.get(lowered)


HELP_NOTE_DETAIL_LABELS = {
    "限制", "Restriction", "制限",
    "要求", "Requirement", "条件",
    "输出", "Output", "出力",
    "可设置", "Available settings", "設定項目",
}


def _help_i18n(user_id, key):
    return get_multilingual_text(
        language_catalog(f"message_manager.help_details.{key}"),
        user_id,
    )


def _help_mode_card(title, body, accent):
    return {
        "type": "box",
        "layout": "vertical",
        "spacing": "xs",
        "paddingAll": "10px",
        "cornerRadius": "8px",
        "borderWidth": "1px",
        "borderColor": "#E6E8EC",
        "contents": [
            flex_text(title, size="xs", color=accent, weight="bold"),
            flex_text(body, size="xxs", color="#555555"),
        ],
    }


def _help_postback_button(label, data, color="#315B7D", display_text=None):
    action = {
        "type": "postback",
        "label": label,
        "data": data,
    }
    if display_text:
        action["displayText"] = display_text
    return {
        "type": "box",
        "layout": "vertical",
        "height": "32px",
        "cornerRadius": "16px",
        "backgroundColor": color,
        "justifyContent": "center",
        "alignItems": "center",
        "paddingStart": "12px",
        "paddingEnd": "12px",
        "action": action,
        "contents": [
            flex_text(label, size="xxs", color="#FFFFFF", weight="bold", align="center", wrap=False),
        ],
    }


def _help_directory_card(title, desc, commands, action_data, accent):
    return {
        "type": "box",
        "layout": "horizontal",
        "spacing": "sm",
        "paddingAll": "10px",
        "cornerRadius": "8px",
        "borderWidth": "1px",
        "borderColor": "#E6E8EC",
        "alignItems": "center",
        "contents": [
            {
                "type": "box",
                "layout": "vertical",
                "spacing": "xs",
                "flex": 1,
                "contents": [
                    node
                    for node in (
                        flex_text(title, size="xs", color=accent, weight="bold"),
                        flex_text(desc, size="xxs", color="#555555"),
                        flex_text(commands, size="xxs", color="#6B7280") if commands else None,
                    )
                    if node is not None
                ],
            },
            {
                "type": "box",
                "layout": "vertical",
                "width": "86px",
                "contents": [
                    _help_postback_button("HELP", action_data, accent),
                ],
            },
        ],
    }


def _help_note_row(label, desc):
    return {
        "type": "box",
        "layout": "vertical",
        "spacing": "xs",
        "paddingAll": "9px",
        "cornerRadius": "8px",
        "backgroundColor": "#F8FAFC",
        "contents": [
            flex_text(label, size="xs", color="#315B7D", weight="bold"),
            flex_text(desc, size="xxs", color="#555555"),
        ],
    }


def _parse_plain_help(text):
    fields = {"命令": "", "说明": "", "参数": "", "示例": "", "注意": ""}
    current_key = None
    for raw_line in str(text or "").replace("`", "").strip().splitlines():
        line = raw_line.strip()
        if not line:
            continue
        matched = False
        for key in fields:
            prefix = f"{key}:"
            if line.startswith(prefix):
                fields[key] = line[len(prefix):].strip() or fields[key]
                current_key = key
                matched = True
                break
        if not matched and current_key:
            fields[current_key] = f"{fields[current_key]}\n{line}".strip()
    return fields


def _split_help_lines(text):
    if isinstance(text, (list, tuple)):
        return [str(line).strip() for line in text if str(line).strip()]
    return [line.strip() for line in str(text or "").splitlines() if line.strip()]


def _partition_help_detail_lines(text, note_labels):
    detail_lines = []
    note_lines = []
    for line in _split_help_lines(text):
        head, tail = line.split(":", 1) if ":" in line else ("", "")
        label = head.strip() if head.strip() and tail.strip() else None
        if label in note_labels:
            note_lines.append(line)
        else:
            detail_lines.append(line)
    return detail_lines, note_lines


def _help_detail_rows(text, fallback_label, none_text):
    lines = _split_help_lines(text)
    if not lines:
        return [help_filter_row(fallback_label, none_text)] if fallback_label else [body_row(none_text)]

    rows = []
    for line in lines:
        label = fallback_label
        desc = line
        if ":" in line:
            head, tail = line.split(":", 1)
            if head.strip() and tail.strip():
                label = head.strip()
                desc = tail.strip()
        rows.append(help_filter_row(label, desc) if label else body_row(desc))
    return rows


def generate_standard_help_flex(help_data, user_id=None):
    fields = get_multilingual_text(help_data, user_id) if isinstance(help_data, dict) else help_data
    if not isinstance(fields, dict):
        fields = _parse_plain_help(fields)
    command = fields.get("command") or fields.get("命令") or help_ui("help_title", user_id)
    purpose = fields.get("purpose") or fields.get("说明")
    params = fields.get("params") or fields.get("参数")
    examples = fields.get("examples") or fields.get("示例")
    notes = fields.get("notes") or fields.get("注意")
    params, param_note_lines = _partition_help_detail_lines(params, HELP_NOTE_DETAIL_LABELS)
    note_lines = [*_split_help_lines(notes), *param_note_lines]
    none_text = help_ui("none", user_id)
    sections = [
        (help_ui("function", user_id), [
            body_row(purpose or help_ui("default_purpose", user_id))
        ]),
        (help_ui("params", user_id), _help_detail_rows(params, help_ui("params", user_id), none_text)),
        (help_ui("examples", user_id), _help_detail_rows(examples, None, none_text)),
    ]
    if note_lines:
        sections.append((help_ui("notes", user_id), _help_detail_rows(note_lines, None, none_text)))
    return standard_help_bubble(
        title="\n".join(part.strip() for part in str(command or "").split("/") if part.strip()),
        subtitle=help_ui("help_title", user_id),
        sections=sections,
        alt_text=f"{command} {help_ui('help_title', user_id)}",
        user_id=user_id,
    )


def generate_b_records_help_flex(user_id=None):
    modes = [
        ("Best", _help_i18n(user_id, 'b50_best50_b40_best40_b35_best35_b15_best15'), "#E85D75"),
        ("All Best", _help_i18n(user_id, 'ab50_allb50_ab35_allb35'), "#8A63D2"),
        ("Special", _help_i18n(user_id, 'ap50_fdx50_r50_rct50_idlb50_s50_sun50'), "#267D8B"),
    ]
    filters = [
        ("-lv / -level", _help_i18n(user_id, 'level_or_constant_one_value_is_exact_two_values_are_a_range'), "-lv 13.6   /   -lv 14 14.9"),
        ("-diff / -difficulty", _help_i18n(user_id, 'difficulty_supports_bas_adv_exp_mas_rem_or_full_names_multiple_v'), "-diff mas rem"),
        ("-ra / -rating", _help_i18n(user_id, 'chart_rating_one_value_is_exact_two_values_are_a_range'), "-ra 320 360"),
        ("-scr / -score", _help_i18n(user_id, 'achievement_one_value_is_a_lower_bound_two_values_are_a_range'), "-scr 100.5   /   -scr 100 100.5"),
        ("-dx / -dxscore", _help_i18n(user_id, 'without_values_sort_by_dx_score_with_values_filter_dx_score_perc'), "-dx   /   -dx 95 100"),
        ("-star / -dxstar", _help_i18n(user_id, 'dx_stars_one_value_is_exact_two_values_are_a_range'), "-star 5"),
        ("-ver / -version", _help_i18n(user_id, 'version_names_multiple_values_are_allowed_is_treated_as_plus_and'), "-ver buddies prism+"),
        ("-type / -tp", _help_i18n(user_id, 'chart_type_supports_dx_and_std_multiple_values_are_allowed'), "-type dx"),
        ("-next / -nxt", _help_i18n(user_id, 'next_version_preview_using_the_next_rating_structure'), "-nxt"),
        ("-page / -pg", _help_i18n(user_id, 'page_number_starting_from_1'), "-page 2"),
        ("-times / -tm", _help_i18n(user_id, 'display_multiplier_capped_at_2_5'), "-times 2"),
    ]
    sections = [
        (help_ui("usage", user_id), [
            help_filter_row(help_ui("command", user_id), "b50 / b40 / b35 / b15 / ab50 / ap50 / fdx50 / r50 / idlb50 / s50"),
        ]),
        (help_ui("function", user_id), [
            body_row(_help_i18n(user_id, 'generate_best_all_best_special_score_images_with_optional_filter')),
        ]),
        (help_ui("modes", user_id), [
            _help_mode_card(title, body, color)
            for title, body, color in modes
        ]),
        (help_ui("params", user_id), [
            help_filter_row(label, desc, example)
            for label, desc, example in filters
        ]),
        (help_ui("examples", user_id), [
            {
                "type": "box",
                "layout": "vertical",
                "spacing": "xs",
                "paddingAll": "10px",
                "cornerRadius": "8px",
                "backgroundColor": "#F7F8FA",
                "contents": [
                    flex_text("b50 -lv 14 14.9 -diff mas rem -scr 100.5", size="xxs", color="#111111"),
                    flex_text("ab50 -ver buddies -type dx", size="xxs", color="#111111"),
                    flex_text("r50 -page 2", size="xxs", color="#111111"),
                ],
            },
        ]),
        (help_ui("notes", user_id), [
            _help_note_row(_help_i18n(user_id, 'data_required'), _help_i18n(user_id, 'requires_a_linked_account_with_maimai_update_completed_or_data_i')),
            _help_note_row(_help_i18n(user_id, 'querying_others'), _help_i18n(user_id, 'line_mentions_can_query_registered_users_self_only_commands_do_n')),
        ]),
    ]
    return standard_help_bubble(
        title=help_ui("b_title", user_id),
        subtitle=help_ui("b_subtitle", user_id),
        sections=sections,
        alt_text=f"{help_ui('b_title', user_id)} {help_ui('help_title', user_id)}",
        user_id=user_id,
    )


HELP_DIRECTORY_CATEGORIES = [
    {
        "key": "account",
        "title_key": "account_and_system",
        "commands": "help / bind / rebind / settings / profile / unbind / update / export / status",
        "desc_key": "binding_settings_profile_sync_export_and_status",
        "color": "#E85D75",
        "items": [
            ("help", "help_index"),
            ("bind", "bind"),
            ("rebind", "rebind"),
            ("settings", "settings"),
            ("profile", "profile"),
            ("unbind", "unbind_prompt"),
            ("update", "maimai_update"),
            ("export", "export"),
            ("status", "status"),
        ],
    },
    {
        "key": "scores",
        "title_key": "score_images",
        "commands": "b50 / b40 / ab50 / ap50 / fdx50 / r50 / idlb50 / s50",
        "desc_key": "best_all_best_recent_and_special_score_images",
        "color": "#8A63D2",
        "items": [
            ("b50", "b_records"),
            ("b40", "b_records"),
            ("ab50", "b_records"),
            ("ap50", "b_records"),
            ("fdx50", "b_records"),
            ("r50", "b_records"),
            ("idlb50", "b_records"),
            ("s50", "b_records"),
        ],
    },
    {
        "key": "songs",
        "title_key": "songs_and_records",
        "commands": "info / rec / ai-rec / record",
        "desc_key": "song_details_score_image_recognition_single_song_records_and_son",
        "color": "#267D8B",
        "items": [
            ("info", "song_info"),
            ("rec", "score_recognition"),
            ("ai-rec", "ai_score_recognition"),
            ("record", "song_record"),
        ],
    },
    {
        "key": "search",
        "title_key": "search",
        "commands": "artist / designer / bpm / random",
        "desc_key": "search_by_artist_designer_bpm_or_random_conditions",
        "color": "#2F7D51",
        "items": [
            ("artist", "search_by_artist"),
            ("designer", "search_by_designer"),
            ("bpm", "search_by_bpm"),
            ("random", "random_song"),
        ],
    },
    {
        "key": "lists",
        "title_key": "lists_and_progress",
        "commands": "records / levels / ver / plate / prog",
        "desc_key": "level_lists_constant_lists_plate_completion_and_target_progress",
        "color": "#B86E19",
        "items": [
            ("records", "level_records"),
            ("levels", "level_rank_list"),
            ("ver", "version_songs"),
            ("plate", "plate"),
            ("prog", "level_rank_progress"),
        ],
    },
    {
        "key": "social",
        "title_key": "social",
        "commands": "friends",
        "desc_key": "friend_list_and_friend_record_lookup",
        "color": "#315B7D",
        "items": [
            ("friends", "friend_list"),
        ],
    },
    {
        "key": "tools",
        "title_key": "tools",
        "commands": "rank / rc / calc / refreshmenu",
        "desc_key": "ranking_rating_breakdown_note_scoring_and_utility_commands",
        "color": "#6B7280",
        "items": [
            ("rank", "ranking"),
            ("rc", "rc"),
            ("calc", "calc_notes"),
            ("refreshmenu", "refreshmenu"),
        ],
    },
]


HELP_DIRECTORY_BY_KEY = {
    category["key"]: category
    for category in HELP_DIRECTORY_CATEGORIES
}


def _help_category_title(category, user_id):
    return _help_i18n(user_id, category["title_key"])


def _help_category_desc(category, user_id):
    return _help_i18n(user_id, category["desc_key"])


def _help_command_summary(help_key, category, user_id):
    if help_key == "b_records":
        return _help_i18n(user_id, "generate_best_all_best_special_score_images_with_optional_filter")
    help_data = localized_catalog("command_help").get(help_key)
    if not help_data:
        return _help_category_desc(category, user_id)
    fields = _parse_plain_help(get_multilingual_text(help_data, user_id))
    return fields.get("说明") or fields.get("function") or _help_category_desc(category, user_id)


def generate_help_index_flex(user_id=None):
    sections = [
        (help_ui("categories", user_id), [
            _help_directory_card(
                _help_category_title(category, user_id),
                _help_category_desc(category, user_id),
                category["commands"],
                f"help {category['items'][0][1] if category['key'] == 'scores' or len(category['items']) == 1 else category['key']}",
                category["color"],
            )
            for category in HELP_DIRECTORY_CATEGORIES
        ]),
        (help_ui("detail_hint", user_id), [
            help_filter_row(_help_i18n(user_id, 'single_command'), _help_i18n(user_id, 'send_b50_help_artist_help_bpm_help_and_similar_forms_for_full_us')),
            help_filter_row(_help_i18n(user_id, 'missing_arguments'), _help_i18n(user_id, 'commands_that_need_arguments_also_show_help_when_sent_without_ar')),
        ]),
    ]
    return standard_help_bubble(
        title=help_ui("catalog_title", user_id),
        subtitle=help_ui("catalog_subtitle", user_id),
        sections=sections,
        alt_text=f"{help_ui('catalog_title', user_id)}",
        user_id=user_id,
    )


def generate_help_category_flex(category_key, user_id=None):
    category = HELP_DIRECTORY_BY_KEY.get(category_key)
    if category is None:
        return None

    rows = [
        _help_directory_card(
            label,
            _help_command_summary(help_key, category, user_id),
            "",
            f"help {help_key}",
            category["color"],
        )
        for label, help_key in category["items"]
    ]
    sections = [
        (help_ui("function", user_id), [
            body_row(_help_category_desc(category, user_id)),
        ]),
        (help_ui("command", user_id), rows),
    ]
    return standard_help_bubble(
        title=_help_category_title(category, user_id),
        subtitle=help_ui("catalog_title", user_id),
        sections=sections,
        alt_text=f"{_help_category_title(category, user_id)} {help_ui('catalog_title', user_id)}",
        user_id=user_id,
    )
