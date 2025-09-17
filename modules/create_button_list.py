from linebot.models import FlexSendMessage

def create_button_action(btn):
    if btn["type"] == "text":
        return {
            "type": "message",
            "label": btn["label"],
            "text": btn["content"]
        }
    elif btn["type"] == "uri":
        return {
            "type": "uri",
            "label": btn["label"],
            "uri": btn["content"]
        }
    else:
        raise ValueError(f"Unsupported button type: {btn['type']}")

#def create_button_bubble(title, buttons):
#    return {
#        "type": "bubble",
#        "size": "mega",
#        "body": {
#            "type": "box",
#            "layout": "vertical",
#            "spacing": "md",
#            "contents": [
#                {"type": "text", "text": title, "weight": "bold", "size": "lg"}
#            ] + [
#                {
#                    "type": "button",
#                    "style": "primary",
#                    "action": create_button_action(btn)
#                } for btn in buttons
#            ]
#        }
#    }

def create_button_bubble(title, buttons):
    # 如果没有按钮，提供一个错误提示按钮
    if not buttons:
        buttons = ["Error"]

    return {
        "type": "bubble",
        "size": "mega",
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": [
                {
                    "type": "text",
                    "text": title,
                    "weight": "bold",
                    "size": "lg",
                    "wrap": True
                }
            ] + [
                {
                    "type": "button",
                    "style": "secondary",  # 更简约的样式
                    "height": "sm",
                    "action": create_button_action(btn)
                } for btn in buttons
            ]
        }
    }

def generate_flex_carousel(alt_text, button_list):
    bubbles = []
    group_size = 8  # 每页 8 个按钮
    for i in range(0, len(button_list), group_size):
        group = button_list[i:i + group_size]
        bubble = create_button_bubble(alt_text, group)
        bubbles.append(bubble)

    return FlexSendMessage(
        alt_text=alt_text,
        contents={
            "type": "carousel",
            "contents": bubbles
        }
    )

my_buttons = [
    {"label": "バインド", "type": "text", "content": "バインド"},
    {"label": "ヘルプ", "type": "text", "content": "ヘルプを表示して"},
    {"label": "公式サイト", "type": "uri", "content": "https://example.com"},
    {"label": "マイページ", "type": "uri", "content": "https://mypage.example.com"},
    {"label": "設定", "type": "text", "content": "設定"},
    {"label": "スコア確認", "type": "text", "content": "スコア"},
    {"label": "アップデート", "type": "text", "content": "更新"},
    {"label": "戻る", "type": "text", "content": "戻る"}
]

test_flex_message = generate_flex_carousel("TEST", my_buttons)
