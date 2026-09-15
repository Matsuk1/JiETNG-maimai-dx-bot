"""Opt-in real Chromium checks: JIETNG_RENDER_TESTS=1 python -m unittest discover ..."""
import os
import unittest
from concurrent.futures import ThreadPoolExecutor

from modules.html_renderer import render_html, template


@unittest.skipUnless(os.getenv('JIETNG_RENDER_TESTS') == '1', 'requires installed Chromium')
class HtmlRendererTests(unittest.TestCase):
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


class TemplateTests(unittest.TestCase):
    def test_song_data_is_escaped(self):
        html = template('song.html', mode='basic', title='<script>alert(1)</script>',
                        cover='', info=[('Artist', '<img src=x>')])
        self.assertNotIn('<script>', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertIn('&lt;img src=x&gt;', html)
