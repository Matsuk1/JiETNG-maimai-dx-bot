"""Traditional Chinese language plugin."""

from languages.traditional import to_traditional


LANGUAGE = {
    "code": "zh-tw",
    "label": "繁體中文",
    "aliases": ("zh-hant", "zh-hk", "zh-mo"),
    "fallbacks": ("zh",),
    "transforms": {"zh": to_traditional, "*": to_traditional},
}

TEXTS = {
    "web": {
        "loading": "載入中",
        "notice_html": "<strong>使用須知</strong><br>您輸入的所有資訊都會以加密形式安全保存，不會提供給第三方。<br><br>不過，本服務由個人營運，不提供官方保證或支援。<br>基於本服務的性質，如果您對安全性或營運方針有疑慮，請勿使用。<br>資訊提供完全基於您自己的判斷與責任。",
        "error": {
            "title": "錯誤",
            "fallback_message": "處理請求時發生錯誤。",
        },
        "unbind": {
            "title": "解除帳號綁定",
            "lead": "請在此瀏覽器中確認，將已綁定帳號從 JiETNG 移除。",
            "type": "類型",
            "account": "SEGA 帳號",
            "server": "伺服器",
            "warning": "這會刪除已保存的帳號憑證、相關設定、成績與最近成績。此操作無法復原。",
            "submit": "解除綁定",
        },
        "success": {
            "titles": {
                "settings": "設定已保存",
                "import_token": "Import Token 已產生",
                "unbind": "已解除綁定",
                "rebind": "更新成功",
                "bind": "綁定成功",
            },
            "descriptions": {
                "settings": "您的設定已成功保存。",
                "import_token": "請將此 Token 儲存至書籤工具中。首次上傳成績後，JiETNG 會初始化您的使用者資料。",
                "unbind": "您的已綁定帳號與已保存成績已從 JiETNG 移除。",
                "rebind": "您的帳號設定已成功更新。",
                "bind": "已成功與 JiETNG 連結。",
            },
            "token": {
                "shown_once": "Token 僅顯示這一次",
                "copy": "複製 Token",
                "copied": "已複製",
            },
        },
    }
}

# BEGIN MESSAGE MANAGER TEXTS
TEXTS["message_manager"] = {'help_ui': {'b_subtitle': 'Best / All Best / 特殊成績圖與篩選參數',
             'b_title': 'B 系列成績圖',
             'catalog_subtitle': '發送 命令-help 查看單項說明',
             'catalog_title': '命令目錄',
             'categories': '分類',
             'command': '命令',
             'default_purpose': '查看該命令的說明。',
             'detail_hint': '詳細說明',
             'docs_button': '說明文件',
             'examples': '示例',
             'function': '說明',
             'help_title': '命令幫助',
             'modes': '可用模式',
             'none': '無',
             'notes': '註意',
             'params': '參數',
             'usage': '用法'},
 'score_recognition': {'break_detail': 'BREAK 詳細判定',
                       'break_detail_source_multiple': 'Calc 推算：從 {count} 個候選中選擇最可能組合',
                       'break_detail_source_single': 'Calc 推算：唯一匹配組合',
                       'break_row_source_multiple': 'BREAK 整行有 {count} 個 Calc 候選；上方為目前候選的細分',
                       'breakdown': '判定資料',
                       'calc_corrected': 'Calc 已自動配平',
                       'calc_incomplete': 'Calc 達成率一致，但判定明細不完整；-? 表示缺失項',
                       'calc_inferred': 'BREAK 未識別，已根據物量和 Calc 推算',
                       'calc_mismatch': 'Calc 檢測到不一致，但無法定位到單個識別項',
                       'calc_uncertain': 'Calc 檢測到不一致，? 表示疑似識別項',
                       'calc_validated': 'Calc 已確認達成率與判定資料一致',
                       'compact_fix': '修正 BREAK',
                       'constant': '定數',
                       'copy_fix': '複製修正命令',
                       'empty': '未能識別判定明細。',
                       'loss_detail': '詳細判定',
                       'manual_fix': '手動修正',
                       'manual_fix_hint': '複製命令，修改達成率或錯誤數字後發送。五行依次為 TAP、HOLD、SLIDE、TOUCH、BREAK；全 0 '
                                          '行是缺失占位，發送前必須填寫。',
                       'status': '狀態',
                       'title': '判定明細',
                       'validated': 'MISS 已根據譜面物量校驗'},
 'service_status': {'queue': '隊列狀態',
                    'songs': '歌曲資料',
                    'summary': '概要',
                    'tasks_today': '今日任務',
                    'title': 'JiETNG 運行狀態',
                    'uptime': '運行時長'}}
# END MESSAGE MANAGER TEXTS

# BEGIN HELP DETAILS
TEXTS["message_manager"]["help_details"] = {'ab50_allb50_ab35_allb35': 'ab50 / allb50, ab35 / allb35',
 'account_and_system': '帳號與系統',
 'achievement_one_value_is_a_lower_bound_two_values_are_a_range': '達成率。1 個值為下限，2 個值為范圍。',
 'ap50_fdx50_r50_rct50_idlb50_s50_sun50': 'ap50, fdx50, r50 / rct50, idlb50, s50 / sun50',
 'b50_best50_b40_best40_b35_best35_b15_best15': 'b50 / best50, b40 / best40, b35 / best35, b15 / '
                                                'best15',
 'best_all_best_recent_and_special_score_images': 'Best、All Best、Recent 與特殊成績圖。',
 'binding_settings_profile_sync_export_and_status': '綁定、設定、資料、同步、導出與狀態。',
 'chart_rating_one_value_is_exact_two_values_are_a_range': '單譜 Rating。1 個值精確匹配，2 個值范圍。',
 'chart_type_supports_dx_and_std_multiple_values_are_allowed': '譜面類型。支持 dx、std，可多個。',
 'commands_that_need_arguments_also_show_help_when_sent_without_ar': '需要參數的命令只發送命令名時，也會顯示對應說明。',
 'data_required': '資料要求',
 'difficulty_supports_bas_adv_exp_mas_rem_or_full_names_multiple_v': '難度。支持 bas、adv、exp、mas、rem '
                                                                     '或完整名，可多個。',
 'display_multiplier_capped_at_2_5': '擴大輸出數量倍率，最大 2.5。',
 'dx_stars_one_value_is_exact_two_values_are_a_range': 'DX 星數。1 個值精確匹配，2 個值范圍。',
 'friend_list_and_friend_record_lookup': '好友列表和好友成績查詢。',
 'generate_best_all_best_special_score_images_with_optional_filter': '產生 Best / All Best / '
                                                                     '特殊成績圖，可追加篩選參數。',
 'level_lists_constant_lists_plate_completion_and_target_progress': '等級列表、定數列表、牌子完成度和目標達成。',
 'level_or_constant_one_value_is_exact_two_values_are_a_range': '等級或定數。1 個值精確匹配，2 個值范圍。',
 'line_mentions_can_query_registered_users_self_only_commands_do_n': '支持 LINE mention '
                                                                     '查詢已註冊使用者；僅限本人命令不會接受 mention。',
 'lists_and_progress': '列表與目標',
 'missing_arguments': '參數缺失',
 'next_version_preview_using_the_next_rating_structure': '下版本預覽。按下一版本 Rating 結構預覽成績圖。',
 'page_number_starting_from_1': '頁碼，從 1 開始。',
 'querying_others': '查詢他人',
 'ranking_rating_breakdown_note_scoring_and_utility_commands': '排行榜、Rating 內訳、分值計算和輔助命令。',
 'requires_a_linked_account_with_maimai_update_completed_or_data_i': '需要已綁定帳號并完成 maimai update，或已有 '
                                                                     'Import Token / 開發者 API '
                                                                     '導入的資料。',
 'score_images': '成績圖',
 'search': '搜索',
 'search_by_artist_designer_bpm_or_random_conditions': '按藝術家、譜師、BPM 或條件隨機選曲。',
 'send_b50_help_artist_help_bpm_help_and_similar_forms_for_full_us': '發送 '
                                                                     'b50-help、artist-help、bpm-help '
                                                                     '這類格式查看完整用法。',
 'single_command': '單項說明',
 'social': '社交',
 'song_details_score_image_recognition_single_song_records_and_son': '查歌曲資訊、識別成績圖、單曲成績和歌曲 ID。',
 'songs_and_records': '歌曲與成績',
 'tools': '工具',
 'version_names_multiple_values_are_allowed_is_treated_as_plus_and': '版本名，可多個。+ 會識別為 PLUS，dx / '
                                                                     'deluxe 會歸一。',
 'without_values_sort_by_dx_score_with_values_filter_dx_score_perc': '無參數時按 DX 分排序；帶值時篩 DX Score '
                                                                     '百分比。'}
# END HELP DETAILS

TEXTS["message_manager"].update({
    "button_labels": {"uri": "查看詳情", "message": "嘗試一下"},
    "vote_labels": {"support": "支持", "oppose": "反對"},
    "search_titles": {
        "song": "歌曲搜尋結果 ({count}首)",
        "record": "成績搜尋結果 ({count}筆)",
    },
    "rating_chart_title": "定數 {level} Rating 對照表",
    "song_unit": "首",
})

# BEGIN MAIN TEXTS
TEXTS["main"] = {'account_already_bound': '已綁定 SEGA 帳號。如需重新綁定，請先使用 unbind 命令解除綁定。',
 'account_not_linked': '未綁定帳號。',
 'already_linked_title': '已綁定',
 'login_rate_limited': '觸發了日服登入速率限制，本次操作已停止。請稍後再試。',
 'candidates_failed': '取得帳號列表失敗。請稍後再試。',
 'constant_out_of_range': '定數 {level} 超出范圍。請輸入 1.0~15.0 范圍內的數值。',
 'constant_precision': '定數 {level} 無效。僅支持一位小數（例如：13.2）。',
 'correction_format_body': '請使用 7 行格式：fix-rcd 曲名、達成率，隨後依次填寫 TAP、HOLD、SLIDE、TOUCH、BREAK；每行格式為 '
                           'CP/PF/GR/GD/MS。',
 'correction_format_title': '修正格式錯誤',
 'fields_required': '請填寫所有欄位。',
 'invalid_constant': '無效的定數。請輸入 1.0~15.0 范圍內的數值。',
 'invalid_credentials': 'SEGA ID 或密碼不正確。請檢查後重試。',
 'maintenance': '官方網站正在維護中。請稍後再試。',
 'maimai_service_busy_body': 'maimai 官方服務目前回應過慢或觸發了存取限制，請稍後再試。',
 'no_linked_account': '目前沒有已綁定帳號。',
 'not_linked_title': '未綁定',
 'private_chat_title': '請在私聊使用',
 'query_failed_title': '查詢失敗',
 'recognition_failed_body': '無法讀取這張成績圖，請確認圖片完整後重試。',
 'recognition_failed_title': '識別失敗',
 'score_image_required_body': '請回復一張成績圖并發送 {command_text}。',
 'score_image_required_title': '缺少成績圖',
 'sega_id_immutable': '無法更改 SEGA ID。',
 'token_invalid': '令牌無效。',
 'token_missing': '未提供令牌。',
 'unbind_token_invalid': '令牌無效或已過期。請重新發送 unbind。',
 'vote_success': '感謝您的投票！\n'
                 '\n'
                 '支持: {support_count}人 ({support_percent:.1f}%)\n'
                 '反對: {oppose_count}人 ({oppose_percent:.1f}%)'}
# END MAIN TEXTS

# BEGIN COMMAND HELP
TEXTS["command_help"] = {'bind': '命令: bind\n'
         '說明: 返回一次性 SEGA 帳號綁定連結，用於首次綁定帳號。\n'
         '參數: 無需參數: 直接發送 bind。\n'
         '限制: 只能在私聊使用，群聊會返回安全提示。\n'
         '示例: bind',
 'calc_notes': '命令: calc <tap> <hold> <slide> [touch] <break>\n'
               '說明: 根據譜面物量計算單個 Note 分值。\n'
               '參數: 必填: <tap> <hold> <slide> <break>，當只給 4 個數字時按 TAP/HOLD/SLIDE/BREAK 解析。\n'
               '可選: [touch]，當給 5 個數字時第 4 個為 TOUCH，第 5 個為 BREAK。\n'
               '格式: 所有參數必須是非負整數，用空格分隔。\n'
               '示例: calc 500 50 80 30\n'
               'calc 500 50 80 20 30',
 'export': '命令: export <json|xml>\n'
           '說明: 將自己的成績資料導出為指定格式。\n'
           '參數: 必填: <格式>，只能填寫 json 或 xml。\n'
           '輸出: 成功後返回臨時下載連結和複製連結按鈕。\n'
           '要求: 需要已有成績資料；如果沒有資料會返回空資料提示。\n'
           '示例: export json',
 'friend_list': '命令: friends\n'
                '說明: 查看已添加的好友列表。\n'
                '參數: 無需參數: 直接發送命令，會從 maimai NET 讀取好友列表。\n'
                '相關: 好友成績圖可透過 friend-rcd <好友編號或名稱> [成績圖類型] [篩選參數] 使用。\n'
                '示例: friends',
 'level_rank_list': '命令: <等級或定數> levels\n'
                    '說明: 查看指定等級或定數相關歌曲列表。\n'
                    '參數: 必填: <等級或定數>，支持 13、13+、14、13.6 等格式。\n'
                    '匹配: 整數/帶 + 按等級匹配，小數按定數精確匹配。\n'
                    '示例: 13.6 levels\n'
                    '14+ levels',
 'level_rank_progress': '命令: <等級或分類><評價> prog [-uc|-up|-c]\n'
                        '說明: 查看指定等級或分類中評價目標的達成情況。\n'
                        '參數: 必填: <等級或分類>，等級支持 11-15；分類支持 '
                        'vocaloid、touhou、popani、gekichu、game、maimai。\n'
                        '必填: <評價>，緊跟等級/分類書寫，支持 s、s+、ss、ss+、sss、sss+、fc、fc+、ap、ap+、fdx、fdx+。\n'
                        '可選: -uc 僅看未完成目標，-up 僅看未游玩，-c 僅看已完成目標。\n'
                        '格式: 等級可直接連寫，例如 14sss+ prog；分類建議和評價之間加空格，例如 vocaloid sss+ prog。\n'
                        '示例: 14sss+ prog\n'
                        '13ap prog -uc\n'
                        'vocaloid sss+ prog\n'
                        'popani ss+ prog -up',
 'level_records': '命令: <等級或定數> records [頁碼]\n'
                  '說明: 查看指定等級或定數的成績列表。\n'
                  '參數: 必填: <等級或定數>，支持 13、13+、14、13.6 等格式。\n'
                  '可選: [頁碼]，正整數，從 1 開始；省略時顯示第 1 頁。\n'
                  '匹配: 整數/帶 + 按等級匹配，小數按定數精確匹配。\n'
                  '示例: 13.6 records\n'
                  '14 records 2',
 'maimai_update': '命令: maimai update\n'
                  '說明: 從 maimai NET 獲取并更新已游玩的歌曲成績資料。\n'
                  '參數: 無需參數: 直接發送命令即可開始同步。\n'
                  '示例: maimai update\n'
                  '註意: 需要先綁定 SEGA 帳號。',
 'plate': '命令: <牌子名> plate [-uc|-up|-c]\n'
          '說明: 查看版本牌子或稱號類目標的完成情況。\n'
          '參數: 必填: <牌子名>，寫在 plate 前面，例如 真極、檄將 等。\n'
          '可選: -uc 僅看未完成項目，-up 僅看未游玩項目，-c 僅看已完成項目。\n'
          '格式: 過濾項寫在命令最後；不寫過濾項時顯示完整完成度。\n'
          '示例: 真極 plate\n'
          '真極 plate -uc',
 'profile': '命令: profile\n'
            '說明: 查看自己的 JiETNG 帳號資訊，包括綁定狀態、伺服器和語言設定。\n'
            '參數: 無需參數: 直接發送 profile。\n'
            '限制: 只能在私聊使用，避免公開個人資訊。\n'
            '示例: profile',
 'random_song': '命令: random [條件]\n'
                '說明: 隨機推薦一首歌曲。\n'
                '參數: 可選: [條件]，可寫等級、定數、譜面類型、難度等關鍵詞。\n'
                '格式: 多個條件用空格分隔；省略條件時從全部歌曲中隨機。\n'
                '示例: random\n'
                'random 13+ dx\n'
                'random 14 mas',
 'ranking': '命令: rank [jp|intl]\n'
            '說明: 查看 DX Rating 總體排行榜。\n'
            '參數: 可選: [伺服器]，支持 jp、intl；省略時使用目前使用者綁定的伺服器。\n'
            '格式: 伺服器參數寫在 rank 後面，用空格分隔。\n'
            'Mention: 可 @ 已註冊使用者，查看對方在總體榜中的位置；需對方允許 @ 查詢成績。\n'
            '示例: rank\n'
            'rank intl',
 'rc': '命令: rc <定數>\n'
       '說明: 查詢 Rating Composition / レート內訳相關資訊。\n'
       '參數: 必填: <定數>，支持 1.0 到 15.0 之間的數字。\n'
       '格式: 可寫整數或小數，例如 13、13.6、14.9。\n'
       '限制: 超出 1.0-15.0 或無法轉成數字會返回輸入錯誤。\n'
       '示例: rc 14\n'
       'rc 13.6',
 'rebind': '命令: rebind\n'
           '說明: 返回 SEGA 帳號編輯連結，用於更新已綁定帳號的資訊。\n'
           '參數: 無需參數: 直接發送 rebind。\n'
           '要求: 必須已經綁定 SEGA 帳號。\n'
           '限制: 只能在私聊使用。\n'
           '示例: rebind',
 'refreshmenu': '命令: refreshmenu\n'
                '說明: 根據目前綁定狀態重新關聯發送者自己的 LINE Rich Menu。\n'
                '參數: 無需參數: 直接發送 refreshmenu。\n'
                '限制: 僅影響發送者自己的 Rich Menu。\n'
                '示例: refreshmenu',
 'score_recognition': '命令: rec [-flex]\n說明: 使用本地 OCR 識別完整成績；校驗通過後返回成績圖片，校正失敗時顯示原始識別資料和可複製的修正命令。不會自動呼叫 AI；AI 識別請使用 ai-rec。\n參數: 必須回覆一張成績圖；可選 -flex，使用 Flex 卡片輸出。\n示例: rec\nrec -flex',
 'ai_score_recognition': '命令: ai-rec [-flex]\n說明: 使用 Codex AI 識別成績原圖，校驗通過後返回成績圖片。\n參數: 必須回覆一張成績圖；可選 -flex，使用 Flex 卡片輸出。\n限制: 需要 AI 識別權限。一般 rec 不會呼叫 AI。\n示例: ai-rec\nai-rec -flex',
 'search_by_artist': '命令: artist <關鍵詞> [頁碼]\n'
                     '說明: 按藝術家名搜索歌曲。\n'
                     '參數: 必填: <關鍵詞>，artist 後面的文本會作為藝術家名進行不區分大小寫的包含匹配。\n'
                     '可選: [頁碼]，正整數，從 1 開始；寫在關鍵詞最後。\n'
                     '限制: 僅限私聊使用，避免群聊刷屏。\n'
                     '示例: artist Nanahira\n'
                     'artist sasakure 2',
 'search_by_bpm': '命令: bpm <BPM或范圍> [頁碼]\n'
                  '說明: 按 BPM 精確值或范圍搜索歌曲。\n'
                  '參數: 必填: <BPM或范圍>，支持單值、連字符范圍、空格范圍。\n'
                  '單值: bpm 180 表示精確匹配 BPM 180。\n'
                  '范圍: bpm 0-120 或 bpm 120 180 表示閉區間，端點可為 0。\n'
                  '可選: [頁碼]，正整數，從 1 開始；寫在最後。\n'
                  '限制: 僅限私聊使用。\n'
                  '示例: bpm 180\n'
                  'bpm 0-120\n'
                  'bpm 120 180 2',
 'search_by_designer': '命令: designer <關鍵詞> [頁碼]\n'
                       '說明: 按譜面設計師名搜索歌曲。\n'
                       '參數: 必填: <關鍵詞>，designer 後面的文本會匹配各難度譜面的 noteDesigner 字段。\n'
                       '可選: [頁碼]，正整數，從 1 開始；寫在關鍵詞最後。\n'
                       '限制: 僅限私聊使用，避免群聊刷屏。\n'
                       '示例: designer Jack\n'
                       'designer 譜面 2',
 'settings': '命令: settings\n'
             '說明: 返回個人設定頁面連結，用於修改時區、語言、背景圖片、隱私等選項。\n'
             '參數: 無需參數: 直接發送 settings。\n'
             '限制: 只能在私聊使用。\n'
             '示例: settings',
 'song_info': '命令: <曲名> info\n'
              '說明: 查詢歌曲基本資訊、譜面資訊和 BPM；也可以回復成績圖片直接發送 info，自動識別曲名。\n'
              '參數: 文本查詢時填寫 <曲名>，可以是完整曲名、部分曲名或別名；圖片查詢時無需填寫曲名。\n'
              '匹配: 如果匹配到多首歌，會返回可選擇的候選結果。\n'
              '示例: ヒバナ info\n'
              '（回復圖片）info',
 'song_record': '命令: <曲名> record\n'
                '說明: 按曲名或別名查詢自己的單曲成績。\n'
                '參數: 必填: <曲名>，寫在 record 前面，可以是完整曲名、部分曲名或別名。\n'
                '匹配: 如果匹配到多首歌，會返回可選擇的候選結果。\n'
                '示例: ヒバナ record',
 'status': '命令: status\n說明: 查看機器人服務狀態，包括運行時間、任務隊列和系統資源。\n參數: 無需參數: 直接發送 status。\n示例: status',
 'unbind_prompt': '命令: unbind\n'
                  '說明: 返回一次性 SEGA 帳號解除綁定連結，在瀏覽器內確認後才會刪除帳號資料。\n'
                  '參數: 無需參數: 直接發送 unbind。\n'
                  '要求: 必須已經綁定 SEGA 帳號或已啟用 Import Token 帳號。\n'
                  '限制: 只能在私聊使用。\n'
                  '示例: unbind',
 'version_songs': '命令: <版本名> ver\n'
                  '說明: 查看指定版本歌曲列表。\n'
                  '參數: 必填: <版本名>，寫在 ver 前面，支持版本完整名或可識別簡稱。\n'
                  '格式: 版本名可包含空格；整段 ver 前的文本都會作為版本查詢詞。\n'
                  '示例: BUDDiES ver\n'
                  'PRiSM PLUS ver'}
# END COMMAND HELP

# BEGIN TEMPLATE TEXTS
TEXTS["web"]["bind"] = {
    "pageTitle": "SEGA 帳號綁定 | JiETNG",
    "pageTitleRebind": "編輯帳號設定 | JiETNG",
    "heading": "SEGA 帳號綁定",
    "headingRebind": "編輯帳號設定",
    "labelSegaid": "SEGA ID",
    "labelPassword": "SEGA 密碼",
    "labelVersion": "版本",
    "optJp": "日本版",
    "optIntl": "國際版",
    "labelTimezone": "時區",
    "labelLanguage": "語言",
    "languagePlatformHint": "語言設定可能不會套用到 LINE 以外的第三方平台。",
    "labelBindType": "綁定方式",
    "optBindSega": "SEGA 帳號",
    "optBindImport": "僅使用 Import Token",
    "bindTypeImportHelp": "不保存 SEGA 帳號密碼，之後透過匯出工具上傳成績。",
    "submitBtn": "綁定",
    "submitBtnImport": "產生 Token",
    "submitBtnRebind": "更新",
    "noticeTitle": "使用須知",
    "aimeModalTitle": "選擇 Aime",
    "aimeModalDescription": "請選擇要綁定的帳號。",
    "aimeConfirm": "確定",
    "aimeFallbackName": "Aime 帳號",
    "ratingLabel": "Rating",
    "trophyLabel": "稱號",
    "accountListError": "無法取得帳號列表。"
}
TEXTS["web"]["bind_notice_html"] = "您輸入的所有資訊都會以加密形式安全保存，不會提供給第三方。<br><br>不過，本服務由個人營運，不提供官方保證或支援。基於本服務的性質，如果您對安全性或營運政策有疑慮，請勿使用。資訊提供完全基於您自己的判斷與責任。"
TEXTS["web"]["settings"] = {
    "pageTitle": "設定 | JiETNG",
    "heading": "設定",
    "labelLanguage": "語言",
    "languagePlatformHint": "語言設定可能不會套用到 LINE 以外的第三方平台。",
    "labelTimezone": "時區",
    "skinSection": "皮膚與背景",
    "labelSkin": "皮膚",
    "skinUsesBackground": "使用背景圖",
    "skinNoBackground": "不使用背景圖",
    "skinBackgroundHint": "使用下方選擇的背景圖、模糊和遮罩設定；關閉背景圖時使用預設底色。",
    "skinNoBackgroundHint": "此皮膚不使用背景圖。既有背景設定會保留，切換回來後仍可使用。",
    "labelBgEnabled": "背景圖片",
    "privacyPanelTitle": "隱私設定",
    "rankingPanelTitle": "排行榜設定",
    "labelMentionScoreQuery": "允許他人 @ 我查詢成績",
    "metaMentionScoreQuery": "開啟後，其他使用者可以透過 LINE mention 查看你的成績圖和成績進度。",
    "labelGlobalRanking": "參與總體排行榜",
    "metaGlobalRanking": "會顯示在 rank / ranking 的總體榜中。",
    "labelBgBlur": "背景模糊",
    "labelBgOverlay": "背景淡化",
    "bgHint": "不選擇時，會從所有背景中隨機使用。",
    "sectionCustomBg": "自訂背景",
    "customBgHint": "上傳您自己的背景圖片（限 2 張，每張 5MB 以內）。",
    "labelCustomBg": "選擇圖片",
    "uploadSub": "PNG / JPG / JPEG / WebP（5MB 以內）",
    "uploadBtn": "上傳",
    "uploadFailed": "上傳失敗。",
    "deleteCustomBgBtn": "刪除",
    "deleteCustomBgConfirm": "確定刪除自訂背景嗎？",
    "deleteAllCustomBgBtn": "全部刪除",
    "deleteAllCustomBgConfirm": "確定刪除全部自訂背景嗎？",
    "submitBtn": "保存",
    "importTokenTitle": "成績匯入 Token",
    "importTokenHelp": "用於讓外部工具把處理後的成績 JSON 上傳到 JiETNG。",
    "importTokenCreate": "產生 Token",
    "importTokenNoteLabel": "Token 名稱",
    "importTokenNotePlaceholder": "例如：工具",
    "importTokenNoteRequired": "請輸入 Token 名稱。",
    "importTokenResultTitle": "Token（只顯示這一次）",
    "importTokenCopy": "複製",
    "importTokenCopied": "已複製",
    "importTokenEmpty": "還沒有 Token。",
    "importTokenRevoke": "撤銷",
    "importTokenRevoked": "已撤銷",
    "importTokenDelete": "刪除",
    "importTokenCreateError": "產生 Token 失敗。",
    "importTokenRevokeConfirm": "確定撤銷這個匯入 Token 嗎？",
    "importTokenRevokeError": "撤銷失敗。",
    "importTokenDeleteConfirm": "確定刪除這個已撤銷的匯入 Token 嗎？",
    "importTokenDeleteError": "刪除失敗。"
}
TEXTS["web"]["settings_permissions"] = {
    "panelTitle": "存取權限管理",
    "ownerLabel": "建立者",
    "revokeBtn": "撤銷",
    "revokeConfirm": "確定撤銷此服務的存取權限嗎？",
    "revokeError": "撤銷失敗，請重試"
}
# END TEMPLATE TEXTS

# BEGIN GENERATED MESSAGE TEXTS
MESSAGE_TEXTS = {'access_error_text': '🙇 現在訪問量很大…請稍後再試！',
 'already_bound_text': '目前已經綁定 SEGA 帳號。\n'
                       '\n'
                       '修改密碼、伺服器版本或 Aime 請使用 rebind。\n'
                       '修改時區、語言、背景圖片、隱私等個人設定請使用 settings。\n'
                       '如需綁定其他帳號，請先使用 unbind 解除目前綁定。',
 'bind_group_warning_text': 'bind 只能在私聊使用。請直接向機器人發送消息。',
 'calc_button_text': 'Note 計算',
 'calc_flex_text': {'alt_multi': 'Note 計算結果',
                    'alt_single': 'Note 計算結果',
                    'max_tap_great': '最多 {count} 個 TAP GREAT',
                    'subtitle': 'Note 計算',
                    'title_distribution': 'Note 分布'},
 'cannot_do_for_others_text': '該命令只能用於你自己的帳號。',
 'dxdata_current_stats_text': '📈 目前: {songs}首歌曲 / {sheets}個譜面',
 'dxdata_fetch_failed_text': '❌ 資料獲取失敗！',
 'dxdata_first_update_text': '(首次更新完成！)',
 'dxdata_initial_stats_sheets_text': '📊 譜面: {count}個',
 'dxdata_initial_stats_songs_text': '📈 歌曲: {count}首',
 'dxdata_last_update_text': '📅 上次更新: {timestamp}',
 'dxdata_new_sheets_text': '📊 新增譜面: +{count}個',
 'dxdata_new_songs_text': '🎵 新增歌曲: +{count}首',
 'dxdata_no_new_sheets_text': '📊 新增譜面: 無',
 'dxdata_no_new_songs_text': '🎵 新增歌曲: 無',
 'dxdata_parse_failed_text': '❌ 資料解析失敗！',
 'dxdata_sheets_decreased_text': '📊 譜面: {count}個',
 'dxdata_songs_decreased_text': '🎵 歌曲: {count}首',
 'dxdata_update_success_text': '✅ Dxdata 更新成功！',
 'export_alt_text': '成績資料已導出',
 'export_empty_text': '還沒有可導出的成績資料。請先使用『maimai update』更新後再試。',
 'export_failed_text': '成績資料導出失敗，請稍後再試。',
 'export_flex_button_text': '下載',
 'export_flex_copy_button_text': '複製連結',
 'export_flex_footnote_text': '下載連結將在 {ttl} 分鐘後失效',
 'export_flex_summary_text': 'Best: {best} 條  ·  Recent: {recent} 條\n格式: {fmt}（{size_kb} KB）',
 'export_flex_title_text': '成績資料已導出',
 'friend_error_text': '還沒有收藏的好友。',
 'friend_list_alt_text': '收藏的好友',
 'friend_rcd_error_text': '指定使用者不在你的好友列表中。',
 'friend_rcd_group_warning_text': '好友成績命令只能在私聊使用。請直接向機器人發送消息。',
 'friend_rcd_text': '{name} 的資料',
 'info_error_text': '你的 maimai 玩家資料尚未保存。請先使用『maimai update』更新後再試。',
 'input_error_text': '無法識別該命令，請檢查輸入內容。',
 'level_not_supported_text': '不支持該等級的定數表。\n僅支持12級及以上。',
 'level_record_not_found_text': '指定等級「{level}」的第 {page} 頁記錄可能不存在...',
 'level_record_page_hint_text': '這是第 {page} 頁的資料！',
 'maintenance_error_text': '🔧 咦？官方網站好像在維護中！\n維護時間無法訪問，請稍後再試~',
 'mention_error_text': '被提到的使用者尚未註冊 JiETNG。',
 'mention_not_allowed_text': '被提到的使用者已關閉 @ 查詢成績。',
 'mention_no_matching_data_text': '被提到的使用者沒有符合條件的成績資料。',
 'mention_record_error_text': '被提到的使用者還沒有 maimai 成績資料。',
 'nearby_stores_alt_text': '附近的 maimai 機廳',
 'no_matching_data_text': '沒有找到符合條件的成績資料。',
 'notice_header_text': '📢 公告',
 'perm_request_accept_button_text': '接受',
 'perm_request_accept_success_text': '✅ 已接受存取權限請求！\n'
                                     '\n'
                                     'Token ID: {token_id}\n'
                                     '申請者: {requester_name}\n'
                                     '\n'
                                     '該 token 現在可以訪問你的帳戶資訊了。',
 'perm_request_already_processed_text': '該請求已經處理過了。',
 'perm_request_notification_alt_text': '你有 {count} 個存取權限請求',
 'perm_request_notification_subtitle_text': '{count} 個新請求',
 'perm_request_notification_title_text': '存取權限請求',
 'perm_request_reject_button_text': '拒絕',
 'perm_request_reject_success_text': '✅ 已拒絕存取權限請求。\n\nToken ID: {token_id}\n申請者: {requester_name}',
 'plate_error_text': '沒有找到指定的牌子。',
 'private_info_group_warning_text': '個人資訊命令只能在私聊使用。請直接向機器人發送消息。',
 'quick_reply_labels': {'account_bind': '綁定帳號',
                        'all_best_50': 'All Best 50',
                        'maimai_update': '更新資料',
                        'recent_50': 'Recent 50',
                        'retry': '再試一次',
                        'support': '幫助'},
 'ranking_alt_text': 'Rating 排行榜',
 'ranking_no_data_text': '暫無排行榜資料。',
 'ranking_title_text': 'Rating 排行榜',
 'rate_limit_msg_text': '🔄 系統目前較為繁忙，請稍後再試。',
 'rebind_button_text': '編輯帳號',
 'rebind_description_text': '修改已綁定 SEGA 帳號的密碼、伺服器版本或 Aime。',
 'rebind_group_warning_text': 'rebind 只能在私聊使用。請直接向機器人發送消息。',
 'rebind_msg_text': '✅ SEGA 帳號資訊已更新。',
 'rebind_not_bound_text': '尚未綁定 SEGA 帳號。請先使用 bind 完成綁定。',
 'rebind_title_alt_text': '編輯帳號設定',
 'record_error_text': '還沒有 maimai 成績資料。請先使用『maimai update』更新後再試。',
 'search_group_warning_text': 'artist / designer / bpm 搜索只能在私聊使用。',
 'sega_bind_alt_text': '綁定 SEGA 帳號',
 'sega_bind_button_text': '開始綁定',
 'sega_bind_description_text': '打開首次綁定用的 SEGA 帳號綁定頁面。',
 'sega_bind_title_text': '綁定 SEGA 帳號',
 'segaid_error_text': '你還沒有綁定 SEGA 帳號吧？',
 'settings_button_text': '打開設定',
 'settings_description_text': '修改時區、語言、背景圖片和隱私設定。',
 'settings_group_warning_text': 'settings 只能在私聊使用。請直接向機器人發送消息。',
 'settings_title_alt_text': '個人設定',
 'song_error_text': '沒有找到符合條件的歌曲。',
 'song_info_alt_text': '歌曲資訊',
 'song_record_alt_text': '歌曲成績',
 'store_error_text': '🥹 附近沒有找到遊戲廳',
 'system_error_text': '😵 發生系統錯誤…已通知管理員。請稍後再試。',
 'unbind_button_text': '打開解除綁定頁面',
 'unbind_description_text': '在瀏覽器內確認并刪除已綁定 SEGA 帳號和已保存成績資料。',
 'unbind_group_warning_text': 'unbind 只能在私聊使用。請直接向機器人發送消息。',
 'unbind_title_alt_text': '解除帳號綁定',
 'update_result_flex_text': {'alt_text_error': '成績更新失敗',
                             'alt_text_success': '成績更新完成',
                             'elapsed_time_label': '耗時',
                             'failed': '失敗',
                             'status_best_records': 'Best 成績',
                             'status_label': '未更新項目',
                             'status_recent_records': 'Recent 成績',
                             'status_user_info': '玩家資料',
                             'summary_section': '概要',
                             'title_error': '成績更新失敗',
                             'title_success': '成績更新完成',
                             'update_time_label': '更新時間'},
 'user_info_flex_text': {'account_section': '帳號',
                         'alt_text': '使用者資訊',
                         'copy_id': '複製ID',
                         'intl_server': '國際服',
                         'jp_server': '日服',
                         'lang_en': '英語',
                         'lang_ja': '日語',
                         'lang_zh': '中文',
                         'language_label': '語言',
                         'last_update_label': '最後更新',
                         'name_label': '玩家名稱',
                         'not_bound': '未綁定',
                         'password_label': '密碼',
                         'profile_section': '玩家資訊',
                         'rating_label': 'Rating',
                         'sega_id_label': 'SEGA ID',
                         'server_label': '伺服器',
                         'settings_section': '設定',
                         'title': '使用者資訊',
                         'user_id_label': 'LINE ID'},
 'version_error_text': '沒有找到指定的版本。',
 'view_info_button_text': '查看歌曲資訊',
 'view_record_button_text': '查看成績'}
# END GENERATED MESSAGE TEXTS

TEXTS["messages"] = MESSAGE_TEXTS

TEXTS["images"] = {
    "score": {
        "subtitle": "判定詳情",
        "judgement": "判定資料",
        "loss": "詳細判定",
        "break": "BREAK 詳細判定",
        "empty": "未能辨識判定詳情。",
        "distribution": '判定分布與失分',
        "cell_legend": '數量 / 合計扣分 / 單個扣分',
        "verified": '已校驗',
        "check_required": '待確認',
        "validation_note": '部分結果尚未通過校驗，請檢查辨識判定。',
        "common_total": "普通音符合計",
        "break_total": "BREAK 合計",
    },
    "records": {
        "avg_level": "平均等級",
        "avg_achievement": "平均達成率",
        "avg_rating": "平均 Rating",
    },
    "progress": {
        "completed": "已完成",
        "incomplete": "未完成",
        "unplayed": "未遊玩",
        "total": "總計",
        "progress_suffix": "目標",
        "level_list_suffix": "等級列表",
    },
    "song": {
        "artist": "藝術家", "category": "分類", "bpm": "BPM", "version": "版本",
        "unknown_title": "未知曲名", "unknown_artist": "未知藝術家", "unknown_category": "未知分類",
        "headers": {
            "chart_type": "譜面難度", "level": "等級", "designer": "譜師",
            "total": "合計", "tap": "TAP", "hold": "HOLD", "slide": "SLIDE",
            "touch": "TOUCH", "break": "BREAK", "jp": "日服", "intl": "國際服", "usa": "美國",
        },
    },
}
