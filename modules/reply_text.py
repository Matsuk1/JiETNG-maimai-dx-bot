from modules.config_loader import DOMAIN
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
# アカウント連携関連 / Account Binding
# ============================================================

bind_msg = TextMessage(
    text="✅ SEGA IDの連携できたよ！",
    quick_reply=QuickReply(
        items=[
            QuickReplyItem(action=MessageAction(label="maimai update", text="maimai update")),
            QuickReplyItem(action=URIAction(label="サポート", uri=f"https://{DOMAIN}/")),
        ]
    )
)

unbind_msg = TextMessage(text="✅ SEGA IDの連携を解除したよ！")

# ============================================================
# データ更新関連 / Data Update
# ============================================================

update_over = TextMessage(
    text="✅ アップデート完了！",
    quick_reply=QuickReply(
        items=[
            QuickReplyItem(action=MessageAction(label="Best 50", text="b50")),
            QuickReplyItem(action=MessageAction(label="Best 100", text="b100")),
            QuickReplyItem(action=MessageAction(label="All Best 50", text="ab50")),
            QuickReplyItem(action=MessageAction(label="All Best 35", text="ab35")),
            QuickReplyItem(action=MessageAction(label="All Perfect Best 50", text="apb50")),
            QuickReplyItem(action=MessageAction(label="Ideal Best 50", text="idlb50")),
            QuickReplyItem(action=URIAction(label="サポート", uri=f"https://{DOMAIN}/")),
        ]
    )
)

update_error = TextMessage(
    text="❗️あれ？アップデート中にエラーが出ちゃった！",
    quick_reply=QuickReply(
        items=[
            QuickReplyItem(action=MessageAction(label="もう一回", text="maimai update")),
            QuickReplyItem(action=URIAction(label="サポート", uri=f"https://{DOMAIN}/")),
        ]
    )
)

# ============================================================
# エラーメッセージ / Error Messages
# ============================================================

segaid_error = TextMessage(
    text="SEGAアカウントまだ連携してないよね？",
    quick_reply=QuickReply(
        items=[
            QuickReplyItem(action=MessageAction(label="アカウント連携", text="sega bind")),
            QuickReplyItem(action=URIAction(label="サポート", uri=f"https://{DOMAIN}/")),
        ]
    )
)

record_error = TextMessage(
    text="maimaiレコードまだアップデートしてないみたい！",
    quick_reply=QuickReply(
        items=[
            QuickReplyItem(action=MessageAction(label="maimai update", text="maimai update")),
            QuickReplyItem(action=URIAction(label="サポート", uri=f"https://{DOMAIN}/")),
        ]
    )
)

info_error = TextMessage(
    text="ごめん！maimai個人情報まだメモしてないわ！",
    quick_reply=QuickReply(
        items=[
            QuickReplyItem(action=MessageAction(label="maimai update", text="maimai update")),
            QuickReplyItem(action=URIAction(label="サポート", uri=f"https://{DOMAIN}/")),
        ]
    )
)

access_error = TextMessage(text="🙇 今めっちゃアクセス多いんだよね…ちょっと後でもう一回試してみて！")

input_error = TextMessage(
    text="全然わかんないなー",
    quick_reply=QuickReply(
        items=[
            QuickReplyItem(action=URIAction(label="サポート", uri=f"https://{DOMAIN}/")),
        ]
    )
)

picture_error = TextMessage(
    text="画像処理しっぱい〜〜",
    quick_reply=QuickReply(
        items=[
            QuickReplyItem(action=URIAction(label="サポート", uri=f"https://{DOMAIN}/")),
        ]
    )
)

song_error = TextMessage(
    text="条件に合う楽曲がないかも...",
    quick_reply=QuickReply(
        items=[
            QuickReplyItem(action=URIAction(label="サポート", uri=f"https://{DOMAIN}/")),
        ]
    )
)

plate_error = TextMessage(
    text="そのプレートがわからないね...",
    quick_reply=QuickReply(
        items=[
            QuickReplyItem(action=URIAction(label="サポート", uri=f"https://{DOMAIN}/")),
        ]
    )
)

version_error = TextMessage(
    text="そのバージョンがわからないね...",
    quick_reply=QuickReply(
        items=[
            QuickReplyItem(action=URIAction(label="サポート", uri=f"https://{DOMAIN}/")),
        ]
    )
)

store_error = TextMessage(text="🥹 周辺の設置店舗がないね")

qrcode_error = TextMessage(text="ん〜？よくわかんない写真だね")

rate_limit_msg = TextMessage(
    text="⏳ ちょっと待ってー！今同じリクエスト処理中だから！\n終わるまでちょっと待っててね〜",
    quick_reply=QuickReply(
        items=[
            QuickReplyItem(action=URIAction(label="サポート", uri=f"https://{DOMAIN}/")),
        ]
    )
)

maintenance_error = TextMessage(
    text="🔧 あれ？公式サイトがメンテナンス中みたい！\n夜間とかメンテナンス時間はアクセスできないから、またあとで試してみてね〜",
    quick_reply=QuickReply(
        items=[
            QuickReplyItem(action=URIAction(label="サポート", uri=f"https://{DOMAIN}/")),
        ]
    )
)

# ============================================================
# フレンド関連 / Friend Messages
# ============================================================

friendid_error = TextMessage(
    text="こういう人見つかってないね",
    quick_reply=QuickReply(
        items=[
            QuickReplyItem(action=URIAction(label="サポート", uri=f"https://{DOMAIN}/")),
        ]
    )
)

friend_added = TextMessage(
    text="もうフレンドになったじゃん！",
    quick_reply=QuickReply(
        items=[
            QuickReplyItem(action=URIAction(label="サポート", uri=f"https://{DOMAIN}/")),
        ]
    )
)

friendid_self_error = TextMessage(
    text="自分とはフレンドになれないよ！",
    quick_reply=QuickReply(
        items=[
            QuickReplyItem(action=URIAction(label="サポート", uri=f"https://{DOMAIN}/")),
        ]
    )
)

friend_error = TextMessage(text="お気に入りにフレンド登録してないみたいだよ？")

friend_rcd_error = TextMessage(text="この人フレンドじゃないかも！")

# フレンド申請関連
friend_request_sent = lambda name: TextMessage(text=f"✅ 「{name}」さんにフレンド申請送ったよ！\n相手が何かコマンド使ったら通知届くよ〜")
friend_request_already_sent = TextMessage(text="もう申請送ったよ〜！相手の承認を待っててね〜")
friend_request_already_friend = lambda name: TextMessage(text=f"「{name}」さんとはもうフレンドになったじゃん！")
friend_request_accepted = lambda name: TextMessage(text=f"✅ 「{name}」さんとフレンドになった！")
friend_request_rejected = lambda name: TextMessage(text=f"「{name}」さんからの申請を拒否したよ")
friend_request_not_found = TextMessage(text="あれ？その申請もう処理しちゃったかも")
friend_request_mutual_accepted = lambda name: TextMessage(text=f"✅ お互いに申請してたから自動で「{name}」さんとフレンドになった！")

# ============================================================
# 管理者通知 / Admin Notifications
# ============================================================

notice_upload = TextMessage(text="✅ Notice uploaded")
dxdata_update = TextMessage(text="✅ Dxdata Updated!")

# ============================================================
# その他 / Others
# ============================================================

share_msg = TextMessage(text="この画像を友達にシェアしよ！")

# ============================================================
# Tips メッセージリスト / Tips Messages
# ============================================================

tip_messages = [
    "💡 定期的に「maimai update」でデータを更新すると、最新のスコアが反映されるよ！",
    "💡 「b50」コマンドでBest 50を確認できるよ！自分の実力を把握しよう！",
    "💡 フレンド機能を使えば、友達のスコアと比較できるよ！",
    "💡 画像生成には少し時間がかかることがあるから、気長に待ってね〜",
    "💡 困ったときは「help」コマンドで使い方を確認できるよ！",
    "💡 定期的にレコードを更新して、進歩を記録しよう！",
    "💡 「ab50」で全難易度のBest 50を見られるよ！",
    "💡 プレイ後は早めに更新すると、リアルタイムで成長が見られるよ！",
    "💡 フレンド申請は相手がコマンドを使用したときに通知されるよ！",
    "💡 サポートページで詳しい使い方を確認できるよ！",
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
                        "Support JiETNG’s journey ahead!"
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
