"""Offline, synthetic visual fixtures. --ref loads renderers from a local Git revision."""
import ast
import argparse
import subprocess
import types
import copy
import logging
import sys
from pathlib import Path
from io import BytesIO
from unittest.mock import patch
sys.path.insert(0, str(Path.cwd()))
from PIL import Image
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', required=True, type=Path)
parser.add_argument('--profile-assets', type=Path, default=Path('artifacts/image-migration/profile-assets'))
parser.add_argument('--ref', help='Local Git revision for the before images')
args = parser.parse_args()
OUT = args.output
OUT.mkdir(parents=True, exist_ok=True)
revision = None
if args.ref:
    revision = subprocess.check_output(['git', 'rev-parse', '--verify', args.ref + '^{commit}'], text=True).strip()
    import modules
    archived_files = set(subprocess.check_output(
        ['git', 'ls-tree', '-r', '--name-only', revision, 'modules'], text=True).splitlines())
    for name in ('user_image_skin', 'profile_generator', 'static_image_generator',
                 'image_manager', 'record_generator', 'song_generator'):
        if f'modules/{name}.py' not in archived_files:
            continue
        source = subprocess.check_output(['git', 'show', f'{revision}:modules/{name}.py'], text=True)
        module = types.ModuleType('modules.' + name)
        module.__file__ = str(Path('modules') / (name + '.py'))
        sys.modules[module.__name__] = module
        setattr(modules, name, module)
        exec(compile(source, module.__file__, 'exec'), module.__dict__)
from modules import record_generator as r, song_generator as s, image_manager as m
from modules.config_loader import read_dxdata
cover_path = next(iter(sorted(Path('assets/covers').glob('*.png'))), Path('assets/pics/404.png'))
cover = Image.open(cover_path).convert('RGBA')
songs = copy.deepcopy(read_dxdata('jp')[0][:18])
for song in songs:
    song['cover_name'] = cover_path.name
    song['cover_url'] = None
records = []
for i, song in enumerate(songs):
    records.append(dict(song, name=song['title'], score='100.1234%', dx_score='1234 / 1300', dx_percentage=.949, difficulty=['basic','advanced','expert','master','remaster'][i%5], internalLevelValue=13.7, ra=305, score_icon='sssp', combo_icon='fcp', sync_icon='fdx', dx_star='4', play_count=12, last_play_time='2026/09/15'))

def save(name, img):
    img.save(OUT / (name + '.png')); print(name, img.size, flush=True); img.close()

def cached(url, path):
    if Path(path).is_file():
        with Image.open(path) as im: return im.convert('RGBA')
    return None

with patch('modules.image_cache.download_and_cache_icon', side_effect=cached), patch.object(r,'download_and_cache_icon',side_effect=cached,create=True):
    save('song', s.song_info_generate(songs[0]))
    save('song_played', s.song_info_generate(songs[0], records[:3]))
    save('records', r.generate_records_picture(records[:10], records[10:15], title='B50'))
    save('records_details', r.generate_records_picture(records[:5], title='LIST', details={'Difficulty':'master remaster','Level':'13+', 'Played':'Yes'}))
    targets = [dict(img=r.generate_cover(None,'dx',cover_name=cover_path.name,difficulty=rec['difficulty'],achieved=i%2==0,song_title=rec['name']),level='14' if i<9 else '13+', internal_level=14.1 if i<9 else 13.8,achieved=i%2==0,achievement_rate=100-i/100) for i,rec in enumerate(records)]
    save('progress', r.generate_level_rank_progress_image(targets,'13+ / 14','SSS',dict(achieved=9,unachieved=7,unplayed=2,total=18)))
    save('plate',r.generate_plate_image(targets,'舞神',headers={key:dict(clear=12,all=18) for key in ['basic','advanced','expert','master']}))
    save('version',s.generate_version_list(songs,{'version':'maimai', 'abbr':'真'}))
    result = dict(parsed=dict(title='君の知らない物語',achievement=99.1234,sub_judgement={key:dict(critical_perfect=100,perfect=5,great=2,good=1,miss=0) for key in ['tap','hold','slide','touch','break']}),validation=dict(difficulty='master',type='dx',cover_name=cover_path.name,internal_level=13.7,loss_percentages={f'{k}_{v}':.01 for k in ['tap','hold','slide','touch'] for v in ['great','good','miss']}))
    save('score',r.generate_score_recognition_picture(result))
    save('footer',m.compose_images([cover],bg_filter=None))
    save('background',m.compose_images([cover],bg_filter={'files':['kaf.jpg'], 'blur':20, 'overlay':40}))
    save('thumbnail_two_icons',r.create_thumbnail(records[3]))
    save('inline_two_icons',r.create_thumbnail_in_line(records[3]))
    long_song = copy.deepcopy(songs[0]); long_song['title'] = '長い曲名 / 超长标题 / A very long song title ' * 4
    long_song['artist'] = '<script>alert(1)</script> & Artist'
    save('song_long_title',s.song_info_generate(long_song, ver='intl'))
    save('score_empty',r.generate_score_recognition_picture({}, ver='intl'))
    for item in targets: item['img'].close()
# Isolate profile rendering from main.py application startup.
source = subprocess.check_output(['git','show',f'{revision}:main.py'], text=True) if revision else Path('main.py').read_text()
fn=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='generate_profile')
fn.decorator_list = []
profile_files = {'fixture:nameplate': Path('data/images/keep_nameplate.png'),
                 'fixture:class': args.profile_assets / 'class.png',
                 'fixture:course': args.profile_assets / 'course.png',
                 'fixture:trophy': args.profile_assets / 'trophy.png'}
class Response:
    def __init__(self, url): self.url=url
    def __enter__(self): return self
    def __exit__(self,*args): pass
    def raise_for_status(self): pass
    @property
    def content(self):
        path=profile_files.get(self.url)
        if path and path.is_file(): return path.read_bytes()
        out=BytesIO(); cover.save(out,format='PNG'); return out.getvalue()
class Requests:
    def get(self,url,**kw): return Response(url)
ns=dict(Image=Image,BytesIO=BytesIO,requests=Requests(),logger=logging.getLogger('preview'))
ns.update({key:getattr(m,key) for key in ['font_profile','font_trophy','round_corner','truncate_text'] if hasattr(m,key)})
from PIL import ImageDraw
ns['ImageDraw']=ImageDraw
exec(compile(ast.Module(body=[fn],type_ignores=[]),'profile','exec'),ns)
with patch('requests.get', side_effect=Requests().get):
    save('profile',ns['generate_profile'](dict(name='JiETNG サンプル',rating='15678',trophy_content='舞い踊る挑戦者',icon_url='fixture',nameplate_url='fixture:nameplate', class_rank_url='fixture:class', cource_rank_url='fixture:course', trophy_url='fixture:trophy',rating_block_path='assets/pics/rating/gold_2.png')))

if revision:
    from io import BytesIO
    with Image.open(BytesIO(subprocess.check_output(['git','show',f'{revision}:assets/pics/404.png']))) as im:
        save('404', im.copy())
else:
    from generate_404 import generate_404
    generate_404(OUT / '404.png')
cover.close()

if revision:
    source = subprocess.check_output(['git','show',f'{revision}:main.py'], text=True)
    fn = next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='admin_pwa_icon')
    fn.decorator_list = []
    ns = dict(Image=Image, BytesIO=BytesIO, LOGO_FILE='assets/pics/logo.png', send_file=lambda buf, **kw: buf)
    exec(compile(ast.Module(body=[fn],type_ignores=[]),'admin_icon','exec'),ns)
    with Image.open(ns['admin_pwa_icon']()) as im:
        save('admin_icon', im.copy())
else:
    from modules.image_manager import admin_icon_png
    with Image.open(BytesIO(admin_icon_png('assets/pics/logo.png'))) as im:
        save('admin_icon', im.copy())
