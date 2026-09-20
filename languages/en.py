"""English language plugin."""

LANGUAGE = {
    "code": "en",
    "label": "English",
    "aliases": ("en-us", "en-gb"),
}

TEXTS = {
    "web": {
        "loading": "Loading",
        "notice_html": "<strong>Notice</strong><br>All information you provide will be securely stored in encrypted format and will not be shared with third parties.<br><br>However, this service is operated by an individual and does not provide official guarantees or support.<br>Given the nature of this service, if you have concerns about security or operational policies, please refrain from using it.<br>You provide information at your own judgment and responsibility.",
        "error": {
            "title": "Error",
            "fallback_message": "An error occurred while processing your request.",
        },
        "unbind": {
            "title": "Unlink Account",
            "lead": "Confirm in this browser to remove your linked account from JiETNG.",
            "type": "Type",
            "account": "SEGA Account",
            "server": "Server",
            "warning": "This will delete saved account credentials, related settings, records, and recent records. This action cannot be undone.",
            "submit": "Unlink Account",
        },
        "success": {
            "titles": {
                "settings": "Settings Saved",
                "import_token": "Import Token Created",
                "unbind": "Account Unlinked",
                "rebind": "Update Successful",
                "bind": "Binding Successful",
            },
            "descriptions": {
                "settings": "Your settings have been saved successfully.",
                "import_token": "Save this token in the bookmarklet. Your JiETNG profile will be initialized after the first record upload.",
                "unbind": "Your linked account and saved records have been removed from JiETNG.",
                "rebind": "Your account settings have been successfully updated.",
                "bind": "Successfully linked with JiETNG.",
            },
            "token": {
                "shown_once": "Token shown only once",
                "copy": "Copy Token",
                "copied": "Copied",
            },
        },
    }
}

# BEGIN MESSAGE MANAGER TEXTS
TEXTS["message_manager"] = {'help_ui': {'b_subtitle': 'Best / All Best / special score images and filters',
             'b_title': 'B-Series Score Images',
             'catalog_subtitle': 'Send command-help for detailed usage',
             'catalog_title': 'Command Directory',
             'categories': 'Categories',
             'command': 'Command',
             'default_purpose': 'Show help for this command.',
             'detail_hint': 'Detailed Help',
             'docs_button': 'Help Docs',
             'examples': 'Examples',
             'function': 'Description',
             'help_title': 'Command Help',
             'modes': 'Modes',
             'none': 'None',
             'notes': 'Notes',
             'params': 'Parameters',
             'usage': 'Usage'},
 'score_recognition': {'break_detail': 'BREAK Details',
                       'break_detail_source_multiple': 'Calc inference: most likely of {count} '
                                                       'candidates',
                       'break_detail_source_single': 'Calc inference: unique matching combination',
                       'break_row_source_multiple': 'The BREAK row has {count} Calc candidates; '
                                                    'details above are for the current candidate',
                       'breakdown': 'Judgements',
                       'calc_corrected': 'Calc automatically resolved the judgements',
                       'calc_incomplete': 'Calc score matches, but judgement rows are incomplete; '
                                          '-? marks missing data',
                       'calc_inferred': 'BREAK was inferred from chart notes and Calc',
                       'calc_mismatch': 'Calc found a mismatch that cannot be isolated to one OCR '
                                        'cell',
                       'calc_uncertain': 'Calc found a mismatch; ? marks suspected OCR cells',
                       'calc_validated': 'Calc confirmed the achievement and judgements',
                       'compact_fix': 'Fix BREAK',
                       'constant': 'Level',
                       'copy_fix': 'Copy Fix Command',
                       'empty': 'No judgement details were recognized.',
                       'loss_detail': 'Detailed Judgements',
                       'manual_fix': 'Manual Correction',
                       'manual_fix_hint': 'Copy the command and correct the achievement or values '
                                          'before sending. Rows are TAP, HOLD, SLIDE, TOUCH, and '
                                          'BREAK; an all-zero row is a missing-data placeholder '
                                          'and must be filled in.',
                       'status': 'Status',
                       'title': 'Judgement Details',
                       'validated': 'MISS validated against chart note counts'},
 'service_status': {'queue': 'Queue Status',
                    'songs': 'Songs DB',
                    'summary': 'Summary',
                    'tasks_today': 'Tasks Today',
                    'title': 'JiETNG Service Status',
                    'uptime': 'Uptime'}}
# END MESSAGE MANAGER TEXTS

# BEGIN HELP DETAILS
TEXTS["message_manager"]["help_details"] = {'ab50_allb50_ab35_allb35': 'ab50 / allb50, ab35 / allb35',
 'account_and_system': 'Account and System',
 'achievement_one_value_is_a_lower_bound_two_values_are_a_range': 'Achievement. One value is a '
                                                                  'lower bound; two values are a '
                                                                  'range.',
 'ap50_fdx50_r50_rct50_idlb50_s50_sun50': 'ap50, fdx50, r50 / rct50, idlb50, s50 / sun50',
 'b50_best50_b40_best40_b35_best35_b15_best15': 'b50 / best50, b40 / best40, b35 / best35, b15 / '
                                                'best15',
 'best_all_best_recent_and_special_score_images': 'Best, All Best, Recent, and special score '
                                                  'images.',
 'binding_settings_profile_sync_export_and_status': 'Binding, settings, profile, sync, export, and '
                                                    'status.',
 'chart_rating_one_value_is_exact_two_values_are_a_range': 'Chart rating. One value is exact; two '
                                                           'values are a range.',
 'chart_type_supports_dx_and_std_multiple_values_are_allowed': 'Chart type. Supports dx and std; '
                                                               'multiple values are allowed.',
 'commands_that_need_arguments_also_show_help_when_sent_without_ar': 'Commands that need arguments '
                                                                     'also show help when sent '
                                                                     'without arguments.',
 'data_required': 'Data required',
 'difficulty_supports_bas_adv_exp_mas_rem_or_full_names_multiple_v': 'Difficulty. Supports bas, '
                                                                     'adv, exp, mas, rem, or full '
                                                                     'names; multiple values are '
                                                                     'allowed.',
 'display_multiplier_capped_at_2_5': 'Display multiplier, capped at 2.5.',
 'dx_stars_one_value_is_exact_two_values_are_a_range': 'DX stars. One value is exact; two values '
                                                       'are a range.',
 'friend_list_and_friend_record_lookup': 'Friend list and friend record lookup.',
 'generate_best_all_best_special_score_images_with_optional_filter': 'Generate Best / All Best / '
                                                                     'special score images with '
                                                                     'optional filters.',
 'level_lists_constant_lists_plate_completion_and_target_progress': 'Level lists, constant lists, '
                                                                    'plate completion, and target '
                                                                    'status.',
 'level_or_constant_one_value_is_exact_two_values_are_a_range': 'Level or constant. One value is '
                                                                'exact; two values are a range.',
 'line_mentions_can_query_registered_users_self_only_commands_do_n': 'LINE mentions can query '
                                                                     'registered users; self-only '
                                                                     'commands do not accept '
                                                                     'mentions.',
 'lists_and_progress': 'Lists and Targets',
 'missing_arguments': 'Missing arguments',
 'next_version_preview_using_the_next_rating_structure': 'Next-version preview using the next '
                                                         'rating structure.',
 'page_number_starting_from_1': 'Page number, starting from 1.',
 'querying_others': 'Querying others',
 'ranking_rating_breakdown_note_scoring_and_utility_commands': 'Ranking, rating breakdown, note '
                                                               'scoring, and utility commands.',
 'requires_a_linked_account_with_maimai_update_completed_or_data_i': 'Requires a linked account '
                                                                     'with maimai update '
                                                                     'completed, or data imported '
                                                                     'through Import Token / '
                                                                     'Developer API.',
 'score_images': 'Score Images',
 'search': 'Search',
 'search_by_artist_designer_bpm_or_random_conditions': 'Search by artist, designer, BPM, or random '
                                                       'conditions.',
 'send_b50_help_artist_help_bpm_help_and_similar_forms_for_full_us': 'Send b50-help, artist-help, '
                                                                     'bpm-help, and similar forms '
                                                                     'for full usage.',
 'single_command': 'Single command',
 'social': 'Social',
 'song_details_score_image_recognition_single_song_records_and_son': 'Song details, score-image '
                                                                     'recognition, single-song '
                                                                     'records, and song IDs.',
 'songs_and_records': 'Songs and Records',
 'tools': 'Tools',
 'version_names_multiple_values_are_allowed_is_treated_as_plus_and': 'Version names. Multiple '
                                                                     'values are allowed; + is '
                                                                     'treated as PLUS, and '
                                                                     'dx/deluxe are normalized.',
 'without_values_sort_by_dx_score_with_values_filter_dx_score_perc': 'Without values, sort by DX '
                                                                     'score; with values, filter '
                                                                     'DX score percentage.'}
# END HELP DETAILS

TEXTS["message_manager"].update({
    "button_labels": {"uri": "View Details", "message": "Try it"},
    "vote_labels": {"support": "Support", "oppose": "Oppose"},
    "search_titles": {
        "song": "Song Search Results ({count})",
        "record": "Record Search Results ({count})",
    },
    "rating_chart_title": "Rating Chart for {level}",
    "song_unit": "songs",
})

# BEGIN MAIN TEXTS
TEXTS["main"] = {'account_already_bound': 'A SEGA account is already linked. To rebind, please use the unbind '
                          'command first to unlink your account.',
 'account_not_linked': 'No account is linked.',
 'already_linked_title': 'Already Linked',
 'login_rate_limited': 'The JP login rate limit was reached. This operation has stopped. Please try again later.',
 'candidates_failed': 'Failed to fetch the account list. Please try again later.',
 'constant_out_of_range': 'Constant {level} is out of range. Please enter a value between 1.0 and '
                          '15.0.',
 'constant_precision': 'Constant {level} is invalid. Only one decimal place is allowed (e.g., '
                       '13.2).',
 'correction_format_body': 'Use 7 lines: fix-rcd TITLE, achievement, then TAP, HOLD, SLIDE, TOUCH, '
                           'and BREAK. Each row must be CP/PF/GR/GD/MS.',
 'correction_format_title': 'Invalid Correction Format',
 'fields_required': 'Please fill in all fields.',
 'invalid_constant': 'Invalid constant. Please enter a value between 1.0 and 15.0.',
 'invalid_credentials': 'Invalid SEGA ID or password. Please check and try again.',
 'maintenance': 'The official website is under maintenance. Please try again later.',
 'no_linked_account': 'No account is linked.',
 'not_linked_title': 'Not Linked',
 'private_chat_title': 'Use Private Chat',
 'recognition_failed_body': 'This score image could not be read. Check that the result screen is '
                            'fully visible and try again.',
 'recognition_failed_title': 'Recognition Failed',
 'score_image_required_body': 'Reply to a score image with {command_text}.',
 'score_image_required_title': 'Score Image Required',
 'sega_id_immutable': 'You cannot change the SEGA ID.',
 'token_invalid': 'Invalid token.',
 'token_missing': 'Token not provided.',
 'unbind_token_invalid': 'The token is invalid or expired. Send unbind again.',
 'vote_success': 'Thank you for voting!\n'
                 '\n'
                 'Support: {support_count} ({support_percent:.1f}%)\n'
                 'Oppose: {oppose_count} ({oppose_percent:.1f}%)'}
# END MAIN TEXTS

# BEGIN COMMAND HELP
TEXTS["command_help"] = {'bind': '命令: bind\n'
         '说明: Return a one-time SEGA account binding URL for first-time linking.\n'
         '参数: No arguments: send bind as-is.\n'
         'Restriction: private chat only; group chats receive a safety warning.\n'
         '示例: bind',
 'calc_notes': '命令: calc <tap> <hold> <slide> [touch] <break>\n'
               '说明: Calculate per-note score values from note counts.\n'
               '参数: Required: <tap> <hold> <slide> <break>; with 4 numbers, they are parsed as '
               'TAP/HOLD/SLIDE/BREAK.\n'
               'Optional: [touch]; with 5 numbers, the 4th is TOUCH and the 5th is BREAK.\n'
               'Format: all values must be non-negative integers separated by spaces.\n'
               '示例: calc 500 50 80 30\n'
               'calc 500 50 80 20 30',
 'export': '命令: export <json|xml>\n'
           '说明: Export your score data in the selected format.\n'
           '参数: Required: <format>, must be json or xml.\n'
           'Output: returns a temporary download URL and a copy-link button on success.\n'
           'Requirement: score data must exist; empty data returns an empty-data message.\n'
           '示例: export json\n'
           'export xml',
 'friend_list': '命令: friends\n'
                '说明: Show your saved friend list from maimai NET.\n'
                '参数: No arguments: send friend list or friends as-is.\n'
                'Related: use friend-rcd <friend number or name> [score image type] [filters] for friend score images.\n'
                '示例: friends',
 'level_rank_list': '命令: <level or constant> levels\n'
                    '说明: Show songs for a level or constant.\n'
                    '参数: Required: <level or constant>; supports 13, 13+, 14, 13.6, and similar '
                    'formats.\n'
                    'Matching: integer/+ values match level; decimals match exact constant.\n'
                    '示例: 13.6 levels\n'
                    '14+ levels',
 'level_rank_progress': '命令: <level or category><rank> prog [-uc|-up|-c]\n'
                        '说明: Show rank-target status at a level or song category.\n'
                        '参数: Required: <level or category>; levels support 11-15; categories '
                        'support vocaloid, touhou, popani, gekichu, game, and maimai.\n'
                        'Required: <rank>, written after the level/category; supports s, s+, ss, '
                        'ss+, sss, sss+, fc, fc+, ap, ap+, fdx, fdx+.\n'
                        'Optional: -uc shows unfinished target charts, -up shows unplayed charts, '
                        '-c shows completed target charts.\n'
                        'Format: levels may be joined directly, for example 14sss+ prog; put a '
                        'space after category names, for example vocaloid sss+ prog.\n'
                        '示例: 14sss+ prog\n'
                        '13ap prog -uc\n'
                        'vocaloid sss+ prog\n'
                        'popani ss+ prog -up',
 'level_records': '命令: <level or constant> records [page]\n'
                  '说明: Show a record list for a level or constant.\n'
                  '参数: Required: <level or constant>; supports 13, 13+, 14, 13.6, and similar '
                  'formats.\n'
                  'Optional: [page], positive integer starting from 1; defaults to page 1.\n'
                  'Matching: integer/+ values match level; decimals match exact constant.\n'
                  '示例: 13.6 records\n'
                  '14 records 2',
 'maimai_update': '命令: maimai update\n'
                  '说明: Sync played song records from maimai NET.\n'
                  '参数: No arguments: send maimai update or update as-is.\n'
                  '示例: maimai update\n'
                  '注意: A linked SEGA account is required.',
 'plate': '命令: <plate title> plate [-uc|-up|-c]\n'
          '说明: Show completion status for plate/title goals.\n'
          '参数: Required: <plate title>, placed before plate, such as 真極 or 檄将.\n'
          'Optional: -uc shows unfinished items, -up shows unplayed items, -c shows completed '
          'items.\n'
          'Format: put the filter at the end; omit it to show full completion.\n'
          '示例: 真極 plate\n'
          '真極 plate -uc',
 'profile': '命令: profile\n'
            '说明: Show your JiETNG account profile, including binding status, server, and language '
            'settings.\n'
            '参数: No arguments: send profile as-is.\n'
            'Restriction: private chat only to avoid exposing personal information.\n'
            '示例: profile',
 'random_song': '命令: random [condition]\n'
                '说明: Recommend a random song.\n'
                '参数: Optional: [condition], such as level, constant, chart type, or difficulty '
                'keywords.\n'
                'Format: separate multiple conditions with spaces; omit conditions to randomize '
                'from all songs.\n'
                '示例: random\n'
                'random 13+ dx\n'
                'random 14 mas',
 'ranking': '命令: rank [jp|intl]\n'
            '说明: Show the global DX Rating ranking.\n'
            '参数: Optional: [server], supports jp and intl; omitted value uses your linked server.\n'
            'Format: put the server after rank, separated by a space.\n'
            'Mention: mention a registered user to show their position in the global ranking. The user must allow record lookup by mention.\n'
            '示例: rank\n'
            'rank intl',
 'rc': '命令: rc <constant>\n'
       '说明: Query Rating Composition / rating breakdown information.\n'
       '参数: Required: <constant>, a number between 1.0 and 15.0.\n'
       'Format: integers and decimals are accepted, such as 13, 13.6, and 14.9.\n'
       'Restriction: values outside 1.0-15.0 or non-numeric input return an input error.\n'
       '示例: rc 14\n'
       'rc 13.6',
 'rebind': '命令: rebind\n'
           '说明: Return an account edit URL for updating an already linked SEGA account.\n'
           '参数: No arguments: send rebind as-is.\n'
           'Requirement: a SEGA account must already be linked.\n'
           'Restriction: private chat only.\n'
           '示例: rebind',
 'refreshmenu': '命令: refreshmenu\n'
                "说明: Re-link the sender's LINE Rich Menu based on current binding state.\n"
                '参数: No arguments: send refreshmenu as-is.\n'
                "Restriction: only affects the sender's Rich Menu.\n"
                '示例: refreshmenu',
 'score_recognition': '命令: rec\n'
                      '说明: Recognizes the full score; returns a generated result image when '
                      'validation is complete, or a correction card when manual fixes are needed.\n'
                      '参数: Must reply to a score image and accepts no other arguments.\n'
                      '示例: rec',
 'search_by_artist': '命令: artist <keyword> [page]\n'
                     '说明: Search songs by artist name.\n'
                     '参数: Required: <keyword>; text after artist is matched against artist names, '
                     'case-insensitively.\n'
                     'Optional: [page], positive integer starting from 1; put it at the end.\n'
                     'Restriction: private chat only to prevent group spam.\n'
                     '示例: artist Nanahira\n'
                     'artist sasakure 2',
 'search_by_bpm': '命令: bpm <BPM or range> [page]\n'
                  '说明: Search songs by exact BPM or BPM range.\n'
                  '参数: Required: <BPM or range>; supports a single value, hyphen range, or '
                  'space-separated range.\n'
                  'Single value: bpm 180 matches BPM 180 exactly.\n'
                  'Range: bpm 0-120 or bpm 120 180 searches an inclusive range; 0 is allowed as an '
                  'endpoint.\n'
                  'Optional: [page], positive integer starting from 1; put it at the end.\n'
                  'Restriction: private chat only.\n'
                  '示例: bpm 180\n'
                  'bpm 0-120\n'
                  'bpm 120 180 2',
 'search_by_designer': '命令: designer <keyword> [page]\n'
                       '说明: Search songs by chart designer.\n'
                       '参数: Required: <keyword>; text after designer is matched against each '
                       "chart's noteDesigner field.\n"
                       'Optional: [page], positive integer starting from 1; put it at the end.\n'
                       'Restriction: private chat only to prevent group spam.\n'
                       '示例: designer Jack\n'
                       'designer chart 2',
 'settings': '命令: settings\n'
             '说明: Return your settings page URL for timezone, language, background image, privacy, '
             'and other options.\n'
             '参数: No arguments: send settings as-is.\n'
             'Restriction: private chat only.\n'
             '示例: settings',
 'song_info': '命令: <song> info\n'
              '说明: Show song details, chart data, and BPM; you can also reply to a result image '
              'with info to recognize its title.\n'
              '参数: For text search, provide a full title, partial title, or alias; no title is '
              'needed when replying to an image.\n'
              'Matching: if multiple songs match, the bot returns selectable candidates.\n'
              '示例: ヒバナ info\n'
              '(reply to image) info',
 'song_record': '命令: <song> record\n'
                '说明: Look up your record by title or alias.\n'
                '参数: Required: <song>, placed before record; accepts full title, '
                'partial title, or alias.\n'
                'Matching: if multiple songs match, the bot returns selectable candidates.\n'
                '示例: ヒバナ record',
 'status': '命令: status\n'
           '说明: Show bot service status, including uptime, task queues, and system resources.\n'
           '参数: No arguments: send status as-is.\n'
           '示例: status',
 'unbind_prompt': '命令: unbind\n'
                  '说明: Return a one-time SEGA account unlink URL. Account data is removed only '
                  'after browser confirmation.\n'
                  '参数: No arguments: send unbind as-is.\n'
                  'Requirement: a SEGA account or Import Token account must already be linked.\n'
                  'Restriction: private chat only.\n'
                  '示例: unbind',
 'version_songs': '命令: <version> ver\n'
                  '说明: Show the song list for a version.\n'
                  '参数: Required: <version>, placed before ver; accepts full version names '
                  'or recognizable aliases.\n'
                  'Format: version names may contain spaces; all text before ver is used '
                  'as the query.\n'
                  '示例: BUDDiES ver\n'
                  'PRiSM PLUS ver'}
# END COMMAND HELP

# BEGIN TEMPLATE TEXTS
TEXTS["web"]["bind"] = {
    "pageTitle": "SEGA Account Binding | JiETNG",
    "pageTitleRebind": "Edit Account Settings | JiETNG",
    "heading": "SEGA Account Binding",
    "headingRebind": "Edit Account Settings",
    "labelSegaid": "SEGA ID",
    "labelPassword": "SEGA Password",
    "labelVersion": "Version",
    "optJp": "JP Version",
    "optIntl": "INTL Version",
    "labelTimezone": "Timezone",
    "labelLanguage": "Language",
    "languagePlatformHint": "Language settings may not apply to third-party platforms outside LINE.",
    "labelBindType": "Link Type",
    "optBindSega": "SEGA Account",
    "optBindImport": "Import Token Only",
    "bindTypeImportHelp": "Do not save SEGA credentials. Upload records from an export tool instead.",
    "submitBtn": "Bind",
    "submitBtnImport": "Generate Token",
    "submitBtnRebind": "Update",
    "noticeTitle": "Notice",
    "aimeModalTitle": "Select Aime",
    "aimeModalDescription": "Choose the account to link.",
    "aimeConfirm": "Confirm",
    "aimeFallbackName": "Aime Account",
    "ratingLabel": "Rating",
    "trophyLabel": "Trophy",
    "accountListError": "Could not fetch the account list."
}
TEXTS["web"]["bind_notice_html"] = "All information you provide will be securely stored in encrypted format and will not be shared with third parties.<br><br>However, this service is operated by an individual and does not provide official guarantees or support. Given the nature of this service, if you have concerns about security or operational policies, please refrain from using it. You provide information at your own judgment and responsibility."
TEXTS["web"]["settings"] = {
    "pageTitle": "Settings | JiETNG",
    "heading": "Settings",
    "labelLanguage": "Language",
    "languagePlatformHint": "Language settings may not apply to third-party platforms outside LINE.",
    "labelTimezone": "Timezone",
    "skinSection": "Skin & background",
    "labelSkin": "Skin",
    "skinUsesBackground": "Uses background images",
    "skinNoBackground": "No background images",
    "skinBackgroundHint": "Uses the background, blur and overlay settings below. Turning backgrounds off uses the default base color.",
    "skinNoBackgroundHint": "This skin does not use background images. Your background settings are kept for when you switch back.",
    "labelBgEnabled": "Background Image",
    "privacyPanelTitle": "Privacy Settings",
    "rankingPanelTitle": "Ranking Settings",
    "labelMentionScoreQuery": "Allow Mention Record Lookup",
    "metaMentionScoreQuery": "When enabled, other users can mention you on LINE to view your record images and progress.",
    "labelGlobalRanking": "Join Global Ranking",
    "metaGlobalRanking": "Shown in the global rank / ranking list.",
    "labelBgBlur": "Background Blur",
    "labelBgOverlay": "Background Fade",
    "bgHint": "If none selected, a random background will be used.",
    "sectionCustomBg": "Custom Background",
    "customBgHint": "Upload your own background images (up to 2, max 5MB each).",
    "labelCustomBg": "Choose Image",
    "uploadSub": "PNG / JPG / JPEG / WebP (max 5MB)",
    "uploadBtn": "Upload",
    "uploadFailed": "Upload failed.",
    "deleteCustomBgBtn": "Delete",
    "deleteCustomBgConfirm": "Delete your custom background?",
    "deleteAllCustomBgBtn": "Delete all",
    "deleteAllCustomBgConfirm": "Delete all custom backgrounds?",
    "submitBtn": "Save",
    "importTokenTitle": "Record Import Token",
    "importTokenHelp": "Use this token to upload processed record JSON from external tools to JiETNG.",
    "importTokenCreate": "Generate Token",
    "importTokenNoteLabel": "Token name",
    "importTokenNotePlaceholder": "e.g. Tool",
    "importTokenNoteRequired": "Please enter a token name.",
    "importTokenResultTitle": "Token (shown only once)",
    "importTokenCopy": "Copy",
    "importTokenCopied": "Copied",
    "importTokenEmpty": "No tokens yet.",
    "importTokenRevoke": "Revoke",
    "importTokenRevoked": "Revoked",
    "importTokenDelete": "Delete",
    "importTokenCreateError": "Failed to generate token.",
    "importTokenRevokeConfirm": "Revoke this import token?",
    "importTokenRevokeError": "Failed to revoke.",
    "importTokenDeleteConfirm": "Delete this revoked import token?",
    "importTokenDeleteError": "Failed to delete."
}
TEXTS["web"]["settings_permissions"] = {
    "panelTitle": "Manage Access Permissions",
    "ownerLabel": "Creator",
    "revokeBtn": "Revoke",
    "revokeConfirm": "Revoke access for this service?",
    "revokeError": "Failed to revoke. Please try again."
}
# END TEMPLATE TEXTS

# BEGIN GENERATED MESSAGE TEXTS
MESSAGE_TEXTS = {'access_error_text': "🙇 There's a lot of traffic right now... Please try again later!",
 'already_bound_text': 'A SEGA account is already linked.\n'
                       '\n'
                       'Use rebind to change password, version, or Aime.\n'
                       'Use settings for timezone, language, background image, and privacy '
                       'options.\n'
                       'To link a different account, unlink the current account with unbind first.',
 'bind_group_warning_text': 'bind is only available in private chat. Message the bot directly.',
 'calc_button_text': 'Note Calc',
 'calc_flex_text': {'alt_multi': 'Note Calc Results',
                    'alt_single': 'Note Calc Result',
                    'max_tap_great': 'Max {count} TAP GREAT',
                    'subtitle': 'Note Calc',
                    'title_distribution': 'Note Distribution'},
 'cannot_do_for_others_text': 'This command can only be used for your own account.',
 'dxdata_current_stats_text': '📈 Current: {songs} Songs / {sheets} Charts',
 'dxdata_fetch_failed_text': '❌ Failed to fetch data!',
 'dxdata_first_update_text': '(Initial update complete!)',
 'dxdata_initial_stats_sheets_text': '📊 Charts: {count}',
 'dxdata_initial_stats_songs_text': '📈 Songs: {count}',
 'dxdata_last_update_text': '📅 Last Update: {timestamp}',
 'dxdata_new_sheets_text': '📊 New Charts: +{count}',
 'dxdata_new_songs_text': '🎵 New Songs: +{count}',
 'dxdata_no_new_sheets_text': '📊 New Charts: None',
 'dxdata_no_new_songs_text': '🎵 New Songs: None',
 'dxdata_parse_failed_text': '❌ Failed to parse data!',
 'dxdata_sheets_decreased_text': '📊 Charts: {count}',
 'dxdata_songs_decreased_text': '🎵 Songs: {count}',
 'dxdata_update_success_text': '✅ Dxdata Updated!',
 'export_alt_text': 'Records exported',
 'export_empty_text': 'No records to export yet. Run `maimai update` first, then try again.',
 'export_failed_text': 'Failed to export records. Please try again later.',
 'export_flex_button_text': 'Download',
 'export_flex_copy_button_text': 'Copy Link',
 'export_flex_footnote_text': 'Link expires in {ttl} minutes',
 'export_flex_summary_text': 'Best: {best}  ·  Recent: {recent}\nFormat: {fmt} ({size_kb} KB)',
 'export_flex_title_text': 'Records Exported',
 'friend_error_text': 'No favorite friends have been registered yet.',
 'friend_list_alt_text': 'Favorite Friends',
 'friend_rcd_error_text': 'The selected user is not in your friend list.',
 'friend_rcd_group_warning_text': 'Friend record commands are only available in private chat. '
                                  'Message the bot directly.',
 'friend_rcd_text': "{name}'s record",
 'info_error_text': 'Your maimai profile has not been saved yet. Run `maimai update` first, then '
                    'try again.',
 'input_error_text': 'Command not recognized. Please check your input.',
 'level_not_supported_text': 'This level constant table is not supported.\n'
                             'Only levels 12 and above are available.',
 'level_record_not_found_text': "No records found for level '{level}' page {page}...",
 'level_record_page_hint_text': 'This is page {page} data!',
 'maintenance_error_text': '🔧 Oh? The official site seems to be under maintenance!\n'
                           "It's not accessible during maintenance hours, so please try again "
                           'later~',
 'mention_error_text': 'The mentioned user is not registered with JiETNG yet.',
 'mention_not_allowed_text': 'The mentioned user has disabled record lookup by mention.',
 'mention_no_matching_data_text': 'The mentioned user has no records matching the criteria.',
 'mention_record_error_text': 'The mentioned user does not have maimai records yet.',
 'nearby_stores_alt_text': 'Nearby maimai Arcade Stores',
 'no_matching_data_text': 'No records matched the criteria.',
 'notice_header_text': '📢 Notice',
 'perm_request_accept_button_text': 'Accept',
 'perm_request_accept_success_text': '✅ Access permission request accepted!\n'
                                     '\n'
                                     'Token ID: {token_id}\n'
                                     'Requester: {requester_name}\n'
                                     '\n'
                                     'This token can now access your account information.',
 'perm_request_already_processed_text': 'This request has already been processed.',
 'perm_request_notification_alt_text': 'You have {count} access permission request(s)',
 'perm_request_notification_subtitle_text': '{count} new requests',
 'perm_request_notification_title_text': 'Access Permission Requests',
 'perm_request_reject_button_text': 'Reject',
 'perm_request_reject_success_text': '✅ Access permission request rejected.\n'
                                     '\n'
                                     'Token ID: {token_id}\n'
                                     'Requester: {requester_name}',
 'plate_error_text': 'Plate not found.',
 'private_info_group_warning_text': 'Personal info commands are only available in private chat. '
                                    'Message the bot directly.',
 'quick_reply_labels': {'account_bind': 'Link Account',
                        'all_best_50': 'All Best 50',
                        'maimai_update': 'maimai update',
                        'recent_50': 'Recent 50',
                        'retry': 'Try Again',
                        'support': 'Support'},
 'ranking_alt_text': 'Rating Ranking',
 'ranking_no_data_text': 'No ranking data available.',
 'ranking_title_text': 'Rating Ranking',
 'rate_limit_msg_text': '🔄 The system is currently busy.\nPlease try again in a moment.',
 'rebind_button_text': 'Edit Account',
 'rebind_description_text': 'Update password, server, or Aime for your linked SEGA account.',
 'rebind_group_warning_text': 'rebind is only available in private chat. Message the bot directly.',
 'rebind_msg_text': '✅ SEGA account settings updated.',
 'rebind_not_bound_text': 'No SEGA account is linked yet. Link one with bind first.',
 'rebind_title_alt_text': 'Edit Account Settings',
 'record_error_text': 'No maimai records found yet. Run `maimai update` first, then try again.',
 'search_group_warning_text': 'artist / designer / bpm search is only available in private chat.',
 'sega_bind_alt_text': 'Link SEGA Account',
 'sega_bind_button_text': 'Start Linking',
 'sega_bind_description_text': 'Open the SEGA account binding page for first-time linking.',
 'sega_bind_title_text': 'Link SEGA Account',
 'segaid_error_text': "You haven't linked your SEGA account yet, right?",
 'settings_button_text': 'Open Settings',
 'settings_description_text': 'Change timezone, language, background image, and privacy settings.',
 'settings_group_warning_text': 'settings is only available in private chat. Message the bot '
                                'directly.',
 'settings_title_alt_text': 'Personal Settings',
 'song_error_text': 'No songs matched the criteria.',
 'song_info_alt_text': 'Song Info',
 'song_record_alt_text': 'Song Record',
 'store_error_text': '🥹 No nearby arcades found',
 'system_error_text': '😵 A system error occurred... The administrator has been notified. Please '
                      'try again later.',
 'unbind_button_text': 'Open Unlink Page',
 'unbind_description_text': 'Review and remove your linked SEGA account and saved record data in '
                            'the browser.',
 'unbind_group_warning_text': 'unbind is only available in private chat. Message the bot directly.',
 'unbind_title_alt_text': 'Unlink Account',
 'update_result_flex_text': {'alt_text_error': 'Records Update Failed',
                             'alt_text_success': 'Records Updated',
                             'elapsed_time_label': 'Elapsed Time',
                             'failed': 'Failed',
                             'status_best_records': 'Best Records',
                             'status_label': 'Items Not Updated',
                             'status_recent_records': 'Recent Records',
                             'status_user_info': 'Profile',
                             'summary_section': 'Summary',
                             'title_error': 'Records Update Failed',
                             'title_success': 'Records Updated',
                             'update_time_label': 'Update Time'},
 'user_info_flex_text': {'account_section': 'Account',
                         'alt_text': 'User Information',
                         'copy_id': 'Copy ID',
                         'intl_server': 'International Server',
                         'jp_server': 'Japanese Server',
                         'lang_en': 'English',
                         'lang_ja': 'Japanese',
                         'lang_zh': 'Chinese',
                         'language_label': 'Language',
                         'last_update_label': 'Last Update',
                         'name_label': 'Player Name',
                         'not_bound': 'Not Bound',
                         'password_label': 'Password',
                         'profile_section': 'Player Info',
                         'rating_label': 'Rating',
                         'sega_id_label': 'SEGA ID',
                         'server_label': 'Server',
                         'settings_section': 'Settings',
                         'title': 'User Information',
                         'user_id_label': 'LINE ID'},
 'version_error_text': 'Version not found.',
 'view_info_button_text': 'View Song Info',
 'view_record_button_text': 'View Record'}
# END GENERATED MESSAGE TEXTS

TEXTS["messages"] = MESSAGE_TEXTS

TEXTS["images"] = {
    "score": {
        "analysis_title": "Score analysis",
        "type": "Type",
        "subtitle": "Judgement Details",
        "judgement": "Judgements",
        "loss": "Detailed Judgements",
        "break": "BREAK Details",
        "empty": "No judgement details were recognized.",
        "distribution": 'Judgements & losses',
        "cell_legend": 'Count / total loss / loss per note',
        "verified": 'Verified',
        "check_required": 'Check required',
        "validation_note": 'Some results could not be verified. Review the recognised judgements.',
        "common_total": "COMMON TOTAL",
        "break_total": "BREAK TOTAL",
    },
    "records": {
        "heading": "Play records",
        "tracks": "tracks",
        "play_count": "Plays",
        "avg_level": "AVG LEVEL",
        "avg_achievement": "AVG ACHIEVEMENT",
        "avg_rating": "AVG RATING",
    },
    "progress": {
        "completed": "COMPLETED",
        "incomplete": "INCOMPLETE",
        "unplayed": "UNPLAYED",
        "total": "TOTAL",
        "progress_suffix": "TARGET",
        "level_list_suffix": "LEVEL LIST",
    },
    "song": {
        "note_loss": {'type': 'Type', 'title': 'Judgement losses', 'unit': 'Achievement lost per note', 'count': 'Count', 'tolerance': 'TAP GREAT allowance', 'max_tap': 'Max {count}', 'legend': 'P1/P2: high/low PERFECT · G1/G2/G3: high/middle/low GREAT'},
        "notes_title": "Note distribution",
        "rating_title": "Notes Designer & rating targets",
        "rating_note": "Rating at the minimum achievement for each rank (excluding the AP bonus)",
        "records": "Play records",
        "unplayed": "Not played",
        "artist": "ARTIST", "category": "CATEGORY", "bpm": "BPM", "version": "VERSION",
        "unknown_title": "Unknown title", "unknown_artist": "Unknown artist", "unknown_category": "Unknown category",
        "headers": {
            "chart_type": "Difficulty", "level": "Level", "designer": "Notes Designer",
            "total": "Total", "tap": "TAP", "hold": "HOLD", "slide": "SLIDE",
            "touch": "TOUCH", "break": "BREAK", "jp": "JP", "intl": "INTL", "usa": "USA",
        },
    },
}
