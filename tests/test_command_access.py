import ast
import re
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from modules.commands import command_config as access
from modules.commands.command_help import command_help_message, detect_command_help_key
from modules.commands.command_parsers import parse_fix_record_command
from modules.commands.command_router import Command, Exact
from modules.score_recognition.presentation import build_fix_command
from modules.score_rules import JUDGEMENT_ROWS


@pytest.mark.parametrize('user,allowed,expected', [
    ('user', None, True), ('', None, False), ('user', '', False),
    ('user', 'other', False), ('user', ' other, user ', True),
])
def test_special_command_policy(monkeypatch, user, allowed, expected):
    if allowed is None:
        monkeypatch.delenv('JIETNG_AI_REC_ALLOWED_USERS', raising=False)
    else:
        monkeypatch.setenv('JIETNG_AI_REC_ALLOWED_USERS', allowed)
    assert access.can_use_command(user, 'ai-rec') is expected
    if not expected:
        with pytest.raises(PermissionError):
            access.require_command_access(user, 'ai-rec')


def test_regular_commands_unaffected(monkeypatch):
    monkeypatch.setenv('JIETNG_AI_REC_ALLOWED_USERS', '')
    assert access.can_use_command('user', 'rec')
    assert access.can_use_command('user', 'crop')


@pytest.mark.parametrize('allowed', [True, False])
def test_generic_dispatch_checks_canonical_command_and_sender(monkeypatch, allowed):
    monkeypatch.setitem(access.COMMAND_ACCESS_POLICIES, 'future_paid_command', 'TEST_COMMAND_USERS')
    monkeypatch.setenv('TEST_COMMAND_USERS', 'sender' if allowed else 'mentioned-user')
    command = Command(Exact('alias'), Mock(), name='future_paid_command')
    path = Path(__file__).resolve().parents[1] / 'main.py'
    node = next(n for n in ast.parse(path.read_text()).body
                if isinstance(n, ast.FunctionDef) and n.name == 'dispatch_command')
    namespace = dict(COMMANDS=[command], _reply_command_help_if_needed=Mock(return_value=False),
                     smart_reply=Mock(), access_error=Mock(), configuration={},
                     QUEUE_SYNC='sync', _run_sync_handler=Mock())
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), 'exec'), namespace)
    ctx = SimpleNamespace(text='alias', user_id='sender', id_use='mentioned-user',
                          reply_token='token', source_type='user')
    assert namespace['dispatch_command'](ctx)
    assert namespace['_run_sync_handler'].called is allowed
    assert namespace['smart_reply'].called is (not allowed)


def _recognize_handler():
    path = Path(__file__).resolve().parents[1] / 'main.py'
    node = next(node for node in ast.parse(path.read_text()).body
                if isinstance(node, ast.FunctionDef) and node.name == '_handle_recognize_command')
    namespace = dict(re=re, smart_reply=Mock(), access_error=Mock(), configuration={},
                     _enqueue_score_recognition_task=Mock())
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), 'exec'), namespace)
    return namespace


@pytest.mark.parametrize('text,command,flex', [
    ('ai-rec', 'ai-rec', False), ('AI-REC -flex', 'ai-rec', True),
    ('rec', 'rec', False), ('crop', 'crop', False),
])
def test_routes_explicit_recognition_commands(monkeypatch, text, command, flex):
    monkeypatch.delenv('JIETNG_AI_REC_ALLOWED_USERS', raising=False)
    namespace = _recognize_handler()
    event = SimpleNamespace(source=SimpleNamespace(user_id='user'),
                            message=SimpleNamespace(quoted_message_id='image'), reply_token='reply')
    assert namespace['_handle_recognize_command'](event, text)
    namespace['_enqueue_score_recognition_task'].assert_called_once_with(
        event, command, 'image', force_flex=flex)


def test_denied_ai_request_does_not_enter_queue(monkeypatch):
    monkeypatch.setenv('JIETNG_AI_REC_ALLOWED_USERS', '')
    namespace = _recognize_handler()
    event = SimpleNamespace(source=SimpleNamespace(user_id='user'),
                            message=SimpleNamespace(quoted_message_id='image'), reply_token='reply')
    assert namespace['_handle_recognize_command'](event, 'ai-rec')
    namespace['_enqueue_score_recognition_task'].assert_not_called()
    namespace['smart_reply'].assert_called_once()


@pytest.mark.parametrize('query,key', [
    ('HELP', 'help_index'), ('maimai   update', 'maimai_update'),
    ('song info', 'song_info'), ('song record', 'song_record'),
    ('13+ records 2', 'level_records'), ('舞神 plate -uc', 'plate'),
    ('artist', 'search_by_artist'), ('not-a-command', None),
])
def test_help_aliases(query, key):
    assert detect_command_help_key(query) == key


def test_help_messages_and_unknown_key():
    for key in ('help_index', 'b_records', 'bind', 'calc_notes'):
        message = command_help_message(key)
        assert message.alt_text
        assert message.contents.to_dict()['type'] == 'bubble'
    assert command_help_message('not-a-command') is None


def test_generated_fix_command_round_trip():
    judgement = {name: dict(critical_perfect=100, perfect=5, great=2, good=1, miss=0)
                 for name in JUDGEMENT_ROWS}
    for title in ('Alpha Beta', ''):
        command = build_fix_command(judgement, title, 99.1234)
        assert parse_fix_record_command(command) == (title, 99.1234, judgement)


def test_comma_percentage_and_legacy_chart_suffix():
    command = '\n'.join(['fix-rcd Alpha [DX]', '100,5000%', *(['1/2/3/4/5'] * 5)])
    title, score, rows = parse_fix_record_command(command)
    assert (title, score) == ('Alpha', 100.5)
    assert rows['break']['miss'] == 5


@pytest.mark.parametrize('achievement', ['102%', '-1', 'nan', '99.12345%'])
def test_invalid_fix_achievement(achievement):
    command = '\n'.join(['fix-rcd Alpha', achievement, *(['0/0/0/0/0'] * 5)])
    with pytest.raises(ValueError, match='achievement'):
        parse_fix_record_command(command)


def test_invalid_fix_rows_and_non_commands():
    for command in ('', 'fix-rcd-help', 'info Alpha'):
        assert parse_fix_record_command(command) is None
    with pytest.raises(ValueError, match='five judgement rows'):
        parse_fix_record_command('fix-rcd Alpha\n100%')
    command = '\n'.join(['fix-rcd Alpha', '100%', '1/2/3/4', *(['0/0/0/0/0'] * 4)])
    with pytest.raises(ValueError, match='slash-separated integers'):
        parse_fix_record_command(command)
