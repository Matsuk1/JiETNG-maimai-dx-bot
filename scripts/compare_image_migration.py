"""Build an offline comparison gallery and paired PNGs from matching fixtures."""
import argparse
import html
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import Image
from modules.html_renderer import file_uri, render_html

LABELS = {
    'song':'单曲信息', 'song_played':'单曲成绩', 'records':'成绩列表',
    'records_details':'带筛选详情的成绩列表', 'progress':'等级与评级进度', 'plate':'牌子进度',
    'version':'版本歌曲列表', 'score':'识别结果分析', 'footer':'页脚',
    'background':'模糊背景', 'profile':'完整用户资料卡', 'thumbnail_two_icons':'小卡片：双图标与定数',
    'inline_two_icons':'横向卡片：双图标与定数', 'song_long_title':'长标题与特殊字符',
    'score_empty':'空识别结果', '404':'404 占位图', 'admin_icon':'后台 PWA 图标',
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    root = args.directory.resolve()
    output = root / 'comparisons'; output.mkdir(exist_ok=True)
    items = []
    for name, label in LABELS.items():
        before, after = root / 'before' / f'{name}.png', root / 'after' / f'{name}.png'
        if not before.is_file() or not after.is_file():
            continue
        with Image.open(before) as im: before_size = im.size
        with Image.open(after) as im: after_size = im.size
        body = f'''<section style="background:#eef1f6;padding:28px;color:#17223b">
            <div style="font-size:34px;margin-bottom:10px">{html.escape(label)}</div>
            <div style="font-size:18px;color:#526078;margin-bottom:22px">同一组样例数据 · 左：迁移前 / Pillow　右：迁移后 / HTML + CSS + Playwright</div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:24px;align-items:start">
            <div><div style="font-size:22px;margin-bottom:12px">迁移前 · {before_size[0]} × {before_size[1]}</div><img src="{file_uri(before)}" style="width:100%;height:auto;background:white;border:1px solid #ccd3e0"></div>
            <div><div style="font-size:22px;margin-bottom:12px">迁移后 · {after_size[0]} × {after_size[1]}</div><img src="{file_uri(after)}" style="width:100%;height:auto;background:white;border:1px solid #ccd3e0"></div>
            </div></section>'''
        with render_html(body, 1800) as im:
            im.save(output / f'{name}.png')
        items.append(f'<section id="{name}"><h2>{html.escape(label)}</h2><a href="comparisons/{name}.png"><img loading="lazy" src="comparisons/{name}.png"></a><p><a href="before/{name}.png">迁移前原图</a> · <a href="after/{name}.png">迁移后原图</a></p></section>')
        print(name, flush=True)
    links = ' · '.join(f'<a href="#{name}">{label}</a>' for name,label in LABELS.items())
    page = '''<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>JiETNG 图片迁移对比</title><style>body{margin:0;padding:32px;background:#eef1f6;color:#17223b;font:16px/1.6 system-ui,sans-serif}main{max-width:1800px;margin:auto}section{margin:36px 0}img{display:block;width:100%;height:auto}a{color:#405cc3}nav{line-height:2.2}h1{margin-bottom:8px}</style><main><h1>JiETNG 图片迁移对比</h1><p>左侧为迁移前，右侧为迁移后。使用固定的公开歌曲数据与合成成绩，封面是统一的示例素材，不是用户真实成绩。可点击图片查看大图。</p><p>重点调整：定数与 Rating 下移 5px；横向卡片增加双图标间距；资料卡文字基线与描边对齐旧版。</p><nav>''' + links + '</nav>' + ''.join(items) + '</main></html>'
    (root / 'index.html').write_text(page)


if __name__ == '__main__':
    main()
