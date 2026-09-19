"""Opt-in real Chromium checks: JIETNG_RENDER_TESTS=1 python -m unittest discover ..."""
import os
import unittest
from concurrent.futures import ThreadPoolExecutor

from modules.images.renderer import render_html, template


@unittest.skipUnless(os.getenv('JIETNG_RENDER_TESTS') == '1', 'requires installed Chromium')
class HtmlRendererTests(unittest.TestCase):
    def test_idle_browser_is_closed_and_recreated(self):
        import threading
        from unittest.mock import patch
        from modules.images import renderer
        renderer.shutdown_renderer()
        closed = threading.Event()
        original_close = renderer._close_browser

        def close():
            had_browser = renderer._browser is not None
            original_close()
            if had_browser:
                closed.set()

        with patch.object(renderer, 'RENDERER_IDLE_SECONDS', 0.1), \
             patch.object(renderer, '_close_browser', side_effect=close):
            try:
                with render_html('<div>First</div>', 100, 40) as image:
                    self.assertEqual(image.size, (100, 40))
                self.assertTrue(closed.wait(timeout=5), 'idle browser was not closed')
                with render_html('<div>Second</div>', 100, 40) as image:
                    self.assertEqual(image.size, (100, 40))
            finally:
                renderer.shutdown_renderer()

    def test_transparency_and_parallel_callers(self):
        def render(_):
            with render_html('<div style="width:20px;height:20px;background:red"></div>', 40, 40) as im:
                self.assertEqual(im.size, (40, 40))
                self.assertEqual(im.getpixel((5, 5)), (255, 0, 0, 255))
                self.assertEqual(im.getpixel((30, 30))[3], 0)
        with ThreadPoolExecutor(max_workers=4) as executor:
            list(executor.map(render, range(8)))

    def test_bad_asset_does_not_poison_next_render(self):
        with self.assertRaises(Exception):
            render_html('<img src="data:image/png;base64,invalid">', 40, 40)
        with render_html('<div>OK</div>', 100) as im:
            self.assertGreater(im.height, 0)

    def test_profile_rating_baseline_matches_pillow(self):
        from modules.images.renderer import render_template, ROOT
        from PIL import ImageFont
        font = ImageFont.truetype(str(ROOT / 'assets/fonts/line_seed_jietng.ttf'), 32)
        expected_top = 28 + font.getbbox('15678')[1]
        with render_template('profile.html', 1363, 218, assets={}, scale=1,
                             user=dict(name='', trophy_content=''), rating='15678', rounded_icon=False) as im:
            with im.crop((359, 0, 474, 82)) as digits:
                actual_top = digits.getchannel('A').getbbox()[1]
        self.assertLessEqual(abs(actual_top - expected_top), 1)


class TemplateTests(unittest.TestCase):
    def test_song_data_is_escaped(self):
        html = template('song.html', mode='basic', title='<script>alert(1)</script>',
                        cover='', info=[('Artist', '<img src=x>')])
        self.assertNotIn('<script>', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertIn('&lt;img src=x&gt;', html)
