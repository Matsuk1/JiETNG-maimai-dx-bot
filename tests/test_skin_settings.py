"""Exercise the real settings handler without starting production services."""
import ast
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch
import os

from flask import Flask, request, render_template
from PIL import Image

from modules.image_skins import available_skins, current_skin, normalize_skin
from modules.i18n import normalize_language, DEFAULT_WEB_LANGUAGE
from modules.web_i18n import register_web_i18n
from modules.user_image_skin import user_image

ROOT = Path(__file__).resolve().parents[1]


def settings_app(tmp_path):
    app = Flask(__name__, template_folder=str(ROOT / 'templates'))
    register_web_i18n(app)
    app.jinja_env.globals['csrf_token'] = lambda: 'test'
    user = dict(import_only=True, language='zh', image_skin='default', bg_enabled=True,
                bg_files=['sample.png'], bg_blur=20, bg_overlay=40)
    namespace = dict(request=request, render_template=render_template, os=os,
                     get_user_id_from_settings_token=lambda token: 'user',
                     user_exists=lambda user_id: True, get_user=lambda user_id: user,
                     normalize_language=normalize_language, DEFAULT_WEB_LANGUAGE=DEFAULT_WEB_LANGUAGE,
                     BG_DIR=str(tmp_path), available_skins=available_skins,
                     normalize_skin=normalize_skin, logger=Mock(),
                     edit_user_value=lambda uid,key,value: user.update({key:value}),
                     link_bound_rich_menu=Mock(), load_dev_tokens=lambda: {},
                     generate_perm_token=lambda uid: 'permission', list_import_tokens=lambda uid: [],
                     language_catalog=lambda key: {}, _error_page=lambda *args: ('error',400))
    node = next(node for node in ast.parse((ROOT/'main.py').read_text()).body
                if isinstance(node,ast.FunctionDef) and node.name=='website_settings')
    node.decorator_list=[]
    exec(compile(ast.Module(body=[node],type_ignores=[]), str(ROOT/'main.py'), 'exec'), namespace)
    app.add_url_rule('/linebot/settings',view_func=namespace['website_settings'],methods=['GET','POST'])
    return app,user


def test_settings_roundtrip_and_invalid_skin_fallback(tmp_path):
    app,user=settings_app(tmp_path)
    client=app.test_client()
    response=client.post('/linebot/settings?token=test',data=dict(
        image_skin='glass', language='zh', bg_enabled_hidden='1',bg_files='sample.png',
        bg_blur='12',bg_overlay='30'))
    assert response.status_code==200
    assert user['image_skin']=='glass'
    assert user['bg_files']==['sample.png'] and user['bg_blur']==12
    html=client.get('/linebot/settings?token=test').get_data(as_text=True)
    assert 'value="glass" data-uses-background="true" selected' in html
    client.post('/linebot/settings?token=test',data={'image_skin':'../../private'})
    assert user['image_skin']=='default'


def test_async_request_skin_and_nested_target_are_isolated():
    @user_image
    async def target(user_id):
        await asyncio.sleep(0)
        return current_skin()

    @user_image
    async def operation(user_id):
        first=current_skin()
        nested=await target('different-user')
        await asyncio.sleep(0)
        return first,nested,current_skin()

    async def run():
        return await asyncio.gather(operation('sender'),operation('other'))

    with patch('modules.user_image_skin.user_skin',side_effect=lambda uid:'glass' if uid=='sender' else 'default'):
        assert asyncio.run(run())==[('glass',)*3,('default',)*3]
    assert current_skin()=='default'


def test_background_disabled_skin_does_not_read_background_files():
    from modules.image_manager import compose_images
    with Image.new('RGBA',(20,20),'red') as source:
        with patch('modules.image_manager.skin_config',return_value={'uses_background':False}), \
             patch('modules.image_manager.os.listdir') as scan, \
             patch('modules.html_renderer.render_template',return_value=Image.new('RGBA',(100,200))) as render:
            with compose_images([source],bg_filter={'files':['sample.png'],'blur':12}):
                pass
            scan.assert_not_called()
            assert render.call_args.kwargs['background']==''
