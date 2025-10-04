from linebot.models import FlexSendMessage, TextSendMessage

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

def create_button_bubble(title, buttons):
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
    if not button_list:
        return TextSendMessage(text="お気に入りのフレンドいないね？")
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
