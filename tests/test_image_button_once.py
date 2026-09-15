from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import sqlite3
from unittest.mock import Mock

import pytest
from itsdangerous import URLSafeSerializer
from modules import image_button_once as buttons


@pytest.fixture
def button_store(tmp_path, monkeypatch):
    path = tmp_path / 'buttons.db'

    class Cursor:
        def __init__(self, connection):
            self.cursor = connection.cursor()

        def execute(self, sql, args=()):
            if 'CREATE TABLE' in sql:
                sql = 'CREATE TABLE IF NOT EXISTS image_button_uses (button_id TEXT PRIMARY KEY)'
            else:
                sql = sql.replace('INSERT IGNORE', 'INSERT OR IGNORE').replace('%s', '?')
            self.cursor.execute(sql, args)

        @property
        def rowcount(self):
            return self.cursor.rowcount

    @contextmanager
    def database_cursor(*, write):
        connection = sqlite3.connect(path, timeout=10)
        try:
            yield connection, Cursor(connection)
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    monkeypatch.setattr(buttons, 'database_cursor', database_cursor)
    monkeypatch.setattr(buttons, '_signer', lambda: URLSafeSerializer('test-only', salt='image-button-once-v1'))
    monkeypatch.setattr(buttons, '_table_ready', False)


def test_concurrent_clicks_and_restart_only_claim_once(button_store, monkeypatch):
    action = buttons.image_button_data('search-song abc123')
    with ThreadPoolExecutor(max_workers=8) as workers:
        results = list(workers.map(buttons.consume_image_button, [action] * 16))
    assert results.count('search-song abc123') == 1
    assert results.count(None) == 15
    monkeypatch.setattr(buttons, '_table_ready', False)
    assert buttons.consume_image_button(action) is None


def test_info_record_note_and_new_cards_have_independent_uses(button_store):
    for command in ['search-song abc123', 'search-record abc123&id_use=target', 'calc-song abc123', 'search-song abc123']:
        data = buttons.image_button_data(command)
        assert len(data) < 300
        assert buttons.consume_image_button(data) == command
        assert buttons.consume_image_button(data) is None


def test_tampered_buttons_cannot_claim_or_execute(button_store, monkeypatch):
    data = buttons.image_button_data('search-song abc123')
    store = Mock(side_effect=AssertionError('invalid token must not reach the database'))
    monkeypatch.setattr(buttons, 'database_cursor', store)
    assert buttons.consume_image_button(data[:-3] + 'xyz') is None
    assert buttons.consume_image_button('image-once invalid') is None
    with pytest.raises(ValueError):
        buttons.image_button_data('unbind')
    store.assert_not_called()


def test_failed_database_claim_does_not_authorize_execution(button_store, monkeypatch):
    monkeypatch.setattr(buttons, '_ensure_table', Mock(side_effect=RuntimeError('database unavailable')))
    with pytest.raises(RuntimeError):
        buttons.consume_image_button(buttons.image_button_data('search-song abc123'))
