"""Exercise the real handler and route without starting the LINE server."""
import ast
import asyncio
import logging
from pathlib import Path
import re
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock

SOURCE = Path(__file__).resolve().parents[1] / 'main.py'
TREE = ast.parse(SOURCE.read_text())


class SongInfoImageTests(unittest.TestCase):
    def test_song_info_route_accepts_bare_command(self):
        route = next(node for node in ast.walk(TREE)
                     if isinstance(node, ast.Call)
                     and isinstance(node.func, ast.Name) and node.func.id == 'Command'
                     and any(k.arg == 'name' and isinstance(k.value, ast.Constant)
                             and k.value.value == 'song_info' for k in node.keywords))
        pattern = route.args[0].args[0].value
        for text in ('info', 'INFO', '白ゆき info', '白ゆきってどんな曲'):
            self.assertIsNotNone(re.fullmatch(pattern, text, re.IGNORECASE), text)
        self.assertIsNone(re.fullmatch(pattern, 'userinfo', re.IGNORECASE))

    def test_quoted_info_downloads_image_and_searches_recognized_title(self):
        for text in ('info', 'INFO', ' info '):
            with self.subTest(text=text):
                namespace = self.handler_namespace()
                ctx = self.context(text, 'photo-id')
                self.assertEqual(namespace['cmd_song_info'](ctx), 'song-result')
                namespace['_download_line_message_content'].assert_called_once_with('photo-id')
                namespace['recognize_score_image_bytes'].assert_called_once_with(
                    b'image', fields=('main_title',))
                namespace['search_song'].assert_awaited_once_with('user', '白ゆき', 'jp')

    def test_text_search_and_bare_command(self):
        namespace = self.handler_namespace()
        self.assertEqual(namespace['cmd_song_info'](self.context('白ゆき info', None)), 'song-result')
        namespace['_download_line_message_content'].assert_not_called()
        namespace['search_song'].assert_awaited_once_with('user', '白ゆき', 'jp')
        namespace['search_song'].reset_mock()
        self.assertEqual(namespace['cmd_song_info'](self.context('info', None)), 'song-result')
        namespace['search_song'].assert_awaited_once_with('user', '', 'jp')

    @staticmethod
    def context(text, quoted):
        return SimpleNamespace(text=text, user_id='user', mai_ver='jp', event=SimpleNamespace(
            message=SimpleNamespace(quoted_message_id=quoted)))

    @staticmethod
    def handler_namespace():
        namespace = dict(re=re, asyncio=asyncio, logger=logging.getLogger(__name__),
                         InvalidScoreImageError=ValueError,
                         _download_line_message_content=Mock(return_value=b'image'),
                         recognize_score_image_bytes=Mock(return_value={'parsed': {'title': '白ゆき'}}),
                         search_song=AsyncMock(return_value='song-result'),
                         info_error=Mock(return_value='info-error'), song_error=Mock(return_value='song-error'))
        node = next(node for node in TREE.body if isinstance(node, ast.FunctionDef)
                    and node.name == 'cmd_song_info')
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(SOURCE), 'exec'), namespace)
        return namespace
