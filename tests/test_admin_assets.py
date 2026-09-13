from pathlib import Path
import re
import unittest
from flask import Flask, render_template

ROOT = Path(__file__).resolve().parents[1]

class AdminAssetTests(unittest.TestCase):
    def test_template_renders_config_and_serves_extracted_assets(self):
        source=(ROOT/'templates/admin_panel.html').read_text()
        stats={key:0 for key in re.findall(r'stats\.([a-zA-Z_0-9]+)',source)}
        stats.update(dau_30d=[],image_command_breakdown=[])
        app=Flask(__name__,template_folder=str(ROOT/'templates'),static_folder=str(ROOT/'assets'),static_url_path='/static')
        with app.test_request_context():
            html=render_template('admin_panel.html',stats=stats,total_users=0,logs='',language_options=[],default_language='ja',csrf_token=lambda:'csrf-test-token')
        self.assertIn('csrf-test-token',html)
        self.assertLess(html.index('window.JIETNG_ADMIN_CONFIG'),html.index('src="/static/admin-panel.js"'))
        for name in ('admin-panel.css','admin-monitor.css','admin-panel.js','admin-user-editor.js'):
            self.assertIn('/static/'+name,html)
            response=app.test_client().get('/static/'+name)
            self.assertEqual(response.status_code,200)
            response.close()
