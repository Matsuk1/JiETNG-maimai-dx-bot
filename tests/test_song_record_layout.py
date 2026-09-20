"""Chart-slot and routing checks without importing network/service dependencies."""
import ast
from pathlib import Path
from types import ModuleType
import unittest
from unittest.mock import Mock, patch


class SongRecordLayoutTests(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).resolve().parents[1] / 'modules/images/songs.py'
        nodes = [node for node in ast.parse(path.read_text()).body
                 if isinstance(node, ast.FunctionDef)
                 and node.name in ('song_info_generate', '_makeup_played_data')]
        for node in nodes:
            node.decorator_list = []
        self.records = ModuleType('modules.images.records')
        self.records.thumbnail_html = Mock(return_value='CARD')
        self.records.cover_html = Mock(return_value='COVER')
        self.renderer = ModuleType('modules.images.renderer')
        self.renderer.render_template = Mock(return_value='rendered')
        self.namespace = dict(_song_text=lambda key, language: (key, language), difficulty_color=lambda d: d, image_language=lambda v: 'ja',
                              compose_generated_images=Mock(return_value='composed'),
                              resize_by_width=Mock(), _render_basic_info_image=Mock(),
                              _generate_song_table_image=Mock())
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), self.namespace)
        self.patch = patch.dict('sys.modules', {'modules.images.records': self.records,
                                               'modules.images.renderer': self.renderer})
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def test_missing_records_keep_existing_charts_in_order(self):
        song = {'sheets': [{'difficulty': d, 'internalLevelValue': 13.7}
                          for d in ('master', 'basic', 'expert', 'advanced')]}
        self.namespace['_makeup_played_data']([{'difficulty': 'master'}], song)
        rows = self.renderer.render_template.call_args.kwargs['played_rows']
        self.assertEqual([r['label'] for r in rows], ['BASIC', 'ADVANCED', 'EXPERT', 'MASTER'])
        self.assertEqual([r['card'] for r in rows], ['', '', '', 'CARD'])

    def test_empty_list_is_record_page_but_omitted_records_is_info_page(self):
        self.namespace['song_info_generate']({'sheets': []}, played_data=[])
        self.assertEqual(self.renderer.render_template.call_args.kwargs['mode'], 'played')
        self.namespace['_generate_song_table_image'].assert_not_called()
        self.namespace['song_info_generate']({'sheets': []})
        self.namespace['_generate_song_table_image'].assert_called_once()

    def test_remaster_placeholder_has_its_own_constant_and_text_color(self):
        self.namespace['_makeup_played_data']([], {'sheets': [dict(difficulty='remaster', internalLevelValue=14.8)]})
        rows = self.renderer.render_template.call_args.kwargs['played_rows']
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]['constant'], rows[0]['text_color'], rows[0]['card']), ('14.8', '#72148d', ''))

    def test_record_labels_and_cards_use_the_requested_language(self):
        for language in ('ja', 'en'):
            self.namespace['_makeup_played_data'](
                [{'difficulty': 'master'}],
                {'sheets': [dict(difficulty='master', internalLevelValue=14)]}, language)
            data = self.renderer.render_template.call_args.kwargs
            self.assertEqual(data['heading'], ('records', language))
            self.assertEqual(data['empty_text'], ('unplayed', language))
            self.assertEqual(self.records.thumbnail_html.call_args.kwargs['language'], language)
