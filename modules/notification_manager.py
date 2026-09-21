import json
import logging
import threading
from datetime import datetime

from modules.config_loader import VAPID_PRIVATE_KEY, VAPID_CONTACT

logger = logging.getLogger(__name__)

_notifications = []
_notif_lock = threading.Lock()
MAX_NOTIFICATIONS = 100
PUSH_SUBS_FILE = './data/push_subscriptions.json'
_subscriptions = {}
_subs_lock = threading.Lock()
_push_dependency_missing = False


def _load_subscriptions():
    global _subscriptions
    try:
        with open(PUSH_SUBS_FILE, encoding='utf-8') as file:
            data = json.load(file)
            _subscriptions = data if isinstance(data, dict) else {}
    except FileNotFoundError:
        _subscriptions = {}
    except (OSError, json.JSONDecodeError):
        logger.exception("[Push] Failed to load subscriptions")
        _subscriptions = {}


def _save_subscriptions():
    try:
        with open(PUSH_SUBS_FILE, 'w', encoding='utf-8') as file:
            json.dump(_subscriptions, file)
    except OSError:
        logger.exception("[Push] Failed to save subscriptions")


_load_subscriptions()


def add_push_subscription(subscription: dict):
    endpoint = subscription.get('endpoint')
    if not endpoint:
        return
    with _subs_lock:
        _subscriptions[endpoint] = subscription
        _save_subscriptions()


def remove_push_subscription(endpoint: str):
    with _subs_lock:
        _subscriptions.pop(endpoint, None)
        _save_subscriptions()


def _send_push(title: str, body: str):
    global _push_dependency_missing
    if not _subscriptions or _push_dependency_missing:
        return

    try:
        from pywebpush import webpush
    except ImportError:
        logger.warning("[Push] pywebpush not installed, skipping push notification")
        _push_dependency_missing = True
        return

    with _subs_lock:
        subs = list(_subscriptions.items())

    stale_endpoints = []
    payload = json.dumps({'title': title, 'body': body})

    for endpoint, sub in subs:
        try:
            webpush(
                subscription_info=sub,
                data=payload,
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims={'sub': VAPID_CONTACT}
            )
        except Exception as exc:
            if '410' in str(exc) or '404' in str(exc):
                stale_endpoints.append(endpoint)
            else:
                logger.error("[Push] Failed to send to %s: %s", endpoint[:40], exc)

    if stale_endpoints:
        with _subs_lock:
            for endpoint in stale_endpoints:
                _subscriptions.pop(endpoint, None)
            _save_subscriptions()


def record_notification(title: str, details: str, user_id: str = None, context: dict = None):
    display_user = user_id or 'Unknown'
    with _notif_lock:
        _notifications.insert(0, {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'title': title,
            'details': details,
            'user_id': display_user,
            'context': context or {}
        })
        del _notifications[MAX_NOTIFICATIONS:]

    first_line = details.splitlines()[0] if details else ''
    body = f"{display_user}\n{first_line}" if first_line else display_user
    threading.Thread(target=_send_push, args=(title, body), daemon=True).start()


def get_notifications():
    with _notif_lock:
        return list(_notifications)


def clear_notifications():
    with _notif_lock:
        _notifications.clear()
