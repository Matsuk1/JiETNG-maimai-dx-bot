"""Run the command gate without importing the LINE application runtime."""
import ast
from pathlib import Path
import re
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


def handler():
    source = Path(__file__).resolve().parents[1] / 'main.py'
    node = next(node for node in ast.parse(source.read_text()).body
                if isinstance(node, ast.FunctionDef) and node.name == '_handle_recognize_command')
    namespace = dict(re=re, smart_reply=Mock(), access_error=Mock(), configuration={},
                     _enqueue_score_recognition_task=Mock())
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(source), 'exec'), namespace)
    return namespace


@pytest.mark.parametrize('text,command,flex', [('ai-rec', 'ai-rec', False),
    ('AI-REC -flex', 'ai-rec', True), ('rec', 'rec', False), ('crop', 'crop', False)])
def test_routes_explicit_commands(monkeypatch, text, command, flex):
    monkeypatch.delenv('JIETNG_AI_REC_ALLOWED_USERS', raising=False)
    namespace = handler()
    event = SimpleNamespace(source=SimpleNamespace(user_id='user'),
                            message=SimpleNamespace(quoted_message_id='image'), reply_token='reply')
    assert namespace['_handle_recognize_command'](event, text)
    namespace['_enqueue_score_recognition_task'].assert_called_once_with(
        event, command, 'image', force_flex=flex)


def test_denied_ai_request_does_not_enter_queue(monkeypatch):
    monkeypatch.setenv('JIETNG_AI_REC_ALLOWED_USERS', '')
    namespace = handler()
    event = SimpleNamespace(source=SimpleNamespace(user_id='user'),
                            message=SimpleNamespace(quoted_message_id='image'), reply_token='reply')
    assert namespace['_handle_recognize_command'](event, 'ai-rec')
    namespace['_enqueue_score_recognition_task'].assert_not_called()
    namespace['smart_reply'].assert_called_once()
