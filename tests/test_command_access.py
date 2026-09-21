import ast
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from modules.commands import command_config as access
from modules.commands.command_router import Command, Exact


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
