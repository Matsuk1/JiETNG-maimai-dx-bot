"""Simplified Chinese language plugin."""

LANGUAGE = {
    "code": "zh",
    "label": "简体中文",
    "aliases": ("zh-cn", "zh-hans"),
    "fallbacks": ("zh-tw",),
}

TEXTS = {
    "web": {
        "loading": "加载中",
        "notice_html": "<strong>使用须知</strong><br>您输入的所有信息都将以加密形式安全保存，不会提供给第三方。<br><br>但是，本服务由个人运营，不提供官方保证或支持。<br>鉴于本服务的性质，如果您对安全性或运营政策有顾虑，请勿使用。<br>信息提供完全基于您自己的判断和责任。",
        "error": {
            "title": "错误",
            "fallback_message": "处理请求时发生错误。",
        },
        "unbind": {
            "title": "解除账号绑定",
            "lead": "请在此浏览器中确认，将已绑定账号从 JiETNG 移除。",
            "type": "类型",
            "account": "SEGA 账号",
            "server": "服务器",
            "warning": "这会删除已保存的账号凭证、相关设置、成绩和最近成绩。此操作无法撤销。",
            "submit": "确认解绑",
        },
        "success": {
            "titles": {
                "settings": "设置已保存",
                "import_token": "Import Token 已生成",
                "unbind": "已解除绑定",
                "rebind": "更新成功",
                "bind": "绑定成功",
            },
            "descriptions": {
                "settings": "您的设置已成功保存。",
                "import_token": "请把这个 Token 保存到书签工具里。第一次上传成绩后，JiETNG 会初始化你的用户资料。",
                "unbind": "你的已绑定账号和已保存成绩已从 JiETNG 移除。",
                "rebind": "您的账号设置已成功更新。",
                "bind": "已成功与 JiETNG 连携。",
            },
            "token": {
                "shown_once": "Token 只显示这一次",
                "copy": "复制 Token",
                "copied": "已复制",
            },
        },
    }
}

# BEGIN MESSAGE MANAGER TEXTS
TEXTS["message_manager"] = {'help_ui': {'b_subtitle': 'Best / All Best / 特殊成绩图与筛选参数',
             'b_title': 'B 系列成绩图',
             'catalog_subtitle': '发送 命令-help 查看单项说明',
             'catalog_title': '命令目录',
             'categories': '分类',
             'command': '命令',
             'default_purpose': '查看该命令的说明。',
             'detail_hint': '详细说明',
             'docs_button': '帮助文档',
             'examples': '示例',
             'function': '说明',
             'help_title': '命令帮助',
             'modes': '可用模式',
             'none': '无',
             'notes': '注意',
             'params': '参数',
             'usage': '用法'},
 'score_recognition': {'break_detail': 'BREAK 详细判定',
                       'break_detail_source_multiple': 'Calc 推算：从 {count} 个候选中选择最可能组合',
                       'break_detail_source_single': 'Calc 推算：唯一匹配组合',
                       'break_row_source_multiple': 'BREAK 整行有 {count} 个 Calc 候选；上方为当前候选的细分',
                       'breakdown': '判定数据',
                       'calc_corrected': 'Calc 已自动配平',
                       'calc_incomplete': 'Calc 达成率一致，但判定明细不完整；-? 表示缺失项',
                       'calc_inferred': 'BREAK 未识别，已根据物量和 Calc 推算',
                       'calc_mismatch': 'Calc 检测到不一致，但无法定位到单个识别项',
                       'calc_uncertain': 'Calc 检测到不一致，? 表示疑似识别项',
                       'calc_validated': 'Calc 已确认达成率与判定数据一致',
                       'compact_fix': '修正 BREAK',
                       'constant': '定数',
                       'copy_fix': '复制修正命令',
                       'empty': '未能识别判定明细。',
                       'loss_detail': '详细判定',
                       'manual_fix': '手动修正',
                       'manual_fix_hint': '复制命令，修改达成率或错误数字后发送。五行依次为 TAP、HOLD、SLIDE、TOUCH、BREAK；全 0 '
                                          '行是缺失占位，发送前必须填写。',
                       'status': '状态',
                       'title': '判定明细',
                       'validated': 'MISS 已根据谱面物量校验'},
 'service_status': {'queue': '队列状态',
                    'songs': '歌曲数据',
                    'summary': '概要',
                    'tasks_today': '今日任务',
                    'title': 'JiETNG 运行状态',
                    'uptime': '运行时长'}}
# END MESSAGE MANAGER TEXTS

# BEGIN HELP DETAILS
TEXTS["message_manager"]["help_details"] = {'ab50_allb50_ab35_allb35': 'ab50 / allb50, ab35 / allb35',
 'account_and_system': '账号与系统',
 'achievement_one_value_is_a_lower_bound_two_values_are_a_range': '达成率。1 个值为下限，2 个值为范围。',
 'ap50_fdx50_r50_rct50_idlb50_s50_sun50': 'ap50, fdx50, r50 / rct50, idlb50, s50 / sun50',
 'b50_best50_b40_best40_b35_best35_b15_best15': 'b50 / best50, b40 / best40, b35 / best35, b15 / '
                                                'best15',
 'best_all_best_recent_and_special_score_images': 'Best、All Best、Recent 与特殊成绩图。',
 'binding_settings_profile_sync_export_and_status': '绑定、设置、资料、同步、导出与状态。',
 'chart_rating_one_value_is_exact_two_values_are_a_range': '单谱 Rating。1 个值精确匹配，2 个值范围。',
 'chart_type_supports_dx_and_std_multiple_values_are_allowed': '谱面类型。支持 dx、std，可多个。',
 'commands_that_need_arguments_also_show_help_when_sent_without_ar': '需要参数的命令只发送命令名时，也会显示对应说明。',
 'data_required': '数据要求',
 'difficulty_supports_bas_adv_exp_mas_rem_or_full_names_multiple_v': '难度。支持 bas、adv、exp、mas、rem '
                                                                     '或完整名，可多个。',
 'display_multiplier_capped_at_2_5': '扩大输出数量倍率，最大 2.5。',
 'dx_stars_one_value_is_exact_two_values_are_a_range': 'DX 星数。1 个值精确匹配，2 个值范围。',
 'friend_list_and_friend_record_lookup': '好友列表和好友成绩查询。',
 'generate_best_all_best_special_score_images_with_optional_filter': '生成 Best / All Best / '
                                                                     '特殊成绩图，可追加筛选参数。',
 'level_lists_constant_lists_plate_completion_and_target_progress': '等级列表、定数列表、牌子完成度和目标达成。',
 'level_or_constant_one_value_is_exact_two_values_are_a_range': '等级或定数。1 个值精确匹配，2 个值范围。',
 'line_mentions_can_query_registered_users_self_only_commands_do_n': '支持 LINE mention '
                                                                     '查询已注册用户；仅限本人命令不会接受 mention。',
 'lists_and_progress': '列表与目标',
 'missing_arguments': '参数缺失',
 'next_version_preview_using_the_next_rating_structure': '下版本预览。按下一版本 Rating 结构预览成绩图。',
 'page_number_starting_from_1': '页码，从 1 开始。',
 'querying_others': '查询他人',
 'ranking_rating_breakdown_note_scoring_and_utility_commands': '排行榜、Rating 内訳、分值计算和辅助命令。',
 'requires_a_linked_account_with_maimai_update_completed_or_data_i': '需要已绑定账号并完成 maimai update，或已有 '
                                                                     'Import Token / 开发者 API '
                                                                     '导入的数据。',
 'score_images': '成绩图',
 'search': '搜索',
 'search_by_artist_designer_bpm_or_random_conditions': '按艺术家、谱师、BPM 或条件随机选曲。',
 'send_b50_help_artist_help_bpm_help_and_similar_forms_for_full_us': '发送 '
                                                                     'b50-help、artist-help、bpm-help '
                                                                     '这类格式查看完整用法。',
 'single_command': '单项说明',
 'social': '社交',
 'song_details_score_image_recognition_single_song_records_and_son': '查歌曲信息、识别成绩图、单曲成绩和歌曲 ID。',
 'songs_and_records': '歌曲与成绩',
 'tools': '工具',
 'version_names_multiple_values_are_allowed_is_treated_as_plus_and': '版本名，可多个。+ 会识别为 PLUS，dx / '
                                                                     'deluxe 会归一。',
 'without_values_sort_by_dx_score_with_values_filter_dx_score_perc': '无参数时按 DX 分排序；带值时筛 DX Score '
                                                                     '百分比。'}
# END HELP DETAILS

TEXTS["message_manager"].update({
    "button_labels": {"uri": "查看详情", "message": "尝试一下"},
    "vote_labels": {"support": "支持", "oppose": "反对"},
    "search_titles": {
        "song": "歌曲搜索结果 ({count}条)",
        "record": "成绩搜索结果 ({count}条)",
    },
    "rating_chart_title": "定数 {level} Rating 对照表",
    "song_unit": "首",
})

# BEGIN MAIN TEXTS
TEXTS["main"] = {'account_already_bound': '已绑定 SEGA 账号。如需重新绑定，请先使用 unbind 命令解除绑定。',
 'account_not_linked': '未绑定账号。',
 'already_linked_title': '已绑定',
 'candidates_failed': '获取账号列表失败。请稍后再试。',
 'constant_out_of_range': '定数 {level} 超出范围。请输入 1.0~15.0 范围内的数值。',
 'constant_precision': '定数 {level} 无效。仅支持一位小数（例如：13.2）。',
 'correction_format_body': '请使用 7 行格式：fix-rcd 曲名、达成率，随后依次填写 TAP、HOLD、SLIDE、TOUCH、BREAK；每行格式为 '
                           'CP/PF/GR/GD/MS。',
 'correction_format_title': '修正格式错误',
 'fields_required': '请填写所有字段。',
 'invalid_constant': '无效的定数。请输入 1.0~15.0 范围内的数值。',
 'invalid_credentials': 'SEGA ID 或密码不正确。请检查后重试。',
 'maintenance': '官方网站正在维护中。请稍后再试。',
 'no_linked_account': '当前没有已绑定账号。',
 'not_linked_title': '未绑定',
 'private_chat_title': '请在私聊使用',
 'recognition_failed_body': '无法读取这张成绩图，请确认图片完整后重试。',
 'recognition_failed_title': '识别失败',
 'score_image_required_body': '请回复一张成绩图并发送 {command_text}。',
 'score_image_required_title': '缺少成绩图',
 'sega_id_immutable': '无法更改 SEGA ID。',
 'token_invalid': '令牌无效。',
 'token_missing': '未提供令牌。',
 'unbind_token_invalid': '令牌无效或已过期。请重新发送 unbind。',
 'vote_success': '感谢您的投票！\n'
                 '\n'
                 '支持: {support_count}人 ({support_percent:.1f}%)\n'
                 '反对: {oppose_count}人 ({oppose_percent:.1f}%)'}
# END MAIN TEXTS

# BEGIN COMMAND HELP
TEXTS["command_help"] = {'bind': '命令: bind\n'
         '说明: 返回一次性 SEGA 账号绑定链接，用于首次绑定账号。\n'
         '参数: 无需参数: 直接发送 bind。\n'
         '限制: 只能在私聊使用，群聊会返回安全提示。\n'
         '示例: bind',
 'calc_notes': '命令: calc <tap> <hold> <slide> [touch] <break>\n'
               '说明: 根据谱面物量计算单个 Note 分值。\n'
               '参数: 必填: <tap> <hold> <slide> <break>，当只给 4 个数字时按 TAP/HOLD/SLIDE/BREAK 解析。\n'
               '可选: [touch]，当给 5 个数字时第 4 个为 TOUCH，第 5 个为 BREAK。\n'
               '格式: 所有参数必须是非负整数，用空格分隔。\n'
               '示例: calc 500 50 80 30\n'
               'calc 500 50 80 20 30',
 'export': '命令: export <json|xml>\n'
           '说明: 将自己的成绩数据导出为指定格式。\n'
           '参数: 必填: <格式>，只能填写 json 或 xml。\n'
           '输出: 成功后返回临时下载链接和复制链接按钮。\n'
           '要求: 需要已有成绩数据；如果没有数据会返回空数据提示。\n'
           '示例: export json',
 'friend_list': '命令: friends\n'
                '说明: 查看已添加的好友列表。\n'
                '参数: 无需参数: 直接发送命令，会从 maimai NET 读取好友列表。\n'
                '相关: 好友成绩图可通过 friend-rcd <好友编号或名称> [成绩图类型] [筛选参数] 使用。\n'
                '示例: friends',
 'level_rank_list': '命令: <等级或定数> levels\n'
                    '说明: 查看指定等级或定数相关歌曲列表。\n'
                    '参数: 必填: <等级或定数>，支持 13、13+、14、13.6 等格式。\n'
                    '匹配: 整数/带 + 按等级匹配，小数按定数精确匹配。\n'
                    '示例: 13.6 levels\n'
                    '14+ levels',
 'level_rank_progress': '命令: <等级或分类><评价> prog [-uc|-up|-c]\n'
                        '说明: 查看指定等级或分类中评价目标的达成情况。\n'
                        '参数: 必填: <等级或分类>，等级支持 11-15；分类支持 '
                        'vocaloid、touhou、popani、gekichu、game、maimai。\n'
                        '必填: <评价>，紧跟等级/分类书写，支持 s、s+、ss、ss+、sss、sss+、fc、fc+、ap、ap+、fdx、fdx+。\n'
                        '可选: -uc 仅看未完成目标，-up 仅看未游玩，-c 仅看已完成目标。\n'
                        '格式: 等级可直接连写，例如 14sss+ prog；分类建议和评价之间加空格，例如 vocaloid sss+ prog。\n'
                        '示例: 14sss+ prog\n'
                        '13ap prog -uc\n'
                        'vocaloid sss+ prog\n'
                        'popani ss+ prog -up',
 'level_records': '命令: <等级或定数> records [页码]\n'
                  '说明: 查看指定等级或定数的成绩列表。\n'
                  '参数: 必填: <等级或定数>，支持 13、13+、14、13.6 等格式。\n'
                  '可选: [页码]，正整数，从 1 开始；省略时显示第 1 页。\n'
                  '匹配: 整数/带 + 按等级匹配，小数按定数精确匹配。\n'
                  '示例: 13.6 records\n'
                  '14 records 2',
 'maimai_update': '命令: maimai update\n'
                  '说明: 从 maimai NET 获取并更新已游玩的歌曲成绩数据。\n'
                  '参数: 无需参数: 直接发送命令即可开始同步。\n'
                  '示例: maimai update\n'
                  '注意: 需要先绑定 SEGA 账号。',
 'plate': '命令: <牌子名> plate [-uc|-up|-c]\n'
          '说明: 查看版本牌子或称号类目标的完成情况。\n'
          '参数: 必填: <牌子名>，写在 plate 前面，例如 真極、檄将 等。\n'
          '可选: -uc 仅看未完成项目，-up 仅看未游玩项目，-c 仅看已完成项目。\n'
          '格式: 过滤项写在命令最后；不写过滤项时显示完整完成度。\n'
          '示例: 真極 plate\n'
          '真極 plate -uc',
 'profile': '命令: profile\n'
            '说明: 查看自己的 JiETNG 账号信息，包括绑定状态、服务器和语言设置。\n'
            '参数: 无需参数: 直接发送 profile。\n'
            '限制: 只能在私聊使用，避免公开个人信息。\n'
            '示例: profile',
 'random_song': '命令: random [条件]\n'
                '说明: 随机推荐一首歌曲。\n'
                '参数: 可选: [条件]，可写等级、定数、谱面类型、难度等关键词。\n'
                '格式: 多个条件用空格分隔；省略条件时从全部歌曲中随机。\n'
                '示例: random\n'
                'random 13+ dx\n'
                'random 14 mas',
 'ranking': '命令: rank [jp|intl]\n'
            '说明: 查看 DX Rating 总体排行榜。\n'
            '参数: 可选: [服务器]，支持 jp、intl；省略时使用当前用户绑定的服务器。\n'
            '格式: 服务器参数写在 rank 后面，用空格分隔。\n'
            'Mention: 可 @ 已注册用户，查看对方在总体榜中的位置；需对方允许 @ 查询成绩。\n'
            '示例: rank\n'
            'rank intl',
 'rc': '命令: rc <定数>\n'
       '说明: 查询 Rating Composition / レート内訳相关信息。\n'
       '参数: 必填: <定数>，支持 1.0 到 15.0 之间的数字。\n'
       '格式: 可写整数或小数，例如 13、13.6、14.9。\n'
       '限制: 超出 1.0-15.0 或无法转成数字会返回输入错误。\n'
       '示例: rc 14\n'
       'rc 13.6',
 'rebind': '命令: rebind\n'
           '说明: 返回 SEGA 账号编辑链接，用于更新已绑定账号的信息。\n'
           '参数: 无需参数: 直接发送 rebind。\n'
           '要求: 必须已经绑定 SEGA 账号。\n'
           '限制: 只能在私聊使用。\n'
           '示例: rebind',
 'refreshmenu': '命令: refreshmenu\n'
                '说明: 根据当前绑定状态重新关联发送者自己的 LINE Rich Menu。\n'
                '参数: 无需参数: 直接发送 refreshmenu。\n'
                '限制: 仅影响发送者自己的 Rich Menu。\n'
                '示例: refreshmenu',
 'score_recognition': '命令: rec\n'
                      '说明: 识别完整成绩；能完全校验时返回成绩图片，需要修正时返回可复制的修正卡片。\n'
                      '参数: 必须回复一张成绩图，不接受其他参数。\n'
                      '示例: rec',
 'search_by_artist': '命令: artist <关键词> [页码]\n'
                     '说明: 按艺术家名搜索歌曲。\n'
                     '参数: 必填: <关键词>，artist 后面的文本会作为艺术家名进行不区分大小写的包含匹配。\n'
                     '可选: [页码]，正整数，从 1 开始；写在关键词最后。\n'
                     '限制: 仅限私聊使用，避免群聊刷屏。\n'
                     '示例: artist Nanahira\n'
                     'artist sasakure 2',
 'search_by_bpm': '命令: bpm <BPM或范围> [页码]\n'
                  '说明: 按 BPM 精确值或范围搜索歌曲。\n'
                  '参数: 必填: <BPM或范围>，支持单值、连字符范围、空格范围。\n'
                  '单值: bpm 180 表示精确匹配 BPM 180。\n'
                  '范围: bpm 0-120 或 bpm 120 180 表示闭区间，端点可为 0。\n'
                  '可选: [页码]，正整数，从 1 开始；写在最后。\n'
                  '限制: 仅限私聊使用。\n'
                  '示例: bpm 180\n'
                  'bpm 0-120\n'
                  'bpm 120 180 2',
 'search_by_designer': '命令: designer <关键词> [页码]\n'
                       '说明: 按谱面设计师名搜索歌曲。\n'
                       '参数: 必填: <关键词>，designer 后面的文本会匹配各难度谱面的 noteDesigner 字段。\n'
                       '可选: [页码]，正整数，从 1 开始；写在关键词最后。\n'
                       '限制: 仅限私聊使用，避免群聊刷屏。\n'
                       '示例: designer Jack\n'
                       'designer 譜面 2',
 'settings': '命令: settings\n'
             '说明: 返回个人设置页面链接，用于修改时区、语言、背景图片、隐私等选项。\n'
             '参数: 无需参数: 直接发送 settings。\n'
             '限制: 只能在私聊使用。\n'
             '示例: settings',
 'song_info': '命令: <曲名> info\n'
              '说明: 查询歌曲基本信息、谱面信息和 BPM；也可以回复成绩图片直接发送 info，自动识别曲名。\n'
              '参数: 文本查询时填写 <曲名>，可以是完整曲名、部分曲名或别名；图片查询时无需填写曲名。\n'
              '匹配: 如果匹配到多首歌，会返回可选择的候选结果。\n'
              '示例: ヒバナ info\n'
              '（回复图片）info',
 'song_record': '命令: <曲名> record\n'
                '说明: 按曲名或别名查询自己的单曲成绩。\n'
                '参数: 必填: <曲名>，写在 record 前面，可以是完整曲名、部分曲名或别名。\n'
                '匹配: 如果匹配到多首歌，会返回可选择的候选结果。\n'
                '示例: ヒバナ record',
 'status': '命令: status\n说明: 查看机器人服务状态，包括运行时间、任务队列和系统资源。\n参数: 无需参数: 直接发送 status。\n示例: status',
 'unbind_prompt': '命令: unbind\n'
                  '说明: 返回一次性 SEGA 账号解绑链接，在浏览器内确认后才会删除账号数据。\n'
                  '参数: 无需参数: 直接发送 unbind。\n'
                  '要求: 必须已经绑定 SEGA 账号或已启用 Import Token 账号。\n'
                  '限制: 只能在私聊使用。\n'
                  '示例: unbind',
 'version_songs': '命令: <版本名> ver\n'
                  '说明: 查看指定版本歌曲列表。\n'
                  '参数: 必填: <版本名>，写在 ver 前面，支持版本完整名或可识别简称。\n'
                  '格式: 版本名可包含空格；整段 ver 前的文本都会作为版本查询词。\n'
                  '示例: BUDDiES ver\n'
                  'PRiSM PLUS ver'}
# END COMMAND HELP

# BEGIN TEMPLATE TEXTS
TEXTS["web"]["bind"] = {
    "pageTitle": "SEGA 账号绑定 | JiETNG",
    "pageTitleRebind": "编辑账号设置 | JiETNG",
    "heading": "SEGA 账号绑定",
    "headingRebind": "编辑账号设置",
    "labelSegaid": "SEGA ID",
    "labelPassword": "SEGA 密码",
    "labelVersion": "版本",
    "optJp": "日本版",
    "optIntl": "国际版",
    "labelTimezone": "时区",
    "labelLanguage": "语言",
    "languagePlatformHint": "语言设置可能不会作用于 LINE 以外的第三方平台。",
    "labelBindType": "绑定方式",
    "optBindSega": "SEGA 账号",
    "optBindImport": "仅使用 Import Token",
    "bindTypeImportHelp": "不保存 SEGA 账号密码，之后通过导出工具上传成绩。",
    "submitBtn": "绑定",
    "submitBtnImport": "生成 Token",
    "submitBtnRebind": "更新",
    "noticeTitle": "使用须知",
    "aimeModalTitle": "选择 Aime",
    "aimeModalDescription": "请选择要绑定的账号。",
    "aimeConfirm": "确定",
    "aimeFallbackName": "Aime 账号",
    "ratingLabel": "Rating",
    "trophyLabel": "称号",
    "accountListError": "无法获取账号列表。"
}
TEXTS["web"]["bind_notice_html"] = "您输入的所有信息都将以加密形式安全保存，不会提供给第三方。<br><br>但是，本服务由个人运营，不提供官方保证或支持。鉴于本服务的性质，如果您对安全性或运营政策有顾虑，请勿使用。信息提供完全基于您自己的判断和责任。"
TEXTS["web"]["settings"] = {
    "pageTitle": "设置 | JiETNG",
    "heading": "设置",
    "labelLanguage": "语言",
    "languagePlatformHint": "语言设置可能不会作用于 LINE 以外的第三方平台。",
    "labelTimezone": "时区",
    "skinSection": "皮肤与背景",
    "labelSkin": "皮肤",
    "skinUsesBackground": "使用背景图",
    "skinNoBackground": "不使用背景图",
    "skinBackgroundHint": "使用下方选择的背景图、模糊和遮罩设置；关闭背景图时使用默认底色。",
    "skinNoBackgroundHint": "此皮肤不使用背景图。已有背景设置会保留，切换回来后仍可使用。",
    "labelBgEnabled": "背景图片",
    "privacyPanelTitle": "隐私设置",
    "rankingPanelTitle": "排行榜设置",
    "labelMentionScoreQuery": "允许他人 @ 我查询成绩",
    "metaMentionScoreQuery": "开启后，其他用户可以通过 LINE mention 查看你的成绩图和成绩进度。",
    "labelGlobalRanking": "参与总体排行榜",
    "metaGlobalRanking": "会显示在 rank / ranking 的总体榜中。",
    "labelBgBlur": "背景模糊",
    "labelBgOverlay": "背景淡化",
    "bgHint": "不选择则从所有背景中随机。",
    "sectionCustomBg": "自定义背景",
    "customBgHint": "上传你自己的背景图片（限2张，每张5MB以内）。",
    "labelCustomBg": "选择图片",
    "uploadSub": "PNG / JPG / JPEG / WebP（5MB以内）",
    "uploadBtn": "上传",
    "uploadFailed": "上传失败。",
    "deleteCustomBgBtn": "删除",
    "deleteCustomBgConfirm": "确定删除自定义背景吗？",
    "deleteAllCustomBgBtn": "全部删除",
    "deleteAllCustomBgConfirm": "确定删除全部自定义背景吗？",
    "submitBtn": "保存",
    "importTokenTitle": "成绩导入 Token",
    "importTokenHelp": "用于让外部工具把加工后的成绩 JSON 上传到 JiETNG。",
    "importTokenCreate": "生成 Token",
    "importTokenNoteLabel": "Token 名称",
    "importTokenNotePlaceholder": "例如：工具",
    "importTokenNoteRequired": "请输入 Token 名称。",
    "importTokenResultTitle": "Token（只显示这一次）",
    "importTokenCopy": "复制",
    "importTokenCopied": "已复制",
    "importTokenEmpty": "还没有 Token。",
    "importTokenRevoke": "撤销",
    "importTokenRevoked": "已撤销",
    "importTokenDelete": "删除",
    "importTokenCreateError": "生成 Token 失败。",
    "importTokenRevokeConfirm": "确定撤销这个导入 Token 吗？",
    "importTokenRevokeError": "撤销失败。",
    "importTokenDeleteConfirm": "确定删除这个已撤销的导入 Token 吗？",
    "importTokenDeleteError": "删除失败。"
}
TEXTS["web"]["settings_permissions"] = {
    "panelTitle": "访问权限管理",
    "ownerLabel": "创建者",
    "revokeBtn": "撤销",
    "revokeConfirm": "确定撤销该服务的访问权限吗？",
    "revokeError": "撤销失败，请重试"
}
# END TEMPLATE TEXTS

# BEGIN GENERATED MESSAGE TEXTS
MESSAGE_TEXTS = {'access_error_text': '🙇 现在访问量很大…请稍后再试！',
 'already_bound_text': '当前已经绑定 SEGA 账号。\n'
                       '\n'
                       '修改密码、服务器版本或 Aime 请使用 rebind。\n'
                       '修改时区、语言、背景图片、隐私等个人设置请使用 settings。\n'
                       '如需绑定其他账号，请先使用 unbind 解除当前绑定。',
 'bind_group_warning_text': 'bind 只能在私聊使用。请直接向机器人发送消息。',
 'calc_button_text': 'Note 计算',
 'calc_flex_text': {'alt_multi': 'Note 计算结果',
                    'alt_single': 'Note 计算结果',
                    'max_tap_great': '最多 {count} 个 TAP GREAT',
                    'subtitle': 'Note 计算',
                    'title_distribution': 'Note 分布'},
 'cannot_do_for_others_text': '该命令只能用于你自己的账号。',
 'dxdata_current_stats_text': '📈 当前: {songs}首歌曲 / {sheets}个谱面',
 'dxdata_fetch_failed_text': '❌ 数据获取失败！',
 'dxdata_first_update_text': '(首次更新完成！)',
 'dxdata_initial_stats_sheets_text': '📊 谱面: {count}个',
 'dxdata_initial_stats_songs_text': '📈 歌曲: {count}首',
 'dxdata_last_update_text': '📅 上次更新: {timestamp}',
 'dxdata_new_sheets_text': '📊 新增谱面: +{count}个',
 'dxdata_new_songs_text': '🎵 新增歌曲: +{count}首',
 'dxdata_no_new_sheets_text': '📊 新增谱面: 无',
 'dxdata_no_new_songs_text': '🎵 新增歌曲: 无',
 'dxdata_parse_failed_text': '❌ 数据解析失败！',
 'dxdata_sheets_decreased_text': '📊 谱面: {count}个',
 'dxdata_songs_decreased_text': '🎵 歌曲: {count}首',
 'dxdata_update_success_text': '✅ Dxdata 更新成功！',
 'export_alt_text': '成绩数据已导出',
 'export_empty_text': '还没有可导出的成绩数据。请先使用『maimai update』更新后再试。',
 'export_failed_text': '成绩数据导出失败，请稍后再试。',
 'export_flex_button_text': '下载',
 'export_flex_copy_button_text': '复制链接',
 'export_flex_footnote_text': '下载链接将在 {ttl} 分钟后失效',
 'export_flex_summary_text': 'Best: {best} 条  ·  Recent: {recent} 条\n格式: {fmt}（{size_kb} KB）',
 'export_flex_title_text': '成绩数据已导出',
 'friend_error_text': '还没有收藏的好友。',
 'friend_list_alt_text': '收藏的好友',
 'friend_rcd_error_text': '指定用户不在你的好友列表中。',
 'friend_rcd_group_warning_text': '好友成绩命令只能在私聊使用。请直接向机器人发送消息。',
 'friend_rcd_text': '{name} 的数据',
 'info_error_text': '你的 maimai 玩家资料尚未保存。请先使用『maimai update』更新后再试。',
 'input_error_text': '无法识别该命令，请检查输入内容。',
 'level_not_supported_text': '不支持该等级的定数表。\n仅支持12级及以上。',
 'level_record_not_found_text': '指定等级「{level}」的第 {page} 页记录可能不存在...',
 'level_record_page_hint_text': '这是第 {page} 页的数据！',
 'maintenance_error_text': '🔧 咦？官方网站好像在维护中！\n维护时间无法访问，请稍后再试~',
 'mention_error_text': '被提到的用户尚未注册 JiETNG。',
 'mention_not_allowed_text': '被提到的用户已关闭 @ 查询成绩。',
 'mention_no_matching_data_text': '被提到的用户没有符合条件的成绩数据。',
 'mention_record_error_text': '被提到的用户还没有 maimai 成绩数据。',
 'nearby_stores_alt_text': '附近的 maimai 机厅',
 'no_matching_data_text': '没有找到符合条件的成绩数据。',
 'notice_header_text': '📢 公告',
 'perm_request_accept_button_text': '接受',
 'perm_request_accept_success_text': '✅ 已接受访问权限请求！\n'
                                     '\n'
                                     'Token ID: {token_id}\n'
                                     '申请者: {requester_name}\n'
                                     '\n'
                                     '该 token 现在可以访问你的账户信息了。',
 'perm_request_already_processed_text': '该请求已经处理过了。',
 'perm_request_notification_alt_text': '你有 {count} 个访问权限请求',
 'perm_request_notification_subtitle_text': '{count} 个新请求',
 'perm_request_notification_title_text': '访问权限请求',
 'perm_request_reject_button_text': '拒绝',
 'perm_request_reject_success_text': '✅ 已拒绝访问权限请求。\n\nToken ID: {token_id}\n申请者: {requester_name}',
 'plate_error_text': '没有找到指定的牌子。',
 'private_info_group_warning_text': '个人信息命令只能在私聊使用。请直接向机器人发送消息。',
 'quick_reply_labels': {'account_bind': '绑定账号',
                        'all_best_50': 'All Best 50',
                        'maimai_update': '更新数据',
                        'recent_50': 'Recent 50',
                        'retry': '再试一次',
                        'support': '帮助'},
 'ranking_alt_text': 'Rating 排行榜',
 'ranking_no_data_text': '暂无排行榜数据。',
 'ranking_title_text': 'Rating 排行榜',
 'rate_limit_msg_text': '🔄 系统当前较为繁忙，请稍后再试。',
 'rebind_button_text': '编辑账号',
 'rebind_description_text': '修改已绑定 SEGA 账号的密码、服务器版本或 Aime。',
 'rebind_group_warning_text': 'rebind 只能在私聊使用。请直接向机器人发送消息。',
 'rebind_msg_text': '✅ SEGA 账号信息已更新。',
 'rebind_not_bound_text': '尚未绑定 SEGA 账号。请先使用 bind 完成绑定。',
 'rebind_title_alt_text': '编辑账号设置',
 'record_error_text': '还没有 maimai 成绩数据。请先使用『maimai update』更新后再试。',
 'search_group_warning_text': 'artist / designer / bpm 搜索只能在私聊使用。',
 'sega_bind_alt_text': '绑定 SEGA 账号',
 'sega_bind_button_text': '开始绑定',
 'sega_bind_description_text': '打开首次绑定用的 SEGA 账号绑定页面。',
 'sega_bind_title_text': '绑定 SEGA 账号',
 'segaid_error_text': '你还没有绑定 SEGA 账号吧？',
 'settings_button_text': '打开设置',
 'settings_description_text': '修改时区、语言、背景图片和隐私设置。',
 'settings_group_warning_text': 'settings 只能在私聊使用。请直接向机器人发送消息。',
 'settings_title_alt_text': '个人设置',
 'song_error_text': '没有找到符合条件的歌曲。',
 'song_info_alt_text': '歌曲信息',
 'song_record_alt_text': '歌曲成绩',
 'store_error_text': '🥹 附近没有找到游戏厅',
 'system_error_text': '😵 发生系统错误…已通知管理员。请稍后再试。',
 'unbind_button_text': '打开解绑页面',
 'unbind_description_text': '在浏览器内确认并删除已绑定 SEGA 账号和已保存成绩数据。',
 'unbind_group_warning_text': 'unbind 只能在私聊使用。请直接向机器人发送消息。',
 'unbind_title_alt_text': '解除账号绑定',
 'update_result_flex_text': {'alt_text_error': '成绩更新失败',
                             'alt_text_success': '成绩更新完成',
                             'elapsed_time_label': '耗时',
                             'failed': '失败',
                             'status_best_records': 'Best 成绩',
                             'status_label': '未更新项目',
                             'status_recent_records': 'Recent 成绩',
                             'status_user_info': '玩家资料',
                             'summary_section': '概要',
                             'title_error': '成绩更新失败',
                             'title_success': '成绩更新完成',
                             'update_time_label': '更新时间'},
 'user_info_flex_text': {'account_section': '账号',
                         'alt_text': '用户信息',
                         'copy_id': '复制ID',
                         'intl_server': '国际服',
                         'jp_server': '日服',
                         'lang_en': '英语',
                         'lang_ja': '日语',
                         'lang_zh': '中文',
                         'language_label': '语言',
                         'last_update_label': '最后更新',
                         'name_label': '玩家名称',
                         'not_bound': '未绑定',
                         'password_label': '密码',
                         'profile_section': '玩家信息',
                         'rating_label': 'Rating',
                         'sega_id_label': 'SEGA ID',
                         'server_label': '服务器',
                         'settings_section': '设置',
                         'title': '用户信息',
                         'user_id_label': 'LINE ID'},
 'version_error_text': '没有找到指定的版本。',
 'view_info_button_text': '查看歌曲信息',
 'view_record_button_text': '查看成绩'}
# END GENERATED MESSAGE TEXTS

TEXTS["messages"] = MESSAGE_TEXTS

TEXTS["images"] = {
    "score": {
        "subtitle": "判定详情",
        "judgement": "判定数据",
        "loss": "详细判定",
        "break": "BREAK 详细判定",
        "empty": "未能识别判定详情。",
        "distribution": '判定分布与失分',
        "cell_legend": '数量 / 合计扣分 / 单个扣分',
        "verified": '已校验',
        "check_required": '待确认',
        "validation_note": '部分结果尚未通过校验，请检查识别判定。',
        "common_total": "普通音符合计",
        "break_total": "BREAK 合计",
    },
    "records": {
        "avg_level": "平均等级",
        "avg_achievement": "平均达成率",
        "avg_rating": "平均 Rating",
    },
    "progress": {
        "completed": "已完成",
        "incomplete": "未完成",
        "unplayed": "未游玩",
        "total": "总计",
        "progress_suffix": "目标",
        "level_list_suffix": "等级列表",
    },
    "song": {
        "artist": "艺术家", "category": "分类", "bpm": "BPM", "version": "版本",
        "unknown_title": "未知曲名", "unknown_artist": "未知艺术家", "unknown_category": "未知分类",
        "headers": {
            "chart_type": "谱面难度", "level": "等级", "designer": "谱师",
            "total": "合计", "tap": "TAP", "hold": "HOLD", "slide": "SLIDE",
            "touch": "TOUCH", "break": "BREAK", "jp": "日服", "intl": "国际服", "usa": "美国",
        },
    },
}
