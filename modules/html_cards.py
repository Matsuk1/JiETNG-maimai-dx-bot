"""Reusable card markup. Asset fetching stays in the existing image cache."""
from pathlib import Path
from modules.html_renderer import file_uri, image_uri, template
from modules import image_cache
from modules.config_loader import (COVERS_DIR, ICON_TYPE_DIR, ICON_BASE_DIR, ICON_SCORE_DIR,
    ICON_COMBO_DIR, ICON_SYNC_DIR, ICON_COMBO_RCD_DIR, ICON_SYNC_RCD_DIR, ICON_DX_STAR_DIR)


def difficulty_color(difficulty):
    return {'basic':'#75b520','advanced':'#efa508','expert':'#cc4d59',
            'master':'#9f51dc','remaster':'#e9d4f3','utage':'#f52edd'}.get(str(difficulty).lower(), '#c8c8c8')


def icon_uri(value, directory, url):
    if not value:
        return ''
    path = Path(directory) / f'{value}.png'
    cached = file_uri(path)
    if cached:
        return cached
    image = image_cache.download_and_cache_icon(url, str(path))
    if image is None:
        return ''
    try:
        return image_uri(image)
    finally:
        image.close()


def cover_html(cover_url, type, icon=None, icon_type=None, cover_name=None,
               complete_info=None, difficulty=None, achieved=None, song_title=None, skin=None):
    path = Path(COVERS_DIR) / Path(cover_name).name if cover_name else None
    cover_src = file_uri(path) if path else ''
    if not cover_src:
        cover = image_cache.get_cover_image(cover_url, cover_name)
        try:
            cover_src = image_uri(cover) if cover is not None else ''
        finally:
            if cover is not None:
                cover.close()
    type_src = icon_uri(type, ICON_TYPE_DIR,
                        'https://maimaidx.jp/maimai-mobile/img/music_standard.png' if type == 'std'
                        else 'https://maimaidx.jp/maimai-mobile/img/music_dx.png')
    status = icon_uri(icon, str(Path(ICON_BASE_DIR) / str(icon_type)),
                      f'https://maimaidx.jp/maimai-mobile/img/music_icon_{icon}.png') if icon and icon_type and icon != 'back' else ''
    footer = complete_info is not None or difficulty is not None
    return template('cover.html', skin=skin, cover=cover_src, type_src=type_src, status=status,
                    color=difficulty_color(difficulty), difficulty=difficulty,
                    achieved=achieved, footer=footer, plate=complete_info is not None,
                    blocks=[difficulty_color(d) if (complete_info or {}).get(d) else 'white'
                            for d in ('basic','advanced','expert','master')],
                    title=song_title or '', text_color='#72148d' if difficulty == 'remaster' else 'white')


def thumbnail_html(song, inline=False, skin=None):
    icons = {}
    for key, directory, name in (
        ('score_icon', ICON_SCORE_DIR, lambda v: 'playlog/' + v.replace('p','plus')),
        ('combo_icon', ICON_COMBO_RCD_DIR if inline else ICON_COMBO_DIR,
         lambda v: 'playlog/' + v.replace('back','fc_dummy').replace('fcp','fcplus').replace('app','applus') if inline else 'music_icon_' + v),
        ('sync_icon', ICON_SYNC_RCD_DIR if inline else ICON_SYNC_DIR,
         lambda v: 'playlog/' + v.replace('back','sync_dummy').replace('fdx','fsd').replace('p','plus') if inline else 'music_icon_' + v),
        ('dx_star', ICON_DX_STAR_DIR, lambda v: 'music_icon_dxstar_detail_' + v),
    ):
        value = song.get(key)
        icons[key] = icon_uri(value, directory, f'https://maimaidx.jp/maimai-mobile/img/{name(str(value))}.png') if value else ''
    cover = '' if inline else cover_html(song.get('cover_url'), song.get('type'), cover_name=song.get('cover_name'), skin=skin)
    return template('thumbnail.html', skin=skin, song=song, inline=inline, icons=icons, cover=cover,
                    color=difficulty_color(song.get('difficulty')),
                    text_color='#72148d' if song.get('difficulty') == 'remaster' else 'white',
                    version=str(song.get('version','')).replace(' PLUS','+').replace('でらっくす','DX'))
