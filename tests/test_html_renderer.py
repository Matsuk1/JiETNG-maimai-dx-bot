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
        rebuilt = threading.Event()
        original_ensure = renderer._ensure_page
        browsers = []

        def ensure(width, height):
            original_ensure(width, height)
            if not browsers or browsers[-1] is not renderer._browser:
                browsers.append(renderer._browser)
            if len(browsers) >= 2:
                rebuilt.set()

        with patch.object(renderer, 'RENDERER_IDLE_SECONDS', 0.1), \
             patch.object(renderer, '_ensure_page', side_effect=ensure):
            try:
                renderer.warm_renderer()
                self.assertEqual(len(browsers), 1)
                self.assertTrue(rebuilt.wait(timeout=5), 'browser was not rebuilt without a new request')
                self.assertFalse(browsers[0].is_connected())
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

    def test_batched_font_fit_matches_stepwise_sizes(self):
        from modules.images import renderer
        text = 'A long title that must fit inside a narrow card'
        body = ''.join(
            f'<div data-fit="12" style="width:{width}px;font-size:32px;white-space:nowrap">{text}</div>'
            for width in (45, 150, 300, 900)
        )
        # Inspect on the renderer worker thread through its screenshot hook.
        from unittest.mock import patch
        screenshot = renderer._screenshot
        checked = []

        def inspect(body, width, height):
            # The normal cleanup clears the DOM, so capture measurements just
            # before screenshot through a temporary wrapper of page.evaluate.
            renderer._ensure_page(width, height)
            evaluate = renderer._page.evaluate
            def evaluate_and_check(script, *args):
                result = evaluate(script, *args)
                if 'Binary-search all overflowing labels' in script:
                    checked.extend(evaluate("""() => [...document.querySelectorAll('[data-fit]')].map(el => {
                        const actual = parseFloat(el.style.fontSize || '32');
                        let expected = 32;
                        el.style.fontSize = '32px';
                        while (el.scrollWidth > el.clientWidth && expected > 12) {
                            el.style.fontSize = `${--expected}px`;
                        }
                        return [actual, expected];
                    })"""))
                return result
            with patch.object(renderer._page, 'evaluate', side_effect=evaluate_and_check):
                return screenshot(body, width, height)
        with patch.object(renderer, '_screenshot', side_effect=inspect):
            with render_html(body, 950):
                pass
        self.assertEqual(len(checked), 4)
        self.assertTrue(all(actual == expected for actual, expected in checked), checked)

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
