import json
import base64
import hmac
import hashlib
import requests

channel_secret = "your_secret_here"
target_url = "https://example.com/linebot/webhook"
access_token = "your_access_token_here"

def _create_line_webhook_payload(user_id, content, token, type):
    return {
        "events": [
            {
                "type": "message",
                "replyToken": f"proxy-{token}",
                "source": {
                    "userId": user_id,
                    "type": type
                },
                "timestamp": 1610000000000,
                "mode": "active",
                "message": {
                    "type": "text",
                    "id": "0000000000",
                    "text": content
                }
            }
        ],
        "destination": "U00000000000000000000000000000000"
    }

def _generate_signature(channel_secret: str, body: str) -> str:
    hash = hmac.new(channel_secret.encode('utf-8'), body.encode('utf-8'), hashlib.sha256).digest()
    signature = base64.b64encode(hash).decode()
    return signature

def proxy_send(user_id, content, token, type):
    payload = _create_line_webhook_payload(user_id, content, token, type)
    payload_str = json.dumps(payload, ensure_ascii=False)
    signature = _generate_signature(channel_secret, payload_str)

    headers = {
        "X-Line-Signature": signature,
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }

    response = requests.post(target_url, headers=headers, data=payload_str)

    print(f"Status: {response.status_code}")
    print("Response:")
    print(response.text)

