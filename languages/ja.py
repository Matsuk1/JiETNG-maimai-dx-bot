"""Japanese language plugin."""

LANGUAGE = {
    "code": "ja",
    "label": "日本語",
    "aliases": ("jp", "jpn", "ja-jp"),
}

TEXTS = {
    "web": {
        "loading": "読み込み中",
        "notice_html": "<strong>ご利用に関するご注意</strong><br>ご入力いただいた情報はすべて暗号化された形式で安全に保存され、第三者に提供されることはありません。<br><br>ただし、本サービスは個人によって運営されており、公式な保証やサポートは提供されておりません。<br>本サービスの性質上、セキュリティや運用方針に不安がある場合は、利用をお控えいただくようお願いいたします。<br>情報提供はあくまでご自身の判断と責任にてお願いいたします。",
        "error": {
            "title": "エラー",
            "fallback_message": "処理中にエラーが発生しました。",
        },
        "unbind": {
            "title": "アカウント連携解除",
            "lead": "このブラウザで確認すると、連携済みアカウントを JiETNG から削除します。",
            "type": "種類",
            "account": "SEGA アカウント",
            "server": "サーバー",
            "warning": "保存済みのアカウント情報、関連設定、成績、最近の成績を削除します。この操作は取り消せません。",
            "submit": "連携を解除",
        },
        "success": {
            "titles": {
                "settings": "設定保存完了",
                "import_token": "Import Token 作成完了",
                "unbind": "連携解除完了",
                "rebind": "更新成功",
                "bind": "バインド成功",
            },
            "descriptions": {
                "settings": "設定が正常に保存されました。",
                "import_token": "この Token をブックマークレットに保存してください。初回の成績アップロード後、JiETNG のユーザーデータが初期化されます。",
                "unbind": "連携済みアカウントと保存済み成績を JiETNG から削除しました。",
                "rebind": "アカウント設定が正常に更新されました。",
                "bind": "JiETNGとの連携が成功しました。",
            },
            "token": {
                "shown_once": "Token は今回のみ表示されます",
                "copy": "Tokenをコピー",
                "copied": "コピーしました",
            },
        },
    }
}

# BEGIN MESSAGE MANAGER TEXTS
TEXTS["message_manager"] = {'help_ui': {'b_subtitle': 'Best / All Best / 特殊成績画像とフィルター',
             'b_title': 'B 系スコア画像',
             'catalog_subtitle': 'command-help で詳細を表示',
             'catalog_title': 'コマンド一覧',
             'categories': 'カテゴリ',
             'command': 'コマンド',
             'default_purpose': 'このコマンドの説明を表示します。',
             'detail_hint': '詳細ヘルプ',
             'docs_button': 'ヘルプドキュメント',
             'examples': '例',
             'function': '説明',
             'help_title': 'コマンドヘルプ',
             'modes': 'モード',
             'none': 'なし',
             'notes': '注意',
             'params': '引数',
             'usage': '使い方'},
 'score_recognition': {'break_detail': 'BREAK 詳細判定',
                       'break_detail_source_multiple': 'Calc 推定：{count} 件の候補から最も可能性の高い組み合わせ',
                       'break_detail_source_single': 'Calc 推定：一致する組み合わせは 1 件です',
                       'break_row_source_multiple': 'BREAK 行には Calc 候補が {count} '
                                                    '件あります。以上は現在の候補の内訳です',
                       'breakdown': '判定データ',
                       'calc_corrected': 'Calc で判定を自動補正しました',
                       'calc_incomplete': 'Calc の達成率は一致しますが、判定行が不足しています。-? は欠損項目です',
                       'calc_inferred': 'BREAK をノーツ数と Calc から推定しました',
                       'calc_mismatch': 'Calc が不一致を検出しましたが、1 項目には特定できません',
                       'calc_uncertain': 'Calc が不一致を検出しました。? は認識候補です',
                       'calc_validated': 'Calc で達成率と判定データを確認済み',
                       'compact_fix': 'BREAK を修正',
                       'constant': '定数',
                       'copy_fix': '修正コマンドをコピー',
                       'empty': '判定詳細を認識できませんでした。',
                       'loss_detail': '詳細判定',
                       'manual_fix': '手動修正',
                       'manual_fix_hint': 'コマンドをコピーし、達成率または誤った数値を修正して送信してください。行順は '
                                          'TAP、HOLD、SLIDE、TOUCH、BREAK です。全て 0 '
                                          'の行は欠損データのプレースホルダーなので、送信前に入力してください。',
                       'status': 'ステータス',
                       'title': '判定詳細',
                       'validated': 'MISS を譜面ノーツ数で検証済み'},
 'service_status': {'queue': 'キュー状況',
                    'songs': '楽曲データ',
                    'summary': '概要',
                    'tasks_today': '本日のタスク',
                    'title': 'JiETNG 稼働状態',
                    'uptime': '稼働時間'}}
# END MESSAGE MANAGER TEXTS

# BEGIN HELP DETAILS
TEXTS["message_manager"]["help_details"] = {'ab50_allb50_ab35_allb35': 'ab50 / allb50, ab35 / allb35',
 'account_and_system': 'アカウントとシステム',
 'achievement_one_value_is_a_lower_bound_two_values_are_a_range': '達成率。1 つは下限、2 つは範囲です。',
 'ap50_fdx50_r50_rct50_idlb50_s50_sun50': 'ap50, fdx50, r50 / rct50, idlb50, s50 / sun50',
 'b50_best50_b40_best40_b35_best35_b15_best15': 'b50 / best50, b40 / best40, b35 / best35, b15 / '
                                                'best15',
 'best_all_best_recent_and_special_score_images': 'Best、All Best、Recent、特殊成績画像。',
 'binding_settings_profile_sync_export_and_status': '連携、設定、プロフィール、同期、エクスポート、状態確認。',
 'chart_rating_one_value_is_exact_two_values_are_a_range': '単曲 Rating。1 つは完全一致、2 つは範囲です。',
 'chart_type_supports_dx_and_std_multiple_values_are_allowed': '譜面種別。dx、std を複数指定できます。',
 'commands_that_need_arguments_also_show_help_when_sent_without_ar': '引数が必要なコマンドを引数なしで送ると説明を表示します。',
 'data_required': 'データ要件',
 'difficulty_supports_bas_adv_exp_mas_rem_or_full_names_multiple_v': '難易度。bas、adv、exp、mas、rem '
                                                                     'または正式名を複数指定できます。',
 'display_multiplier_capped_at_2_5': '表示件数の倍率。最大 2.5 です。',
 'dx_stars_one_value_is_exact_two_values_are_a_range': 'DX 星数。1 つは完全一致、2 つは範囲です。',
 'friend_list_and_friend_record_lookup': 'フレンド一覧とフレンド成績検索。',
 'generate_best_all_best_special_score_images_with_optional_filter': 'Best / All Best / '
                                                                     '特殊成績画像を生成し、フィルターを追加できます。',
 'level_lists_constant_lists_plate_completion_and_target_progress': 'レベルリスト、定数リスト、プレート達成状況、目標達成。',
 'level_or_constant_one_value_is_exact_two_values_are_a_range': 'レベルまたは定数。1 つは完全一致、2 つは範囲です。',
 'line_mentions_can_query_registered_users_self_only_commands_do_n': 'LINE '
                                                                     'メンションで登録済みユーザーを検索できます。本人専用コマンドはメンション不可です。',
 'lists_and_progress': 'リストと目標',
 'missing_arguments': '引数不足',
 'next_version_preview_using_the_next_rating_structure': '次バージョンプレビュー。次の Rating 構成で成績画像を表示します。',
 'page_number_starting_from_1': 'ページ番号。1 から始まります。',
 'querying_others': '他ユーザー検索',
 'ranking_rating_breakdown_note_scoring_and_utility_commands': 'ランキング、レート内訳、ノーツ点数計算、補助コマンド。',
 'requires_a_linked_account_with_maimai_update_completed_or_data_i': 'maimai update 済みの連携アカウント、または '
                                                                     'Import Token / Developer API '
                                                                     'で取り込んだデータが必要です。',
 'score_images': '成績画像',
 'search': '検索',
 'search_by_artist_designer_bpm_or_random_conditions': 'アーティスト、譜面制作者、BPM、ランダム条件で検索。',
 'send_b50_help_artist_help_bpm_help_and_similar_forms_for_full_us': 'b50-help、artist-help、bpm-help '
                                                                     'のように送信すると詳しい使い方を表示します。',
 'single_command': '単体説明',
 'social': 'フレンド',
 'song_details_score_image_recognition_single_song_records_and_son': '楽曲情報、リザルト画像認識、単曲成績、楽曲 ID 検索。',
 'songs_and_records': '楽曲と成績',
 'tools': 'ツール',
 'version_names_multiple_values_are_allowed_is_treated_as_plus_and': 'バージョン名。複数指定可。+ は PLUS、dx / '
                                                                     'deluxe は正規化されます。',
 'without_values_sort_by_dx_score_with_values_filter_dx_score_perc': '値なしでは DX スコア順、値ありでは DX '
                                                                     'スコア割合で絞り込みます。'}
# END HELP DETAILS

TEXTS["message_manager"].update({
    "button_labels": {"uri": "詳細を見る", "message": "試してみる"},
    "vote_labels": {"support": "支持", "oppose": "反対"},
    "search_titles": {
        "song": "楽曲検索結果 ({count}件)",
        "record": "レコード検索結果 ({count}件)",
    },
    "rating_chart_title": "定数 {level} のRating対照表",
    "song_unit": "曲",
})

# BEGIN MAIN TEXTS
TEXTS["main"] = {'account_already_bound': 'すでに SEGA アカウントが連携されています。再度連携する場合は、先に unbind コマンドで連携を解除してください。',
 'account_not_linked': 'アカウントが連携されていません。',
 'already_linked_title': '連携済み',
 'login_rate_limited': '日本版のログインのレート制限に達したため、今回の操作を中止しました。しばらくしてからもう一度お試しください。',
 'candidates_failed': 'アカウント一覧の取得に失敗しました。しばらくしてからもう一度お試しください。',
 'constant_out_of_range': '定数 {level} は範囲外です。1.0～15.0の範囲で入力してください。',
 'constant_precision': '定数 {level} は無効です。小数点以下は1桁まで入力可能です（例：13.2）。',
 'correction_format_body': '7 行で入力してください。fix-rcd 曲名、達成率、TAP、HOLD、SLIDE、TOUCH、BREAK の順で、各判定行を '
                           'CP/PF/GR/GD/MS 形式にします。',
 'correction_format_title': '修正形式エラー',
 'fields_required': 'すべての項目を入力してください。',
 'invalid_constant': '無効な定数です。1.0～15.0の範囲で入力してください。',
 'invalid_credentials': 'SEGA ID または パスワード が正しくありません。もう一度確認してください。',
 'maintenance': '公式サイトがメンテナンス中です。しばらくしてからもう一度お試しください。',
 'no_linked_account': '連携済みアカウントがありません。',
 'not_linked_title': '未連携',
 'private_chat_title': '個人チャットで使用してください',
 'recognition_failed_body': 'このリザルト画像を読み取れませんでした。画面全体が写っているか確認して再試行してください。',
 'recognition_failed_title': '認識に失敗しました',
 'score_image_required_body': 'リザルト画像に返信して {command_text} を送信してください。',
 'score_image_required_title': 'リザルト画像が必要です',
 'sega_id_immutable': 'SEGA ID を変更することはできません。',
 'token_invalid': 'トークンが無効です。',
 'token_missing': 'トークンが提供されていません。',
 'unbind_token_invalid': 'トークンが無効、または期限切れです。もう一度 unbind を送信してください。',
 'vote_success': '投票ありがとうございます！\n'
                 '\n'
                 '支持: {support_count}人 ({support_percent:.1f}%)\n'
                 '反対: {oppose_count}人 ({oppose_percent:.1f}%)'}
# END MAIN TEXTS

# BEGIN COMMAND HELP
TEXTS["command_help"] = {'bind': '命令: bind\n'
         '说明: 初回連携用の SEGA アカウント連携 URL を返します。\n'
         '参数: 引数なし: bind をそのまま送信します。\n'
         '制限: 個人チャット専用です。グループでは安全警告を返します。\n'
         '示例: bind',
 'calc_notes': '命令: calc <tap> <hold> <slide> [touch] <break>\n'
               '说明: ノーツ数から 1 ノーツあたりの点数を計算します。\n'
               '参数: 必須: <tap> <hold> <slide> <break>。4 数値の場合は TAP/HOLD/SLIDE/BREAK として解析します。\n'
               '任意: [touch]。5 数値の場合は 4 番目が TOUCH、5 番目が BREAK です。\n'
               '形式: すべて非負整数で、空白区切りです。\n'
               '示例: calc 500 50 80 30\n'
               'calc 500 50 80 20 30',
 'export': '命令: export <json|xml>\n'
           '说明: 自分の成績データを指定形式で書き出します。\n'
           '参数: 必須: <形式>。json または xml のみ指定できます。\n'
           '出力: 成功時は一時ダウンロード URL とコピー用ボタンを返します。\n'
           '条件: 成績データが必要です。空の場合は空データの案内を返します。\n'
           '示例: export json',
 'friend_list': '命令: friends\n'
                '说明: maimai NET から登録済みフレンド一覧を表示します。\n'
                '参数: 引数なし: friend list または friends をそのまま送信します。\n'
                '関連: friend-rcd <フレンド番号または名前> [成績画像タイプ] [フィルター] でフレンド成績画像を表示できます。\n'
                '示例: friends',
 'level_rank_list': '命令: <レベルまたは定数> levels\n'
                    '说明: 指定レベルまたは定数の楽曲一覧を表示します。\n'
                    '参数: 必須: <レベルまたは定数>。13、13+、14、13.6 などに対応します。\n'
                    '検索: 整数/+ はレベル、小数は定数の完全一致です。\n'
                    '示例: 13.6 levels\n'
                    '14+ levels',
 'level_rank_progress': '命令: <レベルまたはカテゴリ><評価> prog [-uc|-up|-c]\n'
                        '说明: 指定レベルまたはカテゴリ内の評価目標達成状況を表示します。\n'
                        '参数: 必須: <レベルまたはカテゴリ>。レベルは 11-15、カテゴリは '
                        'vocaloid、touhou、popani、gekichu、game、maimai に対応します。\n'
                        '必須: <評価>。レベル/カテゴリの後に書きます。s、s+、ss、ss+、sss、sss+、fc、fc+、ap、ap+、fdx、fdx+ '
                        'に対応します。\n'
                        '任意: -uc は目標未達成のみ、-up は未プレイのみ、-c は目標達成済みのみを表示します。\n'
                        '形式: レベルは 14sss+ prog のように連結できます。カテゴリは vocaloid sss+ prog '
                        'のように空白区切りを推奨します。\n'
                        '示例: 14sss+ prog\n'
                        '13ap prog -uc\n'
                        'vocaloid sss+ prog\n'
                        'popani ss+ prog -up',
 'level_records': '命令: <レベルまたは定数> records [ページ]\n'
                  '说明: 指定レベルまたは定数の成績リストを表示します。\n'
                  '参数: 必須: <レベルまたは定数>。13、13+、14、13.6 などに対応します。\n'
                  '任意: [ページ]。1 から始まる正整数。省略時は 1 ページ目です。\n'
                  '検索: 整数/+ はレベル、小数は定数の完全一致です。\n'
                  '示例: 13.6 records\n'
                  '14 records 2',
 'maimai_update': '命令: maimai update\n'
                  '说明: maimai NET からプレイ済み楽曲成績を同期します。\n'
                  '参数: 引数なし: maimai update または update をそのまま送信します。\n'
                  '示例: maimai update\n'
                  '注意: SEGA アカウント連携が必要です。',
 'plate': '命令: <プレート名> plate [-uc|-up|-c]\n'
          '说明: プレートや称号系目標の達成状況を表示します。\n'
          '参数: 必須: <プレート名>。plate の前に置きます。例: 真極、檄将。\n'
          '任意: -uc は未完成項目のみ、-up は未プレイ項目のみ、-c は達成済み項目のみを表示します。\n'
          '形式: フィルターは末尾に置きます。省略時は全体の達成状況です。\n'
          '示例: 真極 plate\n'
          '真極 plate -uc',
 'profile': '命令: profile\n'
            '说明: 連携状態、サーバー、言語設定などの JiETNG アカウント情報を表示します。\n'
            '参数: 引数なし: profile をそのまま送信します。\n'
            '制限: 個人情報保護のため個人チャット専用です。\n'
            '示例: profile',
 'random_song': '命令: random [条件]\n'
                '说明: ランダムに 1 曲おすすめします。\n'
                '参数: 任意: [条件]。レベル、定数、譜面種別、難易度などのキーワードを指定できます。\n'
                '形式: 複数条件は空白で区切ります。省略時は全曲からランダムです。\n'
                '示例: random\n'
                'random 13+ dx\n'
                'random 14 mas',
 'ranking': '命令: rank [jp|intl]\n'
            '说明: DX Rating の総合ランキングを表示します。\n'
            '参数: 任意: [サーバー]。jp、intl に対応。省略時はユーザーの連携サーバーを使います。\n'
            '形式: rank の後ろに空白区切りで指定します。\n'
            'Mention: 登録済みユーザーをメンションすると、そのユーザーの総合ランキング上の位置を表示します。相手がメンションでの成績参照を許可している必要があります。\n'
            '示例: rank\n'
            'rank intl',
 'rc': '命令: rc <定数>\n'
       '说明: Rating Composition / レート内訳の情報を検索します。\n'
       '参数: 必須: <定数>。1.0 から 15.0 までの数値です。\n'
       '形式: 13、13.6、14.9 のような整数または小数に対応します。\n'
       '制限: 1.0-15.0 の範囲外、または数値化できない入力はエラーです。\n'
       '示例: rc 14\n'
       'rc 13.6',
 'rebind': '命令: rebind\n'
           '说明: 連携済み SEGA アカウント情報を更新する編集 URL を返します。\n'
           '参数: 引数なし: rebind をそのまま送信します。\n'
           '条件: SEGA アカウント連携済みである必要があります。\n'
           '制限: 個人チャット専用です。\n'
           '示例: rebind',
 'refreshmenu': '命令: refreshmenu\n'
                '说明: 現在の連携状態に応じて送信者本人の LINE リッチメニューを再連携します。\n'
                '参数: 引数なし: refreshmenu をそのまま送信します。\n'
                '制限: 送信者本人の Rich Menu のみに影響します。\n'
                '示例: refreshmenu',
 'score_recognition': '命令: rec\n'
                      '说明: リザルト全体を認識します。完全に検証できた場合は生成画像を返し、修正が必要な場合はコピー可能な修正カードを返します。\n'
                      '参数: リザルト画像への返信が必須で、追加引数は使用できません。\n'
                      '示例: rec',
 'search_by_artist': '命令: artist <キーワード> [ページ]\n'
                     '说明: アーティスト名で楽曲を検索します。\n'
                     '参数: 必須: <キーワード>。artist 後の文字列をアーティスト名に部分一致で検索します。\n'
                     '任意: [ページ]。1 から始まる正整数。末尾に指定します。\n'
                     '制限: グループでの連投防止のため個人チャット専用です。\n'
                     '示例: artist Nanahira\n'
                     'artist sasakure 2',
 'search_by_bpm': '命令: bpm <BPMまたは範囲> [ページ]\n'
                  '说明: BPM の完全一致または範囲で楽曲を検索します。\n'
                  '参数: 必須: <BPMまたは範囲>。単一値、ハイフン範囲、空白区切り範囲に対応します。\n'
                  '単一値: bpm 180 は BPM 180 の完全一致です。\n'
                  '範囲: bpm 0-120 または bpm 120 180 は両端を含む範囲検索です。端点 0 も使用できます。\n'
                  '任意: [ページ]。1 から始まる正整数。末尾に指定します。\n'
                  '制限: 個人チャット専用です。\n'
                  '示例: bpm 180\n'
                  'bpm 0-120\n'
                  'bpm 120 180 2',
 'search_by_designer': '命令: designer <キーワード> [ページ]\n'
                       '说明: 譜面制作者名で楽曲を検索します。\n'
                       '参数: 必須: <キーワード>。designer 後の文字列を各譜面の noteDesigner に対して検索します。\n'
                       '任意: [ページ]。1 から始まる正整数。末尾に指定します。\n'
                       '制限: グループでの連投防止のため個人チャット専用です。\n'
                       '示例: designer Jack\n'
                       'designer 譜面 2',
 'settings': '命令: settings\n'
             '说明: タイムゾーン、言語、背景画像、プライバシーなどを変更する設定 URL を返します。\n'
             '参数: 引数なし: settings をそのまま送信します。\n'
             '制限: 個人チャット専用です。\n'
             '示例: settings',
 'song_info': '命令: <曲名> info\n'
              '说明: 楽曲情報、譜面情報、BPM を表示します。リザルト画像に返信して info を送ると、曲名を自動認識できます。\n'
              '参数: テキスト検索では正式名・部分一致・別名を指定します。画像への返信時は曲名の入力は不要です。\n'
              '検索: 複数候補がある場合は選択候補を返します。\n'
              '示例: ヒバナ info\n'
              '（画像に返信）info',
 'song_record': '命令: <曲名> record\n'
                '说明: 曲名または別名で自分の単曲成績を検索します。\n'
                '参数: 必須: <曲名>。record の前に置き、正式名・部分一致・別名を指定できます。\n'
                '検索: 複数候補がある場合は選択候補を返します。\n'
                '示例: ヒバナ record',
 'status': '命令: status\n'
           '说明: 稼働時間、キュー、システムリソースなど Bot の状態を表示します。\n'
           '参数: 引数なし: status をそのまま送信します。\n'
           '示例: status',
 'unbind_prompt': '命令: unbind\n'
                  '说明: 一回限りの SEGA アカウント連携解除 URL を返します。ブラウザで確認した後に削除されます。\n'
                  '参数: 引数なし: unbind をそのまま送信します。\n'
                  '条件: SEGA アカウント、または Import Token アカウント連携済みである必要があります。\n'
                  '制限: 個人チャット専用です。\n'
                  '示例: unbind',
 'version_songs': '命令: <バージョン名> ver\n'
                  '说明: 指定バージョンの楽曲一覧を表示します。\n'
                  '参数: 必須: <バージョン名>。ver の前に置き、正式名または認識可能な略称を指定します。\n'
                  '形式: バージョン名に空白を含められます。ver より前の全体を検索語として扱います。\n'
                  '示例: BUDDiES ver\n'
                  'PRiSM PLUS ver'}
# END COMMAND HELP

# BEGIN TEMPLATE TEXTS
TEXTS["web"]["bind"] = {
    "pageTitle": "SEGA アカウント連携 | JiETNG",
    "pageTitleRebind": "アカウント設定の編集 | JiETNG",
    "heading": "SEGA アカウント連携",
    "headingRebind": "アカウント設定の編集",
    "labelSegaid": "セガID",
    "labelPassword": "セガパスワード",
    "labelVersion": "バージョン",
    "optJp": "日本版",
    "optIntl": "海外版",
    "labelTimezone": "タイムゾーン",
    "labelLanguage": "言語",
    "languagePlatformHint": "言語設定は LINE 以外の外部プラットフォームには反映されない場合があります。",
    "labelBindType": "連携方式",
    "optBindSega": "SEGA アカウント",
    "optBindImport": "Import Token のみ",
    "bindTypeImportHelp": "SEGA ID を保存せず、書き出しツールから成績をアップロードします。",
    "submitBtn": "連携",
    "submitBtnImport": "Tokenを生成",
    "submitBtnRebind": "更新",
    "noticeTitle": "ご利用に関するご注意",
    "aimeModalTitle": "Aime を選択",
    "aimeModalDescription": "連携するアカウントを選択してください。",
    "aimeConfirm": "確定",
    "aimeFallbackName": "Aime アカウント",
    "ratingLabel": "Rating",
    "trophyLabel": "称号",
    "accountListError": "アカウント一覧を取得できませんでした。"
}
TEXTS["web"]["bind_notice_html"] = "ご入力いただいた情報はすべて暗号化された形式で安全に保存され、第三者に提供されることはありません。<br><br>ただし、本サービスは個人によって運営されており、公式な保証やサポートは提供されておりません。本サービスの性質上、セキュリティや運用方針に不安がある場合は、利用をお控えいただくようお願いいたします。情報提供はあくまでご自身の判断と責任にてお願いいたします。"
TEXTS["web"]["settings"] = {
    "pageTitle": "設定 | JiETNG",
    "heading": "設定",
    "labelLanguage": "言語",
    "languagePlatformHint": "言語設定は LINE 以外の外部プラットフォームには反映されない場合があります。",
    "labelTimezone": "タイムゾーン",
    "skinSection": "スキンと背景",
    "labelSkin": "スキン",
    "skinUsesBackground": "背景画像を使用",
    "skinNoBackground": "背景画像なし",
    "skinBackgroundHint": "下の背景画像・ぼかし・オーバーレイ設定を使用します。背景をオフにすると既定の背景色になります。",
    "skinNoBackgroundHint": "このスキンは背景画像を使用しません。背景設定は保持され、切り替えると再利用できます。",
    "labelBgEnabled": "背景画像",
    "privacyPanelTitle": "プライバシー設定",
    "rankingPanelTitle": "ランキング設定",
    "labelMentionScoreQuery": "メンションでの成績参照を許可",
    "metaMentionScoreQuery": "有効にすると、他のユーザーが LINE メンションであなたの成績画像や進捗を表示できます。",
    "labelGlobalRanking": "総合ランキングに参加",
    "metaGlobalRanking": "rank / ranking の総合ランキングに表示されます。",
    "labelBgBlur": "背景ぼかし",
    "labelBgOverlay": "背景フェード",
    "bgHint": "選択しない場合、すべての背景からランダムに選ばれます。",
    "sectionCustomBg": "カスタム背景",
    "customBgHint": "自分だけの背景画像をアップロードできます（2枚まで、各5MB以下）。",
    "labelCustomBg": "画像を選択",
    "uploadSub": "PNG / JPG / JPEG / WebP（5MB以下）",
    "uploadBtn": "アップロード",
    "uploadFailed": "アップロードに失敗しました。",
    "deleteCustomBgBtn": "削除",
    "deleteCustomBgConfirm": "カスタム背景を削除しますか？",
    "deleteAllCustomBgBtn": "すべて削除",
    "deleteAllCustomBgConfirm": "カスタム背景をすべて削除しますか？",
    "submitBtn": "保存",
    "importTokenTitle": "成績インポートToken",
    "importTokenHelp": "外部ツールから加工済みの成績JSONをJiETNGへアップロードするためのTokenです。",
    "importTokenCreate": "Tokenを生成",
    "importTokenNoteLabel": "Token名",
    "importTokenNotePlaceholder": "例：ツール",
    "importTokenNoteRequired": "Token名を入力してください。",
    "importTokenResultTitle": "Token（今回のみ表示）",
    "importTokenCopy": "コピー",
    "importTokenCopied": "コピーしました",
    "importTokenEmpty": "まだTokenはありません。",
    "importTokenRevoke": "撤廃",
    "importTokenRevoked": "Revoked",
    "importTokenDelete": "削除",
    "importTokenCreateError": "Tokenの生成に失敗しました。",
    "importTokenRevokeConfirm": "このインポートTokenを撤廃しますか？",
    "importTokenRevokeError": "撤廃に失敗しました。",
    "importTokenDeleteConfirm": "この撤廃済みTokenを削除しますか？",
    "importTokenDeleteError": "削除に失敗しました。"
}
TEXTS["web"]["settings_permissions"] = {
    "panelTitle": "アクセス権限の管理",
    "ownerLabel": "作成者",
    "revokeBtn": "撤廃",
    "revokeConfirm": "このサービスのアクセス権限を取り消しますか？",
    "revokeError": "取り消しに失敗しました。もう一度お試しください。"
}
# END TEMPLATE TEXTS

# BEGIN GENERATED MESSAGE TEXTS
MESSAGE_TEXTS = {'access_error_text': '🙇 今めっちゃアクセス多いんだよね…ちょっと後でもう一回試してみて！',
 'already_bound_text': 'SEGA アカウントはすでに連携済みです。\n'
                       '\n'
                       'パスワード、バージョン、Aime を変更する場合は rebind を使用してください。\n'
                       'タイムゾーン、言語、背景画像、プライバシー設定は settings から変更できます。\n'
                       '別のアカウントを連携する場合は、先に unbind で連携を解除してください。',
 'bind_group_warning_text': 'bind は個人チャット専用です。ボットに直接メッセージを送信してください。',
 'calc_button_text': 'ノーツ計算',
 'calc_flex_text': {'alt_multi': 'ノーツ計算結果',
                    'alt_single': 'ノーツ計算結果',
                    'max_tap_great': '最大 {count} TAP GREAT',
                    'subtitle': 'ノーツ計算',
                    'title_distribution': 'ノーツ分布'},
 'cannot_do_for_others_text': 'このコマンドは自分のアカウントにのみ使用できます。',
 'dxdata_current_stats_text': '📈 現在: 楽曲{songs}首 / 譜面{sheets}個',
 'dxdata_fetch_failed_text': '❌ データ取得失敗！',
 'dxdata_first_update_text': '(初回更新完了！)',
 'dxdata_initial_stats_sheets_text': '📊 譜面: {count}個',
 'dxdata_initial_stats_songs_text': '📈 楽曲: {count}首',
 'dxdata_last_update_text': '📅 前回更新: {timestamp}',
 'dxdata_new_sheets_text': '📊 新譜面: +{count}個',
 'dxdata_new_songs_text': '🎵 新曲: +{count}首',
 'dxdata_no_new_sheets_text': '📊 新譜面: なし',
 'dxdata_no_new_songs_text': '🎵 新曲: なし',
 'dxdata_parse_failed_text': '❌ データ解析失敗！',
 'dxdata_sheets_decreased_text': '📊 譜面: {count}個',
 'dxdata_songs_decreased_text': '🎵 楽曲: {count}首',
 'dxdata_update_success_text': '✅ Dxdata Updated!',
 'export_alt_text': '成績データを書き出しました',
 'export_empty_text': 'まだ書き出せる成績データがありません。『maimai update』で更新してから試してください。',
 'export_failed_text': '成績データの書き出しに失敗しました。しばらくしてからもう一度お試しください。',
 'export_flex_button_text': 'ダウンロード',
 'export_flex_copy_button_text': 'リンクをコピー',
 'export_flex_footnote_text': 'リンクは {ttl} 分後に自動で失効します',
 'export_flex_summary_text': 'Best: {best} 件 ・ Recent: {recent} 件\nファイル形式: {fmt}（{size_kb} KB）',
 'export_flex_title_text': '成績データを書き出しました',
 'friend_error_text': 'お気に入りフレンドがまだ登録されていません。',
 'friend_list_alt_text': 'お気に入りフレンド',
 'friend_rcd_error_text': '指定されたユーザーはフレンドに登録されていません。',
 'friend_rcd_group_warning_text': 'フレンド成績コマンドは個人チャット専用です。ボットに直接メッセージを送信してください。',
 'friend_rcd_text': '{name} のデータ',
 'info_error_text': 'maimai プロフィールがまだ保存されていません。『maimai update』で更新してから試してください。',
 'input_error_text': 'コマンドを認識できませんでした。入力内容を確認してください。',
 'level_not_supported_text': 'このレベルの定数表はサポートされていません。\nレベル12以上のみ対応しています。',
 'level_record_not_found_text': '指定されたレベル「{level}」の{page}ページ目の譜面記録は存在しないかも...',
 'level_record_page_hint_text': 'これは{page}ページ目のデータだよ！',
 'maintenance_error_text': '🔧 あれ？公式サイトがメンテナンス中みたい！\n夜間とかメンテナンス時間はアクセスできないから、またあとで試してみてね〜',
 'mention_error_text': 'メンションされたユーザーはまだ JiETNG に登録されていません。',
 'mention_not_allowed_text': 'メンションされたユーザーは、メンションによる成績参照を無効にしています。',
 'mention_no_matching_data_text': 'メンションされたユーザーには、条件に合う成績データがありません。',
 'mention_record_error_text': 'メンションされたユーザーには、まだ maimai 成績データがありません。',
 'nearby_stores_alt_text': '最寄りの maimai 設置店舗',
 'no_matching_data_text': '条件に合う成績データが見つかりませんでした。',
 'notice_header_text': '📢 お知らせ',
 'perm_request_accept_button_text': '承認',
 'perm_request_accept_success_text': '✅ アクセス権限リクエストを承認しました！\n'
                                     '\n'
                                     'Token ID: {token_id}\n'
                                     '申請者: {requester_name}\n'
                                     '\n'
                                     'このトークンはあなたのアカウント情報にアクセスできるようになりました。',
 'perm_request_already_processed_text': 'このリクエストはすでに処理されています。',
 'perm_request_notification_alt_text': '{count} 件のアクセス権限リクエストがあります',
 'perm_request_notification_subtitle_text': '{count} 件の新しいリクエスト',
 'perm_request_notification_title_text': 'アクセス権限リクエスト • Permission Requests',
 'perm_request_reject_button_text': '拒否',
 'perm_request_reject_success_text': '✅ アクセス権限リクエストを拒否しました。\n'
                                     '\n'
                                     'Token ID: {token_id}\n'
                                     '申請者: {requester_name}',
 'plate_error_text': '指定されたプレートが見つかりませんでした。',
 'private_info_group_warning_text': '個人情報コマンドは個人チャット専用です。ボットに直接メッセージを送信してください。',
 'quick_reply_labels': {'account_bind': 'アカウント連携',
                        'all_best_50': 'All Best 50',
                        'maimai_update': 'maimai update',
                        'recent_50': 'Recent 50',
                        'retry': 'もう一回',
                        'support': 'サポート'},
 'ranking_alt_text': 'Rating ランキング',
 'ranking_no_data_text': 'ランキングデータがありません。',
 'ranking_title_text': 'Rating ランキング',
 'rate_limit_msg_text': '🔄 現在システムが混み合っています。\nしばらくしてからもう一度お試しください。',
 'rebind_button_text': 'アカウントを編集',
 'rebind_description_text': '連携済み SEGA アカウントのパスワード、サーバー、Aime を変更します。',
 'rebind_group_warning_text': 'rebind は個人チャット専用です。ボットに直接メッセージを送信してください。',
 'rebind_msg_text': '✅ SEGA アカウント情報を更新しました。',
 'rebind_not_bound_text': 'SEGA アカウントがまだ連携されていません。先に bind で連携してください。',
 'rebind_title_alt_text': 'アカウント設定の編集',
 'record_error_text': 'まだ maimai 成績データがありません。『maimai update』で更新してから試してください。',
 'search_group_warning_text': 'artist / designer / bpm 検索は個人チャット専用です。',
 'sega_bind_alt_text': 'SEGA アカウント連携',
 'sega_bind_button_text': '連携を開始',
 'sega_bind_description_text': '初回連携用の SEGA アカウント連携ページを開きます。',
 'sega_bind_title_text': 'SEGA アカウント連携',
 'segaid_error_text': 'SEGAアカウントまだ連携してないよね？',
 'settings_button_text': '設定を開く',
 'settings_description_text': 'タイムゾーン、言語、背景画像、プライバシー設定を変更します。',
 'settings_group_warning_text': 'settings は個人チャット専用です。ボットに直接メッセージを送信してください。',
 'settings_title_alt_text': '個人設定',
 'song_error_text': '条件に合う楽曲が見つかりませんでした。',
 'song_info_alt_text': '楽曲情報',
 'song_record_alt_text': '楽曲成績',
 'store_error_text': '🥹 周辺の設置店舗がないね',
 'system_error_text': '😵 システムエラーが発生しました…管理者に通知済みです。しばらくしてから再度お試しください。',
 'unbind_button_text': '解除ページを開く',
 'unbind_description_text': '連携済み SEGA アカウントと保存済み成績データをブラウザ内で確認して削除します。',
 'unbind_group_warning_text': 'unbind は個人チャット専用です。ボットに直接メッセージを送信してください。',
 'unbind_title_alt_text': 'アカウント連携解除',
 'update_result_flex_text': {'alt_text_error': '成績更新エラー',
                             'alt_text_success': '成績更新完了',
                             'elapsed_time_label': '処理時間',
                             'failed': '失敗',
                             'status_best_records': 'Best 成績',
                             'status_label': '取得できなかった項目',
                             'status_recent_records': 'Recent 成績',
                             'status_user_info': 'プロフィール',
                             'summary_section': '概要',
                             'title_error': '成績更新エラー',
                             'title_success': '成績更新完了',
                             'update_time_label': '更新日時'},
 'user_info_flex_text': {'account_section': 'アカウント',
                         'alt_text': 'ユーザー情報',
                         'copy_id': 'IDをコピー',
                         'intl_server': '海外版',
                         'jp_server': '日本版',
                         'lang_en': '英語',
                         'lang_ja': '日本語',
                         'lang_zh': '中国語',
                         'language_label': '言語',
                         'last_update_label': '最終更新',
                         'name_label': 'プレイヤー名',
                         'not_bound': '未連携',
                         'password_label': 'パスワード',
                         'profile_section': 'プレイ情報',
                         'rating_label': 'レーティング',
                         'sega_id_label': 'SEGA ID',
                         'server_label': 'サーバー',
                         'settings_section': '設定',
                         'title': 'ユーザー情報',
                         'user_id_label': 'LINE ID'},
 'version_error_text': '指定されたバージョンが見つかりませんでした。',
 'view_info_button_text': '楽曲情報を見る',
 'view_record_button_text': 'スコアを見る'}
# END GENERATED MESSAGE TEXTS

TEXTS["messages"] = MESSAGE_TEXTS

TEXTS["images"] = {
    "score": {
        "analysis_title": "スコア解析",
        "type": "種類",
        "subtitle": "判定詳細",
        "judgement": "判定データ",
        "loss": "詳細判定",
        "break": "BREAK 詳細判定",
        "empty": "判定詳細を認識できませんでした。",
        "distribution": '判定分布・失点',
        "cell_legend": '数量 / 合計失点 / 1個あたりの失点',
        "verified": '検証済み',
        "check_required": '要確認',
        "validation_note": '未検証の項目があります。認識された判定を確認してください。',
        "common_total": "通常ノーツ合計",
        "break_total": "BREAK 合計",
    },
    "records": {
        "heading": "プレイ記録",
        "tracks": "曲",
        "play_count": "プレイ回数",
        "avg_level": "平均レベル",
        "avg_achievement": "平均達成率",
        "avg_rating": "平均レーティング",
    },
    "progress": {
        "completed": "完了",
        "incomplete": "未完了",
        "unplayed": "未プレイ",
        "total": "総計",
        "progress_suffix": "目標",
        "level_list_suffix": "レベル一覧",
    },
    "song": {
        "note_loss": {'type': '種類', 'title': 'ノーツ判定・失点', 'unit': '各数値は 1 個あたりの達成率減少量', 'count': '数量', 'tolerance': 'TAP GREAT 許容数', 'max_tap': '最大 {count} 回'},
        "notes_title": "ノーツ内訳",
        "rating_title": "譜面作者・ランク別 Rating",
        "rating_note": "各ランクの最低達成率で算出した Rating（AP ボーナスを除く）",
        "records": "プレイ記録",
        "unplayed": "未プレイ",
        "artist": "アーティスト", "category": "カテゴリ", "bpm": "BPM", "version": "バージョン",
        "unknown_title": "タイトル不明", "unknown_artist": "アーティスト不明", "unknown_category": "カテゴリ不明",
        "headers": {
            "chart_type": "譜面種類", "level": "レベル", "designer": "ノーツデザイナー",
            "total": "合計", "tap": "TAP", "hold": "HOLD", "slide": "SLIDE",
            "touch": "TOUCH", "break": "BREAK", "jp": "国内", "intl": "海外", "usa": "USA",
        },
    },
}
