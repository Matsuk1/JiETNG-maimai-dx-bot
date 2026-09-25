from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from modules.images import skins as image_skins
from modules.images.renderer import template


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


def test_glass_skin_overrides_and_default_fallback():
    assert image_skins.resolve_template('records.html', 'glass') == 'skins/glass/records.html'
    assert image_skins.resolve_template('document.html', 'glass') == 'document.html'
    html = template('records.html', skin='glass', title='<script>unsafe</script>',
                    stats=[], rating='12345', equation='', details=[], up=['card'], down=[],
                    texts={'heading': 'Play records', 'tracks': 'tracks'})
    assert '&lt;script&gt;' in html
    assert '<script>' not in html
    assert 'glass-records' in html


def test_glass_thumbnail_cover_does_not_expose_white_card_corners():
    html = template('thumbnail.html', skin='glass', song={
        'name': 'Sample', 'score': '100.0000%', 'dx_score': '1000 / 1000',
        'difficulty': 'master', 'internalLevelValue': 14.0, 'ra': 300,
    }, inline=False, icons={}, cover='<div class="plain-cover"></div>',
                    color='#9f51dc', text_color='white', version='Sample')
    assert '.glass-card-cover {' in html
    assert 'border-radius: 12px;' in html
    assert 'class="glass-card-cover-content"' in html
    assert 'class="plain-cover"' in html
    assert 'class="glass-cover"' not in html


def test_nested_skin_scope_is_isolated_and_restored_on_error():
    from modules.images.skins import use_skin, current_skin, skinnable

    @skinnable
    def nested():
        return current_skin()

    def render(skin):
        with use_skin(skin):
            assert nested() == skin
            assert nested(skin='default') == 'default'
            assert current_skin() == skin
            try:
                with use_skin('temporary'):
                    raise ValueError('render failure')
            except ValueError:
                pass
            return current_skin()

    with ThreadPoolExecutor(max_workers=4) as pool:
        assert list(pool.map(render, ['glass', 'default'] * 8)) == ['glass', 'default'] * 8
    assert current_skin() == 'default'


def test_glass_cover_dimensions_inside_version_grid():
    import os
    import pytest
    if os.getenv('JIETNG_RENDER_TESTS') != '1':
        pytest.skip('requires installed Chromium')
    from playwright.sync_api import sync_playwright
    from modules.images.renderer import file_uri
    asset = file_uri('assets/pics/logo.png')
    cover = template('cover.html', skin='glass', cover=asset, type_src=asset,
                     status='', difficulty='master', color='#9f51dc', footer=True,
                     title='Sample', achieved=False, plate=False)
    page_html = template('progress.html', skin='glass', mode='version', title='',
                         title_src='', plates=[], rows=[('14', [cover])], markup=True,
                         margin=20, max_per_row=10)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.set_content(template('document.html', body=page_html, width=1820,
                                  font=file_uri('assets/fonts/line_seed_jietng.ttf')))
        assert page.locator('.glass-cover-type').bounding_box()['width'] == 68
        assert page.locator('.glass-cover-type').bounding_box()['height'] == 20
        assert page.locator('.glass-cover-art').bounding_box()['width'] == 144
        browser.close()


def test_glass_profile_preserves_original_geometry():
    import os
    import pytest
    if os.getenv('JIETNG_RENDER_TESTS') != '1':
        pytest.skip('requires installed Chromium')
    from playwright.sync_api import sync_playwright
    from modules.images.renderer import file_uri
    asset = file_uri('assets/pics/logo.png')
    assets = {key: asset for key in ['nameplate_url', 'icon_url', 'rating_block_path',
                                    'class_rank_url', 'cource_rank_url', 'trophy_url']}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        layouts = []
        for skin in ['default', 'glass']:
            body = template('profile.html', skin=skin, assets=assets, scale=1,
                            user=dict(name='Sample', trophy_content='Trophy'),
                            rating='15678', rounded_icon=False)
            page.set_content(template('document.html', body=body, width=1363, height=218,
                                      font=file_uri('assets/fonts/line_seed_jietng.ttf')))
            page.evaluate('document.fonts.ready')
            layouts.append(page.locator('.profile-card').evaluate('''root =>
                [...root.querySelectorAll('img, div, span')].map(el => {
                    const r = el.getBoundingClientRect();
                    return [r.x, r.y, r.width, r.height];
                })'''))
        assert layouts[0] == layouts[1]
        browser.close()
