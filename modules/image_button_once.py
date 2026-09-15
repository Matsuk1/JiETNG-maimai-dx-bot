"""Signed, single-use Info/Record/Note postbacks, shared across server workers."""
from functools import lru_cache
import re
import secrets
import threading

from itsdangerous import BadSignature, URLSafeSerializer

from modules.dbpool_manager import database_cursor
from modules.session_key import load_session_key

PREFIX = 'image-once '
_ACTION = re.compile(r'(?:(?:search-song|calc-song) \S{6}|search-record \S{6}(?:&id_use=\S+)?)')
_table_ready = False
_table_lock = threading.Lock()


@lru_cache(maxsize=1)
def _signer():
    return URLSafeSerializer(load_session_key(), salt='image-button-once-v1')


def image_button_data(command):
    """Each rendered button gets its own signed nonce, even for the same song."""
    if not _ACTION.fullmatch(command):
        raise ValueError('Unsupported image button action')
    return PREFIX + _signer().dumps([secrets.token_hex(16), command])


def _ensure_table():
    global _table_ready
    if _table_ready:
        return
    with _table_lock:
        if _table_ready:
            return
        with database_cursor(write=True) as (_, cursor):
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS image_button_uses (
                    button_id CHAR(32) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
                    used_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB
            ''')
        _table_ready = True


def consume_image_button(data):
    """Claim before loading/rendering; duplicate or invalid buttons do nothing.

    The primary key makes concurrent deliveries safe across processes. Claims
    persist across restarts, including a failed image generation after claiming.
    Database failures propagate so an unclaimed action cannot be executed.
    """
    if not data.startswith(PREFIX):
        return None
    try:
        payload = _signer().loads(data[len(PREFIX):])
    except BadSignature:
        return None
    if not isinstance(payload, list) or len(payload) != 2:
        return None
    nonce, command = payload
    if (not isinstance(nonce, str) or not re.fullmatch(r'[0-9a-f]{32}', nonce)
            or not isinstance(command, str) or not _ACTION.fullmatch(command)):
        return None
    _ensure_table()
    with database_cursor(write=True) as (_, cursor):
        cursor.execute('INSERT IGNORE INTO image_button_uses (button_id) VALUES (%s)', (nonce,))
        claimed = cursor.rowcount == 1
    return command if claimed else None
