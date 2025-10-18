from linebot.models import FlexSendMessage, TextSendMessage
from modules.reply_text import friend_error

def _create_button_action(btn):
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

def _create_button_bubble(title, buttons):
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
                    "action": _create_button_action(btn)
                } for btn in buttons
            ]
        }
    }

def generate_friend_buttons(alt_text, button_list, group_size=10):
    if not button_list:
        return friend_error
    bubbles = []
    for i in range(0, len(button_list), group_size):
        group = button_list[i:i + group_size]
        bubble = _create_button_bubble(alt_text, group)
        bubbles.append(bubble)

    return FlexSendMessage(
        alt_text=alt_text,
        contents={
            "type": "carousel",
            "contents": bubbles
        }
    )
