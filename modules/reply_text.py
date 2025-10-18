from modules.config_loader import DOMAIN
from linebot.models import (
    TextSendMessage,
    QuickReply,
    QuickReplyButton,
    MessageAction,
    URIAction
)

bind_msg = TextSendMessage(
    text="✅ SEGA ID 連携できた！",
    quick_reply=QuickReply(
        items=[
            QuickReplyButton(action=MessageAction(label="maimai update", text="maimai update")),
            QuickReplyButton(action=URIAction(label="サポート", uri=f"https://{DOMAIN}/")),
        ]
    )
)
unbind_msg = TextSendMessage(text="✅ SEGA ID 連携解消できた！")

update_over = TextSendMessage(
    text="✅ アップデート完了！",
    quick_reply=QuickReply(
        items=[
            QuickReplyButton(action=MessageAction(label="Best 50", text="b50")),
            QuickReplyButton(action=MessageAction(label="All Perfect Best 50", text="apb50")),
            QuickReplyButton(action=MessageAction(label="Ideal Best 50", text="idlb50")),
            QuickReplyButton(action=URIAction(label="サポート", uri=f"https://{DOMAIN}/")),
        ]
    )
)
update_error = TextSendMessage(
    text="❗️アップデート中エラーが発生！",
    quick_reply=QuickReply(
        items=[
            QuickReplyButton(action=MessageAction(label="もう一回", text="maimai update")),
            QuickReplyButton(action=URIAction(label="サポート", uri=f"https://{DOMAIN}/")),
        ]
    )
)

segaid_error = TextSendMessage(
    text="SEGAアカウントはまだ連携されてないでしょ？",
    quick_reply=QuickReply(
        items=[
            QuickReplyButton(action=MessageAction(label="アカウント連携", text="sega bind")),
            QuickReplyButton(action=URIAction(label="サポート", uri=f"https://{DOMAIN}/")),
        ]
    )
)

record_error = TextSendMessage(
    text="maimaiレコードはまだアップデートされてないね？",
    quick_reply=QuickReply(
        items=[
            QuickReplyButton(action=MessageAction(label="maimai update", text="maimai update")),
            QuickReplyButton(action=URIAction(label="サポート", uri=f"https://{DOMAIN}/")),
        ]
    )
)

active_reply = TextSendMessage(text="✅ Active")
access_error = TextSendMessage(text="🙇 今はアクセスが集中しています。後ほどもう一度お試しください。")

input_error = TextSendMessage(
    text="ゼンゼンわかんないなー",
    quick_reply=QuickReply(
        items=[
            QuickReplyButton(action=URIAction(label="サポート", uri=f"https://{DOMAIN}/")),
        ]
    )
)
song_error = TextSendMessage(
    text="条件に合う楽曲がないかも...",
    quick_reply=QuickReply(
        items=[
            QuickReplyButton(action=URIAction(label="サポート", uri=f"https://{DOMAIN}/")),
        ]
    )
)
plate_error = TextSendMessage(
    text="プレートわかんないね...",
    quick_reply=QuickReply(
        items=[
            QuickReplyButton(action=URIAction(label="サポート", uri=f"https://{DOMAIN}/")),
        ]
    )
)
version_error = TextSendMessage(
    text="バージョンわかんないね...",
    quick_reply=QuickReply(
        items=[
            QuickReplyButton(action=URIAction(label="サポート", uri=f"https://{DOMAIN}/")),
        ]
    )
)

friend_error = TextSendMessage(text="お気に入りに登録したフレンドいないでしょ？")

qrcode_error = TextSendMessage(text="わかんないけどいい写真かな？")

share_msg = TextSendMessage(text="この画像を友達にシェアしよ！")

notice_upload = TextSendMessage(text="✅ Notice uploaded")
dxdata_update = TextSendMessage(text="✅ Dxdata Updated!")
