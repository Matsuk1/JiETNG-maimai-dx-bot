from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from modules import image_skins
from modules.html_renderer import template


def test_registered_overrides_fallback_and_path_safety(tmp_path):
    skin = tmp_path / 'sample'
    skin.mkdir()
    (skin / 'skin.json').write_text('{"label":"Sample"}')
    (skin / 'records.html').write_text('example')
    with patch.object(image_skins, 'SKINS', tmp_path):
        assert image_skins.resolve_template('records.html', 'sample') == 'skins/sample/records.html'
        assert image_skins.resolve_template('profile.html', 'sample') == 'profile.html'
        for invalid in ('unknown', '../sample', '/tmp/sample', None):
            assert image_skins.resolve_template('records.html', invalid) == 'records.html'
        assert image_skins.resolve_template('../records.html', 'sample') == '../records.html'


def test_skin_selection_does_not_leak_between_callers():
    def render(skin):
        return template('stack.html', skin=skin, images=[])
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(render, ['default', 'missing'] * 8))
    assert len(set(results)) == 1
