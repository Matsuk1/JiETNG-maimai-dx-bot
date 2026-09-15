"""Local image template workbench. Run with: python -m devtools.image_preview.server"""
import argparse
import copy
from contextlib import ExitStack
import hashlib
from io import BytesIO
import json
from pathlib import Path
import threading
import time
from unittest.mock import patch
from urllib.parse import urlsplit

from flask import Flask, abort, jsonify, request, send_file
from PIL import Image

from modules import html_cards, image_cache, record_generator as records, song_generator as songs
from modules.image_skins import available_skins, use_skin
from modules.html_renderer import file_uri, image_uri, render_template
from modules.image_manager import compose_generated_images

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
FIXTURES = HERE / 'fixtures'
ASSETS = FIXTURES / 'assets'
RENDER_LOCK = threading.Lock()
CASES = {
    'thumbnail': ('小成绩卡片', 'thumbnail.html', '双图标、达成率、定数与 Rating'),
    'inline': ('横向成绩卡片', 'thumbnail.html', '游玩次数、最近游玩、状态图标'),
    'records': ('B50 成绩列表', 'records.html', '35 首旧曲 + 15 首新曲，覆盖五种难度'),
    'profile': ('用户资料卡', 'profile.html', '完整底板、头像、段位与称号'),
    'cover': ('歌曲封面', 'cover.html', '难度边框、完成状态与标题'),
    'song': ('单曲信息', 'song.html', '基本信息与谱面表格'),
    'song_played': ('单曲游玩记录', 'song.html', '歌曲信息与三条游玩记录'),
    'progress': ('等级 / 评级进度', 'progress.html', '按定数分组的完成进度'),
    'plate': ('牌子进度', 'progress.html', '各难度统计与歌曲完成情况'),
    'version': ('版本歌曲列表', 'progress.html', '版本标志、牌子与等级分组'),
    'score': ('识别结果分析', 'score.html', '判定数量、DX 星级和扣分明细'),
    'composition': ('背景与页脚', 'composition.html', '模糊、遮罩、二维码和生成信息'),
}


def clean_data(value):
    """Fixtures resolve only the bundled cover; previews never fetch user URLs."""
    if isinstance(value, dict):
        return {key: (None if key == 'cover_url' else 'cover.png' if key == 'cover_name'
                      else clean_data(item)) for key, item in value.items()}
    if isinstance(value, list):
        if len(value) > 100:
            raise ValueError('每个列表最多支持 100 项示例数据')
        return [clean_data(item) for item in value]
    return value


def render_case(kind, data, skin="default", background=False):
    """Use production generators in this isolated development process."""
    data = clean_data(copy.deepcopy(data))
    sample_bg = {'files': ['kaf.jpg'], 'blur': 12, 'overlay': 60} if background else None
    with RENDER_LOCK, use_skin(skin), ExitStack() as stack:
        # Scope the offline fixture assets to one render, without changing production files.
        stack.enter_context(patch.object(html_cards, 'COVERS_DIR', str(ASSETS)))
        stack.enter_context(patch.object(image_cache, 'COVERS_DIR', str(ASSETS)))
        stack.enter_context(patch.object(image_cache, '_download_rgba', return_value=(None, None)))
        if kind in ('thumbnail', 'inline'):
            fn = records.create_thumbnail if kind == 'thumbnail' else records.create_thumbnail_in_line
            image = fn(data['record'], skin=skin)
        elif kind == 'cover':
            image = records.generate_cover(cover_url=None, **{k:v for k,v in data['cover'].items() if k != 'cover_url'})
        elif kind in ('song', 'song_played'):
            image = songs.song_info_generate(data['song'], played_data=data.get('records', []), ver=data.get('ver', 'jp'), bg_filter=sample_bg)
        elif kind == 'records':
            image = records.generate_records_picture(**dict(data, skin=skin))
            if image is None:
                raise ValueError('成绩列表为空，请至少提供一条成绩')
        elif kind == 'profile':
            scale = float(data.get('scale', 1))
            if not .25 <= scale <= 3:
                raise ValueError('资料卡 scale 范围为 0.25–3')
            assets = {key:file_uri(path) for key,path in {
                'nameplate_url': ASSETS/'nameplate.png', 'icon_url': ASSETS/'cover.png',
                'class_rank_url': ASSETS/'class.png', 'cource_rank_url': ASSETS/'course.png',
                'trophy_url': ASSETS/'trophy.png',
                'rating_block_path': ROOT/'assets/pics/rating/gold_2.png',
            }.items()}
            image = render_template('profile.html', int(1363*scale), int(218*scale),
                user=data['user'], assets=assets, scale=scale, rounded_icon=data.get('rounded_icon', False),
                rating=str(data['user']['rating']).rjust(5))
        elif kind in ('progress', 'plate'):
            targets = []
            for item in data.pop('targets'):
                cover = records.generate_cover(None, item.get('type', 'dx'), cover_name='cover.png',
                    difficulty=item.get('difficulty'), achieved=item.get('achieved'),
                    song_title=item.get('song_title'), complete_info=item.get('complete_info'))
                stack.callback(cover.close)
                targets.append(dict(item, img=cover))
            # Keep debug output bounded while preserving production defaults.
            for key in ('img_width', 'max_per_row', 'margin', 'img_height'):
                data.pop(key, None)
            fn = records.generate_plate_image if kind == 'plate' else records.generate_level_rank_progress_image
            image = fn(targets, **data)
        elif kind == 'version':
            image = songs.generate_version_list(data['songs'], data.get('version_info'), data.get('ver', 'jp'))
        elif kind == 'score':
            image = records.generate_score_recognition_picture(data['result'], ver=data.get('ver', 'jp'), bg_filter=sample_bg)
        elif kind == 'composition':
            # Render a full-width row so the footer has its normal working width.
            card = records.create_thumbnail_in_line(data['record'])
            with card:
                row = card.resize((1200, 450))
            image = compose_generated_images([row], bg_filter=sample_bg if background else data.get('bg_filter'),
                                             timezone_offset=float(data.get('timezone_offset', 9)))
        else:
            raise ValueError('未知示例类型')
        if background and kind not in ('song', 'song_played', 'score', 'composition'):
            image = compose_generated_images([image], bg_filter=sample_bg)
        with image, BytesIO() as output:
            image.save(output, format='PNG')
            return output.getvalue(), image.size


def revision():
    paths = list((ROOT/'templates/images').rglob('*')) + list(FIXTURES.rglob('*'))
    stamps = [(str(p.relative_to(ROOT)), p.stat().st_mtime_ns, p.stat().st_size)
              for p in sorted(paths) if p.is_file()]
    return hashlib.sha256(json.dumps(stamps).encode()).hexdigest()[:16]


def create_app():
    app = Flask(__name__, static_folder=str(HERE/'static'))
    app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024

    @app.before_request
    def local_only():
        if request.host.split(':')[0] not in ('127.0.0.1', 'localhost'):
            abort(403)
        origin = request.headers.get('Origin')
        if origin and urlsplit(origin).netloc != request.host:
            abort(403)

    @app.after_request
    def no_cache(response):
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response

    @app.get('/')
    def index():
        return send_file(HERE/'static/index.html')

    @app.get('/api/skins')
    def skins():
        return jsonify(available_skins())

    @app.get('/api/examples')
    def examples():
        return jsonify([dict(id=key, label=value[0], template='templates/images/'+value[1],
                             description=value[2]) for key,value in CASES.items()])

    @app.get('/api/examples/<kind>')
    def example(kind):
        if kind not in CASES:
            abort(404)
        return jsonify(json.loads((FIXTURES/f'{kind}.json').read_text()))

    @app.get('/api/revision')
    def get_revision():
        return jsonify(revision=revision())

    @app.post('/api/render/<kind>')
    def render(kind):
        if kind not in CASES:
            abort(404)
        data = request.get_json()
        if not isinstance(data, dict):
            return jsonify(error='示例数据必须是 JSON 对象'), 400
        started = time.perf_counter()
        try:
            png, size = render_case(kind, data, skin=request.args.get('skin', 'default'),
                                    background=request.args.get('background') == 'sample')
        except Exception as exc:
            app.logger.warning('Preview failed: %s: %s', type(exc).__name__, exc)
            return jsonify(error=f'{type(exc).__name__}: {exc}'), 422
        response = app.response_class(png, mimetype='image/png')
        response.headers['X-Image-Width'], response.headers['X-Image-Height'] = map(str, size)
        response.headers['X-Render-Ms'] = str(round((time.perf_counter()-started)*1000))
        return response

    return app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=5088)
    args = parser.parse_args()
    import os
    os.chdir(ROOT)
    create_app().run(host='127.0.0.1', port=args.port, threaded=True, debug=False)


if __name__ == '__main__':
    main()
