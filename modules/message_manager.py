from modules.config_loader import SUPPORT_PAGE, USERS
from linebot.v3.messaging import (
    TextMessage,
    QuickReply,
    QuickReplyItem,
    MessageAction,
    URIAction,
    FlexMessage,
    FlexContainer
)

from linebot.v3.messaging.models import (
    FlexBubble,
    FlexBox,
    FlexText,
    FlexButton,
    FlexSeparator
)

# ============================================================
# 多语言辅助函数 / Multilingual Helper Functions
# ============================================================

def get_user_language(user_id):
    """
    获取用户语言设置

    Args:
        user_id: 用户ID

    Returns:
        str: 语言代码 ('ja', 'en', 'zh')，默认为 'ja'
    """
    if user_id and user_id in USERS:
        return USERS[user_id].get('language', 'ja')
    return 'ja'

def get_multilingual_text(message_dict, user_id=None, language=None):
    """
    根据用户语言获取对应的文本

    Args:
        message_dict: 多语言消息字典 {'ja': '...', 'en': '...', 'zh': '...'}
        user_id: 用户ID（可选）
        language: 直接指定语言（可选，优先级高于user_id）

    Returns:
        str: 对应语言的文本，如果不存在则返回日语文本
    """
    if not isinstance(message_dict, dict):
        return message_dict

    if language is None:
        language = get_user_language(user_id) if user_id else 'ja'

    return message_dict.get(language, message_dict.get('ja', ''))

# ============================================================
# アカウント連携関連 / Account Binding
# ============================================================

bind_msg_text = {
    "ja": "✅ SEGA IDの連携できたよ！",
    "en": "✅ SEGA ID linked successfully!",
    "zh": "✅ SEGA ID 绑定成功！"
}

unbind_msg_text = {
    "ja": "✅ SEGA IDの連携を解除したよ！",
    "en": "✅ SEGA ID unlinked successfully!",
    "zh": "✅ SEGA ID 解绑成功！"
}

# ============================================================
# データ更新関連 / Data Update
# ============================================================

update_over_text = {
    "ja": "✅ アップデート完了！",
    "en": "✅ Update completed!",
    "zh": "✅ 更新完成！"
}

update_error_text = {
    "ja": "❗️あれ？アップデート中にエラーが出ちゃった！",
    "en": "❗️Oops! An error occurred during the update!",
    "zh": "❗️哎呀？更新过程中出现错误了！"
}

# ============================================================
# エラーメッセージ / Error Messages
# ============================================================

segaid_error_text = {
    "ja": "SEGAアカウントまだ連携してないよね？",
    "en": "You haven't linked your SEGA account yet, right?",
    "zh": "你还没有绑定 SEGA 账号吧？"
}

record_error_text = {
    "ja": "maimaiレコードまだアップデートしてないみたい！",
    "en": "Looks like you haven't updated your maimai records yet!",
    "zh": "看起来你还没有更新 maimai 记录！"
}

info_error_text = {
    "ja": "ごめん！maimai個人情報まだメモしてないわ！",
    "en": "Sorry! Your maimai profile hasn't been saved yet!",
    "zh": "抱歉！你的 maimai 个人信息还没有保存！"
}

access_error_text = {
    "ja": "🙇 今めっちゃアクセス多いんだよね…ちょっと後でもう一回試してみて！",
    "en": "🙇 There's a lot of traffic right now... Please try again later!",
    "zh": "🙇 现在访问量很大…请稍后再试！"
}

system_error_text = {
    "ja": "😵 システムエラーが発生しました…管理者に通知済みです。しばらくしてから再度お試しください。",
    "en": "😵 A system error occurred... The administrator has been notified. Please try again later.",
    "zh": "😵 发生系统错误…已通知管理员。请稍后再试。"
}

input_error_text = {
    "ja": "全然わかんないなー",
    "en": "I don't understand what you mean...",
    "zh": "我完全不明白你的意思..."
}

picture_error_text = {
    "ja": "画像処理しっぱい〜〜",
    "en": "Image processing failed~~",
    "zh": "图片处理失败~~"
}

song_error_text = {
    "ja": "条件に合う楽曲がないかも...",
    "en": "No songs match the criteria...",
    "zh": "没有符合条件的歌曲..."
}

level_not_supported_text = {
    "ja": "このレベルの定数表はサポートされていません。\nレベル12以上のみ対応しています。",
    "en": "This level constant table is not supported.\nOnly levels 12 and above are available.",
    "zh": "不支持该等级的定数表。\n仅支持12级及以上。"
}

cache_not_found_text = {
    "ja": "定数表のキャッシュが見つかりません。\n管理者に問い合わせてください。",
    "en": "Level chart cache not found.\nPlease contact the administrator.",
    "zh": "定数表缓存不存在。\n请联系管理员。"
}

plate_error_text = {
    "ja": "そのプレートがわからないね...",
    "en": "I don't recognize that plate...",
    "zh": "我不认识那个牌子..."
}

version_error_text = {
    "ja": "そのバージョンがわからないね...",
    "en": "I don't recognize that version...",
    "zh": "我不认识那个版本..."
}

store_error_text = {
    "ja": "🥹 周辺の設置店舗がないね",
    "en": "🥹 No nearby arcades found",
    "zh": "🥹 附近没有找到游戏厅"
}

qrcode_error_text = {
    "ja": "ん〜？よくわかんない写真だね",
    "en": "Hmm? I can't recognize this image",
    "zh": "嗯~？我看不懂这张图片"
}

rate_limit_msg_text = {
    "ja": "⏳ ちょっと待ってー！今同じリクエスト処理中だから！\n終わるまでちょっと待っててね〜",
    "en": "⏳ Wait a moment! I'm still processing the same request!\nPlease wait until it's done~",
    "zh": "⏳ 稍等一下！我正在处理相同的请求！\n等我完成再试试吧~"
}

maintenance_error_text = {
    "ja": "🔧 あれ？公式サイトがメンテナンス中みたい！\n夜間とかメンテナンス時間はアクセスできないから、またあとで試してみてね〜",
    "en": "🔧 Oh? The official site seems to be under maintenance!\nIt's not accessible during maintenance hours, so please try again later~",
    "zh": "🔧 咦？官方网站好像在维护中！\n维护时间无法访问，请稍后再试~"
}

# ============================================================
# フレンド関連 / Friend Messages
# ============================================================

friend_error_text = {
    "ja": "お気に入りにフレンド登録してないみたいだよ？",
    "en": "Looks like you haven't registered any friends in favorites?",
    "zh": "看起来你还没有在收藏中注册好友？"
}

friend_rcd_error_text = {
    "ja": "この人フレンドじゃないかも！",
    "en": "This person might not be your friend!",
    "zh": "这个人可能不是你的好友！"
}

# 権限リクエスト関連 / Permission Request Related
perm_request_sent_text = {
    "ja": "✅ アクセス権限のリクエストを送信しました！\n「{name}」さんが承認するまでお待ちください〜",
    "en": "✅ Access permission request sent!\nPlease wait for '{name}' to approve~",
    "zh": "✅ 已发送访问权限请求！\n请等待「{name}」批准~"
}

perm_request_already_sent_text = {
    "ja": "もうリクエスト送ったよ〜！承認を待っててね〜",
    "en": "You've already sent a request~! Wait for approval~",
    "zh": "你已经发送过请求了~！等待批准吧~"
}

perm_request_already_granted_text = {
    "ja": "「{name}」さんへのアクセス権限はもう持ってるよ！",
    "en": "You already have access permission to '{name}'!",
    "zh": "你已经拥有「{name}」的访问权限了！"
}

perm_request_accepted_text = {
    "ja": "✅ 「{name}」さん（{requester_name}）からのアクセス権限リクエストを承認しました！",
    "en": "✅ Access permission granted to '{name}' ({requester_name})!",
    "zh": "✅ 已批准来自「{name}」（{requester_name}）的访问权限请求！"
}

perm_request_rejected_text = {
    "ja": "「{name}」さん（{requester_name}）からのアクセス権限リクエストを拒否しました",
    "en": "Access permission request from '{name}' ({requester_name}) rejected",
    "zh": "已拒绝来自「{name}」（{requester_name}）的访问权限请求"
}

perm_request_not_found_text = {
    "ja": "あれ？そのリクエストもう処理しちゃったかも",
    "en": "Hmm? That request might have been processed already",
    "zh": "咦？那个请求可能已经处理过了"
}

# 权限请求通知相关文本
perm_request_notification_title_text = {
    "ja": "アクセス権限リクエスト • Permission Requests",
    "en": "Access Permission Requests",
    "zh": "访问权限请求"
}

perm_request_notification_subtitle_text = {
    "ja": "{count} 件の新しいリクエスト",
    "en": "{count} new requests",  # 简化处理，统一使用复数
    "zh": "{count} 个新请求"
}

perm_request_accept_button_text = {
    "ja": "承認",
    "en": "Accept",
    "zh": "接受"
}

perm_request_reject_button_text = {
    "ja": "拒否",
    "en": "Reject",
    "zh": "拒绝"
}

perm_request_notification_alt_text = {
    "ja": "{count} 件のアクセス権限リクエストがあります",
    "en": "You have {count} access permission request(s)",
    "zh": "你有 {count} 个访问权限请求"
}

perm_request_accept_success_text = {
    "ja": "✅ アクセス権限リクエストを承認しました！\n\nToken ID: {token_id}\n申請者: {requester_name}\n\nこのトークンはあなたのアカウント情報にアクセスできるようになりました。",
    "en": "✅ Access permission request accepted!\n\nToken ID: {token_id}\nRequester: {requester_name}\n\nThis token can now access your account information.",
    "zh": "✅ 已接受访问权限请求！\n\nToken ID: {token_id}\n申请者: {requester_name}\n\n该 token 现在可以访问你的账户信息了。"
}

perm_request_reject_success_text = {
    "ja": "✅ アクセス権限リクエストを拒否しました。\n\nToken ID: {token_id}\n申請者: {requester_name}",
    "en": "✅ Access permission request rejected.\n\nToken ID: {token_id}\nRequester: {requester_name}",
    "zh": "✅ 已拒绝访问权限请求。\n\nToken ID: {token_id}\n申请者: {requester_name}"
}

perm_request_error_text = {
    "ja": "❌ エラー: {error}\n{message}",
    "en": "❌ Error: {error}\n{message}",
    "zh": "❌ 错误: {error}\n{message}"
}

# ============================================================
# 管理者通知 / Admin Notifications
# ============================================================

notice_upload_text = {
    "ja": "✅ Notice uploaded",
    "en": "✅ Notice uploaded",
    "zh": "✅ 公告已上传"
}

dxdata_update_text = {
    "ja": "✅ Dxdata Updated!",
    "en": "✅ Dxdata Updated!",
    "zh": "✅ Dxdata 已更新！"
}

# ============================================================
# その他 / Others
# ============================================================

# 临时使用好友账号
friend_use_once_text = {
    "ja": "これからは一回だけ「{name}」さんとしてレコードをチェックしていきますよ！\n色んなコマンドを使ってみてね！",
    "en": "Checking records as '{name}' just once!\nTry various commands!",
    "zh": "这次将作为「{name}」查看记录！\n试试各种命令吧！"
}

# 好友 Best 50 标题
friend_best50_title_text = {
    "ja": "「{name}」さんの Best 50",
    "en": "{name}'s Best 50",
    "zh": "「{name}」的 Best 50"
}

# 指定レベルのレコードなし
level_record_not_found_text = {
    "ja": "指定されたレベル「{level}」の{page}ページ目の譜面記録は存在しないかも...",
    "en": "No records found for level '{level}' page {page}...",
    "zh": "指定等级「{level}」的第 {page} 页记录可能不存在..."
}

# レベルレコード追加ページの説明
level_record_page_hint_text = {
    "ja": "これは{page}ページ目のデータだよ！",
    "en": "This is page {page} data!",
    "zh": "这是第 {page} 页的数据！"
}

# Dxdata 更新通知（管理员）
dxdata_update_notification_text = {
    "ja": "📢 Dxdata 更新通知\n\n{message}",
    "en": "📢 Dxdata Update Notification\n\n{message}",
    "zh": "📢 Dxdata 更新通知\n\n{message}"
}

# Dxdata 更新成功消息组件
dxdata_update_success_text = {
    "ja": "✅ Dxdata Updated!",
    "en": "✅ Dxdata Updated!",
    "zh": "✅ Dxdata 更新成功！"
}

dxdata_new_songs_text = {
    "ja": "🎵 新曲: +{count}首",
    "en": "🎵 New Songs: +{count}",
    "zh": "🎵 新增歌曲: +{count}首"
}

dxdata_songs_decreased_text = {
    "ja": "🎵 楽曲: {count}首",
    "en": "🎵 Songs: {count}",
    "zh": "🎵 歌曲: {count}首"
}

dxdata_no_new_songs_text = {
    "ja": "🎵 新曲: なし",
    "en": "🎵 New Songs: None",
    "zh": "🎵 新增歌曲: 无"
}

dxdata_new_sheets_text = {
    "ja": "📊 新譜面: +{count}個",
    "en": "📊 New Charts: +{count}",
    "zh": "📊 新增谱面: +{count}个"
}

dxdata_sheets_decreased_text = {
    "ja": "📊 譜面: {count}個",
    "en": "📊 Charts: {count}",
    "zh": "📊 谱面: {count}个"
}

dxdata_no_new_sheets_text = {
    "ja": "📊 新譜面: なし",
    "en": "📊 New Charts: None",
    "zh": "📊 新增谱面: 无"
}

dxdata_last_update_text = {
    "ja": "📅 前回更新: {timestamp}",
    "en": "📅 Last Update: {timestamp}",
    "zh": "📅 上次更新: {timestamp}"
}

dxdata_current_stats_text = {
    "ja": "📈 現在: 楽曲{songs}首 / 譜面{sheets}個",
    "en": "📈 Current: {songs} Songs / {sheets} Charts",
    "zh": "📈 当前: {songs}首歌曲 / {sheets}个谱面"
}

dxdata_first_update_text = {
    "ja": "(初回更新完了！)",
    "en": "(Initial update complete!)",
    "zh": "(首次更新完成！)"
}

dxdata_fetch_failed_text = {
    "ja": "❌ データ取得失敗！",
    "en": "❌ Failed to fetch data!",
    "zh": "❌ 数据获取失败！"
}

dxdata_parse_failed_text = {
    "ja": "❌ データ解析失敗！",
    "en": "❌ Failed to parse data!",
    "zh": "❌ 数据解析失败！"
}

dxdata_initial_stats_songs_text = {
    "ja": "📈 楽曲: {count}首",
    "en": "📈 Songs: {count}",
    "zh": "📈 歌曲: {count}首"
}

dxdata_initial_stats_sheets_text = {
    "ja": "📊 譜面: {count}個",
    "en": "📊 Charts: {count}",
    "zh": "📊 谱面: {count}个"
}

# 定数列表提示消息
level_list_hint_text = {
    "ja": "💡 より詳細な定数検索は https://dxrating.net をご利用ください！",
    "en": "💡 For more accurate constant queries, visit https://dxrating.net!",
    "zh": "💡 想要更精确的定数查询？请访问 https://dxrating.net！"
}

# SEGA 账号绑定消息
sega_bind_title_text = {
    "ja": "SEGA アカウント連携",
    "en": "SEGA Account Link",
    "zh": "SEGA 账号绑定"
}

sega_bind_description_text = {
    "ja": "SEGA アカウントと連携されます\n有効期限は発行から2分間です",
    "en": "Link your SEGA account\nValid for 2 minutes from issuance",
    "zh": "将绑定你的 SEGA 账号\n有效期为发行后2分钟"
}

sega_bind_button_text = {
    "ja": "押しで連携",
    "en": "Tap to Link",
    "zh": "点击绑定"
}

sega_bind_alt_text = {
    "ja": "SEGA アカウント連携",
    "en": "SEGA Account Link",
    "zh": "SEGA 账号绑定"
}

# 语言选择消息（用于首次绑定时）
# 这些文本在用户未选择语言时显示，所以直接显示三语
language_select_title = "言語選択 / Language Selection / 语言选择"

language_select_description = """言語を選択 / Select language / 选择语言"""

language_button_jp = "🇯🇵 日本語"
language_button_en = "🇺🇸 English"
language_button_zh = "🇨🇳 中文"

language_select_alt = "Language Selection / 言語選択 / 语言选择"

language_set_success_text = {
    "ja": "✅ 言語を日本語に設定しました！\n次に SEGA アカウントを連携してください。\n（既に連携済みの場合は無視してください）",
    "en": "✅ Language set to English!\nNext, please link your SEGA account.\n(If already linked, please ignore this message)",
    "zh": "✅ 语言已设置为中文！\n接下来请绑定你的 SEGA 账号。\n（如已绑定，请忽略此消息）"
}

# 已绑定账号的提示
already_bound_text = {
    "ja": "⚠️ すでに SEGA アカウントが連携されています。\n再度連携する場合は、先に unbind コマンドで連携を解除してください。",
    "en": "⚠️ A SEGA account is already linked.\nTo rebind, please use the unbind command first to unlink your account.",
    "zh": "⚠️ 已绑定 SEGA 账号。\n如需重新绑定，请先使用 unbind 命令解除绑定。"
}

# 公告标题
notice_header_text = {
    "ja": "📢 お知らせ",
    "en": "📢 Notice",
    "zh": "📢 公告"
}

# 开发者 Token 相关消息
devtoken_create_success_text = {
    "ja": "✅ 開発者トークンを作成しました！\n\nToken ID: {token_id}\nToken: {token}\n備考: {note}\n作成日時: {created_at}\n\n⚠️ このトークンは一度しか表示されません。安全な場所に保管してください。",
    "en": "✅ Developer token created successfully!\n\nToken ID: {token_id}\nToken: {token}\nNote: {note}\nCreated: {created_at}\n\n⚠️ This token will only be shown once. Please store it securely.",
    "zh": "✅ 开发者 Token 创建成功！\n\nToken ID: {token_id}\nToken: {token}\n备注: {note}\n创建时间: {created_at}\n\n⚠️ 此 Token 仅显示一次，请妥善保管。"
}

devtoken_create_failed_text = {
    "ja": "❌ トークンの作成に失敗しました。",
    "en": "❌ Failed to create token.",
    "zh": "❌ Token 创建失败。"
}

devtoken_list_header_text = {
    "ja": "📋 開発者トークン一覧",
    "en": "📋 Developer Tokens List",
    "zh": "📋 开发者 Token 列表"
}

devtoken_list_empty_text = {
    "ja": "トークンはまだ作成されていません。",
    "en": "No tokens created yet.",
    "zh": "还没有创建任何 Token。"
}

devtoken_revoke_success_text = {
    "ja": "✅ トークン {token_id} を無効化しました。",
    "en": "✅ Token {token_id} has been revoked.",
    "zh": "✅ 已撤销 Token {token_id}。"
}

devtoken_revoke_failed_text = {
    "ja": "❌ トークン {token_id} が見つかりません。",
    "en": "❌ Token {token_id} not found.",
    "zh": "❌ 找不到 Token {token_id}。"
}

devtoken_info_text = {
    "ja": "📝 トークン詳細情報\n\nToken ID: {token_id}\nToken: {token}\n備考: {note}\n作成者: {created_by}\n作成日時: {created_at}\n最終使用: {last_used}\nステータス: {status}",
    "en": "📝 Token Details\n\nToken ID: {token_id}\nToken: {token}\nNote: {note}\nCreated by: {created_by}\nCreated: {created_at}\nLast used: {last_used}\nStatus: {status}",
    "zh": "📝 Token 详细信息\n\nToken ID: {token_id}\nToken: {token}\n备注: {note}\n创建者: {created_by}\n创建时间: {created_at}\n最后使用: {last_used}\n状态: {status}"
}

devtoken_info_not_found_text = {
    "ja": "❌ トークンが見つかりません。",
    "en": "❌ Token not found.",
    "zh": "❌ 找不到 Token。"
}

devtoken_usage_text = {
    "ja": "📚 開発者トークン管理\n\ndevtoken create <備考> - 新しいトークンを作成\ndevtoken list - トークン一覧を表示\ndevtoken revoke <token_id> - トークンを無効化\ndevtoken info <token_id> - トークンの詳細を表示",
    "en": "📚 Developer Token Management\n\ndevtoken create <note> - Create a new token\ndevtoken list - List all tokens\ndevtoken revoke <token_id> - Revoke a token\ndevtoken info <token_id> - Show token details",
    "zh": "📚 开发者 Token 管理\n\ndevtoken create <备注> - 创建新 Token\ndevtoken list - 显示所有 Token\ndevtoken revoke <token_id> - 撤销 Token\ndevtoken info <token_id> - 显示 Token 详情"
}

# 好友列表 alt_text
friend_list_alt_text = {
    "ja": "フレンドリスト",
    "en": "Friends List",
    "zh": "好友列表"
}

# 附近机厅列表 alt_text
nearby_stores_alt_text = {
    "ja": "最寄りの maimai 設置店舗",
    "en": "Nearby maimai Arcade Stores",
    "zh": "附近的 maimai 机厅"
}

# ============================================================
# Tips メッセージリスト / Tips Messages (多语言支持)
# ============================================================

tip_messages = [
    {
        "ja": "💡 定期的に「maimai update」でデータを更新すると、最新のスコアが反映されるよ！",
        "en": "💡 Regularly use 'maimai update' to sync your latest scores!",
        "zh": "💡 定期使用「maimai update」更新数据，可以反映最新分数！"
    },
    {
        "ja": "💡 フレンド機能を使えば、友達のスコアと比較できるよ！",
        "en": "💡 Use the friend feature to compare scores with your friends!",
        "zh": "💡 使用好友功能可以和朋友比较分数！"
    },
    {
        "ja": "💡 困ったときは「help」コマンドで使い方を確認できるよ！",
        "en": "💡 Type 'help' to learn how to use the bot!",
        "zh": "💡 输入「help」可以查看使用方法！"
    },
    {
        "ja": "💡 「calc [tap] [hold] [slide] ([touch])  [break]」でノーツ数を入力すると、各ノーツの達成率が計算できるよ！",
        "en": "💡 Use 'calc [tap] [hold] [slide] ([touch]) [break]' to calculate achievement rates for each kind of notes!",
        "zh": "💡 使用「calc [tap] [hold] [slide] ([touch]) [break]」输入 note 数量，可以计算各类note对应的达成率！"
    },
    {
        "ja": "💡 位置情報を送信すると、近くのmaimaiゲーセンを検索できるよ！",
        "en": "💡 Send your location to find nearby maimai arcades!",
        "zh": "💡 发送位置信息可以搜索附近的 maimai 游戏厅！"
    },
    {
        "ja": "💡 「ランダム曲」で迷った時にランダムに曲を選んでくれるよ！",
        "en": "💡 Use 'random-song' to randomly pick a song when you can't decide!",
        "zh": "💡 使用「random-song」在犹豫时随机选择歌曲！"
    },
    {
        "ja": "💡 「宴極の達成状況」のように入力すると、プレート達成状況が見られるよ！",
        "en": "💡 Type commands like '宴極 achievement' to view plate achievement status!",
        "zh": "💡 输入「宴極 achievement」等命令可以查看牌子达成情况！"
    },
    {
        "ja": "💡 より詳細な楽曲検索は https://dxrating.net をご利用ください！",
        "en": "💡 For more accurate song queries, visit https://dxrating.net!",
        "zh": "💡 想要更精确的歌曲查询？请访问 https://dxrating.net！"
    },
    {
        "ja": "💡 二次元コードの画像を送信すると、自動的に認識して処理するよ！",
        "en": "💡 Send a QR code image and it will be automatically recognized and processed!",
        "zh": "💡 发送二维码图片可以自动识别并处理！"
    },
    {
        "ja": "💡 ジャケット画像を送信すると、楽曲を認識できるよ！",
        "en": "💡 Send a song jacket image to identify the song!",
        "zh": "💡 发送曲绘图片可以识别歌曲！"
    },
]

donate_message = FlexMessage(
    alt_text="JiETNGを支援 · Support JiETNG",
    contents=FlexBubble(
        body=FlexBox(
            layout="vertical",
            spacing="md",
            paddingAll="16px",
            backgroundColor="#FFFFFF",
            contents=[
                # 标题
                FlexText(
                    text="カヰテーを支援 · Support JiETNG",
                    weight="bold",
                    size="md",
                    wrap=True,
                    align="center",
                    color="#000000"
                ),
                # 多语言说明文本
                FlexText(
                    text=(
                        "一起为 JiETNG 的开发与未来加油！\n"
                        "JiETNG の開発と未来を応援しよう！\n"
                        "Support JiETNG's journey ahead!"
                    ),
                    size="sm",
                    wrap=True,
                    margin="md",
                    align="center",
                    color="#555555"
                ),
                # 按钮容器
                FlexBox(
                    layout="horizontal",
                    spacing="md",
                    margin="lg",
                    justifyContent="center",
                    contents=[
                        # 🇯🇵 Liberapay
                        FlexBox(
                            layout="vertical",
                            flex=0,
                            width="100px",                # ← 按钮宽度
                            height="40px",                # ← 按钮高度
                            cornerRadius="6px",
                            borderColor="#000000",
                            borderWidth="1px",
                            backgroundColor="#FFFFFF",
                            justifyContent="center",
                            alignItems="center",
                            contents=[
                                FlexText(
                                    text="🇯🇵 Liberapay",
                                    weight="bold",
                                    color="#000000",
                                    size="sm",
                                    align="center",
                                    action=URIAction(
                                        label="Liberapay",
                                        uri="https://ja.liberapay.com/_matsuk1/donate?currency=JPY"
                                    )
                                )
                            ]
                        ),
                        # 🇨🇳 爱发电
                        FlexBox(
                            layout="vertical",
                            flex=0,
                            width="100px",
                            height="40px",
                            cornerRadius="6px",
                            borderColor="#000000",
                            borderWidth="1px",
                            backgroundColor="#FFFFFF",
                            justifyContent="center",
                            alignItems="center",
                            contents=[
                                FlexText(
                                    text="🇨🇳 爱发电",
                                    weight="bold",
                                    color="#000000",
                                    size="sm",
                                    align="center",
                                    action=URIAction(
                                        label="爱发电",
                                        uri="https://afdian.com/a/matsuki"
                                    )
                                )
                            ]
                        ),
                    ],
                ),
                # 底部灰分割线
                FlexSeparator(
                    margin="lg",
                    color="#DDDDDD"
                ),
                # 底部说明
                FlexText(
                    text="Thank you for supporting JiETNG 💙",
                    size="xs",
                    color="#666666",
                    align="center",
                    margin="md"
                ),
            ],
        )
    ),
)

# ============================================================
# QuickReply 按钮标签多语言
# ============================================================

quick_reply_labels = {
    "maimai_update": {"ja": "maimai update", "en": "maimai update", "zh": "maimai update"},
    "support": {"ja": "サポート", "en": "Support", "zh": "帮助"},
    "account_bind": {"ja": "アカウント連携", "en": "Link Account", "zh": "绑定账号"},
    "retry": {"ja": "もう一回", "en": "Try Again", "zh": "再试一次"},
    "best_50": {"ja": "Best 50", "en": "Best 50", "zh": "Best 50"},
    "best_100": {"ja": "Best 100", "en": "Best 100", "zh": "Best 100"},
    "all_best_50": {"ja": "All Best 50", "en": "All Best 50", "zh": "All Best 50"},
    "all_best_35": {"ja": "All Best 35", "en": "All Best 35", "zh": "All Best 35"},
    "ap_best_50": {"ja": "All Perfect Best 50", "en": "All Perfect Best 50", "zh": "All Perfect Best 50"},
    "ideal_best_50": {"ja": "Ideal Best 50", "en": "Ideal Best 50", "zh": "Ideal Best 50"},
}

# ============================================================
# 消息生成辅助函数 / Message Generation Helper Functions
# ============================================================

def get_quick_reply_label(key, user_id=None):
    """获取 QuickReply 按钮的多语言标签"""
    if key not in quick_reply_labels:
        return key
    return get_multilingual_text(quick_reply_labels[key], user_id)

def create_text_message(msg_text_dict, user_id=None, quick_reply=None):
    """
    生成多语言 TextMessage

    Args:
        msg_text_dict: 多语言消息字典
        user_id: 用户ID（可选）
        quick_reply: QuickReply 对象（可选）

    Returns:
        TextMessage: 多语言文本消息
    """
    text = get_multilingual_text(msg_text_dict, user_id)
    return TextMessage(text=text, quick_reply=quick_reply)

def get_support_quick_reply(user_id=None):
    """获取「サポート」按钮的 QuickReply"""
    return QuickReply(
        items=[
            QuickReplyItem(action=URIAction(
                label=get_quick_reply_label("support", user_id),
                uri=SUPPORT_PAGE
            ))
        ]
    )

def get_update_quick_reply(user_id=None):
    """获取更新相关的 QuickReply"""
    return QuickReply(
        items=[
            QuickReplyItem(action=MessageAction(
                label=get_quick_reply_label("maimai_update", user_id),
                text="maimai update"
            )),
            QuickReplyItem(action=URIAction(
                label=get_quick_reply_label("support", user_id),
                uri=SUPPORT_PAGE
            ))
        ]
    )

def get_bind_quick_reply(user_id=None):
    """获取绑定相关的 QuickReply"""
    return QuickReply(
        items=[
            QuickReplyItem(action=MessageAction(
                label=get_quick_reply_label("bind", user_id),
                text="bind"
            )),
            QuickReplyItem(action=URIAction(
                label=get_quick_reply_label("support", user_id),
                uri=SUPPORT_PAGE
            ))
        ]
    )

def get_update_over_quick_reply(user_id=None):
    """获取更新完成后的 QuickReply"""
    return QuickReply(
        items=[
            QuickReplyItem(action=MessageAction(
                label=get_quick_reply_label("best_50", user_id),
                text="b50"
            )),
            QuickReplyItem(action=MessageAction(
                label=get_quick_reply_label("all_best_50", user_id),
                text="ab50"
            )),
            QuickReplyItem(action=MessageAction(
                label=get_quick_reply_label("ap_best_50", user_id),
                text="apb50"
            )),
            QuickReplyItem(action=MessageAction(
                label=get_quick_reply_label("ideal_best_50", user_id),
                text="idlb50"
            )),
            QuickReplyItem(action=URIAction(
                label=get_quick_reply_label("support", user_id),
                uri=SUPPORT_PAGE
            ))
        ]
    )

def get_update_error_quick_reply(user_id=None):
    """获取更新错误后的 QuickReply"""
    return QuickReply(
        items=[
            QuickReplyItem(action=MessageAction(
                label=get_quick_reply_label("retry", user_id),
                text="maimai update"
            )),
            QuickReplyItem(action=URIAction(
                label=get_quick_reply_label("support", user_id),
                uri=SUPPORT_PAGE
            ))
        ]
    )

def get_segaid_error_quick_reply(user_id=None):
    """获取 SEGA ID 错误的 QuickReply"""
    return QuickReply(
        items=[
            QuickReplyItem(action=MessageAction(
                label=get_quick_reply_label("account_bind", user_id),
                text="bind"
            )),
            QuickReplyItem(action=URIAction(
                label=get_quick_reply_label("support", user_id),
                uri=SUPPORT_PAGE
            ))
        ]
    )

def get_record_error_quick_reply(user_id=None):
    """获取记录错误的 QuickReply"""
    return QuickReply(
        items=[
            QuickReplyItem(action=MessageAction(
                label=get_quick_reply_label("maimai_update", user_id),
                text="maimai update"
            )),
            QuickReplyItem(action=URIAction(
                label=get_quick_reply_label("support", user_id),
                uri=SUPPORT_PAGE
            ))
        ]
    )

# ============================================================
# 向后兼容的消息生成函数 / Backward Compatible Message Functions
# ============================================================

def bind_msg(user_id=None):
    """生成 SEGA ID 绑定成功消息"""
    return create_text_message(bind_msg_text, user_id, get_update_quick_reply(user_id))

def unbind_msg(user_id=None):
    """生成 SEGA ID 解绑成功消息"""
    return create_text_message(unbind_msg_text, user_id)

def update_over(user_id=None):
    """生成更新完成消息"""
    return create_text_message(update_over_text, user_id, get_update_over_quick_reply(user_id))

def update_error(user_id=None):
    """生成更新错误消息"""
    return create_text_message(update_error_text, user_id, get_update_error_quick_reply(user_id))

def segaid_error(user_id=None):
    """生成 SEGA ID 错误消息"""
    return create_text_message(segaid_error_text, user_id, get_segaid_error_quick_reply(user_id))

def record_error(user_id=None):
    """生成记录错误消息"""
    return create_text_message(record_error_text, user_id, get_record_error_quick_reply(user_id))

def info_error(user_id=None):
    """生成个人信息错误消息"""
    return create_text_message(info_error_text, user_id, get_record_error_quick_reply(user_id))

def access_error(user_id=None):
    """生成访问错误消息"""
    return create_text_message(access_error_text, user_id)

def system_error(user_id=None):
    """生成系统错误消息"""
    return create_text_message(system_error_text, user_id, get_support_quick_reply(user_id))

def input_error(user_id=None):
    """生成输入错误消息"""
    return create_text_message(input_error_text, user_id, get_support_quick_reply(user_id))

def picture_error(user_id=None):
    """生成图片错误消息"""
    return create_text_message(picture_error_text, user_id, get_support_quick_reply(user_id))

def song_error(user_id=None):
    """生成歌曲错误消息"""
    return create_text_message(song_error_text, user_id, get_support_quick_reply(user_id))

def level_not_supported(user_id=None):
    """生成等级不支持消息"""
    return create_text_message(level_not_supported_text, user_id, get_support_quick_reply(user_id))

def cache_not_found(user_id=None):
    """生成缓存不存在消息"""
    return create_text_message(cache_not_found_text, user_id, get_support_quick_reply(user_id))

def plate_error(user_id=None):
    """生成牌子错误消息"""
    return create_text_message(plate_error_text, user_id, get_support_quick_reply(user_id))

def version_error(user_id=None):
    """生成版本错误消息"""
    return create_text_message(version_error_text, user_id, get_support_quick_reply(user_id))

def store_error(user_id=None):
    """生成店铺错误消息"""
    return create_text_message(store_error_text, user_id)

def qrcode_error(user_id=None):
    """生成二维码错误消息"""
    return create_text_message(qrcode_error_text, user_id)

def rate_limit_msg(user_id=None):
    """生成频率限制消息"""
    return create_text_message(rate_limit_msg_text, user_id, get_support_quick_reply(user_id))

def maintenance_error(user_id=None):
    """生成维护错误消息"""
    return create_text_message(maintenance_error_text, user_id, get_support_quick_reply(user_id))

def friend_error(user_id=None):
    """生成好友错误消息"""
    return create_text_message(friend_error_text, user_id)

def friend_rcd_error(user_id=None):
    """生成好友记录错误消息"""
    return create_text_message(friend_rcd_error_text, user_id)

def perm_request_sent(name, user_id=None):
    """生成权限请求已发送消息"""
    text = get_multilingual_text(perm_request_sent_text, user_id).format(name=name)
    return TextMessage(text=text)

def perm_request_already_sent(user_id=None):
    """生成权限请求已发送消息"""
    return create_text_message(perm_request_already_sent_text, user_id)

def perm_request_already_granted(name, user_id=None):
    """生成已拥有访问权限的消息"""
    text = get_multilingual_text(perm_request_already_granted_text, user_id).format(name=name)
    return TextMessage(text=text)

def perm_request_accepted(name, requester_name, user_id=None):
    """生成权限请求已接受消息"""
    text = get_multilingual_text(perm_request_accepted_text, user_id).format(name=name, requester_name=requester_name)
    return TextMessage(text=text)

def perm_request_rejected(name, requester_name, user_id=None):
    """生成权限请求已拒绝消息"""
    text = get_multilingual_text(perm_request_rejected_text, user_id).format(name=name, requester_name=requester_name)
    return TextMessage(text=text)

def perm_request_not_found(user_id=None):
    """生成权限请求未找到消息"""
    return create_text_message(perm_request_not_found_text, user_id)

def get_perm_request_notification_alt_text(count, user_id=None):
    """获取权限请求通知的 alt text"""
    return get_multilingual_text(perm_request_notification_alt_text, user_id).format(count=count)

def notice_upload(user_id=None):
    """生成公告上传消息"""
    return create_text_message(notice_upload_text, user_id)

def friend_use_once(name, user_id=None):
    """生成临时使用好友账号消息"""
    text = get_multilingual_text(friend_use_once_text, user_id).format(name=name)
    return TextMessage(text=text)

def friend_best50_title(name, user_id=None):
    """生成好友 Best 50 标题消息"""
    text = get_multilingual_text(friend_best50_title_text, user_id).format(name=name)
    return TextMessage(text=text)

def level_record_not_found(level, page, user_id=None):
    """生成指定等级记录未找到消息"""
    text = get_multilingual_text(level_record_not_found_text, user_id).format(level=level, page=page)
    return TextMessage(text=text)

def level_record_page_hint(page, user_id=None):
    """生成等级记录页面提示消息"""
    text = get_multilingual_text(level_record_page_hint_text, user_id).format(page=page)
    return TextMessage(text=text)

def dxdata_update_notification(message, user_id=None):
    """生成 Dxdata 更新通知消息（管理员）"""
    text = get_multilingual_text(dxdata_update_notification_text, user_id).format(message=message)
    return TextMessage(text=text)

def get_notice_header(user_id=None):
    """获取公告标题（多语言）"""
    return get_multilingual_text(notice_header_text, user_id)

def get_friend_list_alt_text(user_id=None):
    """获取好友列表 alt_text（多语言）"""
    return get_multilingual_text(friend_list_alt_text, user_id)

def get_nearby_stores_alt_text(user_id=None):
    """获取附近机厅列表 alt_text（多语言）"""
    return get_multilingual_text(nearby_stores_alt_text, user_id)

def build_dxdata_update_message(result, user_id=None):
    """
    构建 Dxdata 更新消息（多语言）

    Args:
        result: update_dxdata_with_comparison 返回的结果字典
        user_id: 用户ID（用于确定语言）

    Returns:
        str: 多语言更新消息
    """
    if not result.get('success'):
        # 更新失败
        if 'message' in result:
            # 如果已经有消息，判断是什么类型的错误
            if 'データ取得失敗' in result['message'] or 'fetch' in result['message'].lower():
                return get_multilingual_text(dxdata_fetch_failed_text, user_id)
            else:
                return get_multilingual_text(dxdata_parse_failed_text, user_id)
        return get_multilingual_text(dxdata_fetch_failed_text, user_id)

    message_parts = []

    # 标题
    message_parts.append(get_multilingual_text(dxdata_update_success_text, user_id))
    message_parts.append('')

    if result.get('old_stats'):
        # 有历史数据，显示对比
        diff = result.get('diff', {})
        songs_diff = diff.get('songs_added', 0)
        sheets_diff = diff.get('sheets_added', 0)

        # 新曲变化
        if songs_diff > 0:
            message_parts.append(get_multilingual_text(dxdata_new_songs_text, user_id).format(count=songs_diff))
        elif songs_diff < 0:
            message_parts.append(get_multilingual_text(dxdata_songs_decreased_text, user_id).format(count=songs_diff))
        else:
            message_parts.append(get_multilingual_text(dxdata_no_new_songs_text, user_id))

        # 新谱面变化
        if sheets_diff > 0:
            message_parts.append(get_multilingual_text(dxdata_new_sheets_text, user_id).format(count=sheets_diff))
        elif sheets_diff < 0:
            message_parts.append(get_multilingual_text(dxdata_sheets_decreased_text, user_id).format(count=sheets_diff))
        else:
            message_parts.append(get_multilingual_text(dxdata_no_new_sheets_text, user_id))

        # 上次更新时间
        message_parts.append('')
        message_parts.append(get_multilingual_text(dxdata_last_update_text, user_id).format(
            timestamp=result['old_stats']['timestamp']
        ))

        # 当前统计
        new_stats = result['new_stats']
        message_parts.append(get_multilingual_text(dxdata_current_stats_text, user_id).format(
            songs=new_stats['total_songs'],
            sheets=new_stats['total_sheets']
        ))
    else:
        # 首次更新
        new_stats = result['new_stats']
        message_parts.append(get_multilingual_text(dxdata_initial_stats_songs_text, user_id).format(
            count=new_stats['total_songs']
        ))
        message_parts.append(get_multilingual_text(dxdata_initial_stats_sheets_text, user_id).format(
            count=new_stats['total_sheets']
        ))
        message_parts.append('')
        message_parts.append(get_multilingual_text(dxdata_first_update_text, user_id))

    return '\n'.join(message_parts)

def level_list_hint(user_id=None):
    """生成定数列表提示消息"""
    text = get_multilingual_text(level_list_hint_text, user_id)
    return TextMessage(text=text)
