"""Button entry points show loading before rendering, without live LINE calls."""
import ast
import asyncio
from pathlib import Path
import re
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


@pytest.mark.parametrize('command,kind', [('search-song abc123','info'), ('search-record abc123&id_use=target','record')])
@pytest.mark.parametrize('source_type', ['user','group'])
def test_song_buttons_show_loading_before_render(command, kind, source_type):
    events=[]

    async def info(*args):
        events.append('info')
        return 'image'

    async def record(*args):
        events.append('record')
        assert args[:2] == ('sender','target')
        return 'image'

    namespace=dict(re=re,asyncio=asyncio,
                   show_loading=lambda user_id: events.append(('loading',user_id)),
                   get_user_field=lambda *args:'jp',search_song_by_id=info,
                   get_song_record_by_id=record,configuration=object(),smart_reply=Mock())
    path=Path(__file__).resolve().parents[1]/'main.py'
    node=next(node for node in ast.parse(path.read_text()).body
              if isinstance(node,ast.FunctionDef) and node.name=='handle_postback_command')
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),'exec'),namespace)
    event=SimpleNamespace(source=SimpleNamespace(user_id='sender',type=source_type),reply_token='reply')
    assert namespace['handle_postback_command'](event,command) is True
    assert events == ([('loading','sender'),kind] if source_type=='user' else [kind])
    namespace['smart_reply'].assert_called_once()
