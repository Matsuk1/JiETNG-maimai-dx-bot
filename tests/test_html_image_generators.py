import unittest
from unittest.mock import patch
from PIL import Image

from modules.images import records as records
from modules.images import composition as image_manager
from modules.images.records import thumbnail_html


class ImageDataTests(unittest.TestCase):
    def test_record_totals_and_escaping(self):
        record = dict(ra=305, internalLevelValue=13.7, score='100.1234%')
        with patch('modules.images.records.thumbnail_html', return_value='card'), patch('modules.images.renderer.render_template') as render:
            records.generate_records_picture([record, record], [record], title='<script>x</script>')
        values = render.call_args.kwargs
        self.assertEqual(values['rating'], '  915')
        self.assertEqual(values['equation'], '= 610 + 305')
        self.assertEqual([value for _, value in values['stats']], ['13.70', '100.1234%', '305.00'])
        self.assertIsNone(records.generate_records_picture())

    def test_group_order_and_completed_first(self):
        with Image.new('RGBA', (150, 180)) as im:
            data = [dict(img=im, level='13+', internal_level=13.8, achieved=False, achievement_rate=100),
                    dict(img=im, level='14', internal_level=14.2, achieved=True, achievement_rate=99)]
            with patch('modules.images.renderer.render_template') as render:
                records.generate_level_rank_progress_image(data, '13–14', 'SSS',
                    dict(achieved=1, unachieved=1, unplayed=0, total=2))
            self.assertEqual([label for label, _ in render.call_args.kwargs['rows']], ['14.2', '13.8'])
            self.assertEqual(render.call_args.kwargs['cards'][0][1], '1 (50.0%)')

    def test_two_icons_and_user_text_are_safe(self):
        record = dict(name='<img src=x>', version='test', score='100.0000%', dx_score='1500',
                      difficulty='master', internalLevelValue=14.1, ra=315,
                      combo_icon='fcp', sync_icon='fdx', dx_star='5')
        with patch('modules.images.records.icon_uri', side_effect=lambda v,*_: 'data:' + v), patch('modules.images.records.cover_html', return_value=''):
            html = thumbnail_html(record)
        self.assertIn('data:fcp', html)
        self.assertIn('data:fdx', html)
        self.assertIn('&lt;img src=x&gt;', html)
        self.assertNotIn('<img src=x>', html)

    def test_owned_sources_closed_on_render_failure(self):
        im = Image.new('RGBA', (40, 40))
        with patch('modules.images.composition.compose_images', side_effect=RuntimeError('failed')):
            with self.assertRaises(RuntimeError):
                image_manager.compose_generated_images([im, im])
        with self.assertRaises(ValueError):
            im.getpixel((0, 0))

    def test_break_loss_totals_preserved(self):
        result = dict(parsed=dict(achievement=99, sub_judgement={'tap': {'great': 2}}),
                      validation=dict(difficulty='master', internal_level=13,
                        loss_percentages={'tap_great': .02},
                        break_detail=dict(perfect_high=2, loss_percentages={'perfect_high': .003})))
        with patch('modules.images.renderer.render_template') as render, patch.object(records, 'compose_generated_images'):
            records.generate_score_recognition_picture(result)
        panels = render.call_args.kwargs['panels']
        self.assertEqual(panels[0]['total'], '-0.04000%')
        self.assertEqual(panels[1]['total'], '-0.00600%')

    def test_invalid_columns_rejected_before_grouping(self):
        for columns in (0, -1):
            with self.subTest(columns=columns), self.assertRaisesRegex(ValueError, 'max_per_row'):
                records.generate_level_rank_progress_image(
                    [{}], '14', 'SSS', {}, max_per_row=columns)

    def test_low_levels_grouped_by_constant_without_mutating_input(self):
        data = [dict(img='a', level='9', internal_level=9.1, achieved=True, achievement_rate=100),
                dict(img='b', level='9+', internal_level=9.8, achieved=False, achievement_rate=99),
                dict(img='c', level='10', internal_level=10.0, achieved=True, achievement_rate=100),
                dict(img='d', level='9+', internal_level=9.8, achieved=True, achievement_rate=98)]
        with patch('modules.images.renderer.image_uri', side_effect=lambda image: image), \
             patch('modules.images.renderer.render_template') as render:
            records.generate_level_rank_progress_image(
                data, 'ALL', '', dict(achieved=3, unachieved=1, unplayed=0, total=4), group_by='level')
        self.assertEqual(render.call_args.kwargs['rows'], [('10', ['c']), ('10-', ['d', 'b', 'a'])])
        self.assertEqual([entry['img'] for entry in data], ['a', 'b', 'c', 'd'])

    def test_version_rows_sorted_by_level_constant_and_title(self):
        from modules.images import songs
        source = [dict(title=title, sheets=[dict(difficulty='master', level=level, internalLevelValue=constant)])
                  for title, level, constant in [('Z', '13', 13.1), ('A', '13', 13.1), ('B', '14+', 14.7)]]
        source.append(dict(title='No master', sheets=[]))
        with patch('modules.images.records.cover_html', side_effect=lambda *args, **kw: kw['song_title']), \
             patch('modules.images.renderer.render_template') as render:
            songs.generate_version_list(source)
        self.assertEqual(render.call_args.kwargs['rows'], [('14+', ['B']), ('13', ['A', 'Z'])])
