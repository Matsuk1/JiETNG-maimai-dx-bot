import re
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from bs4 import BeautifulSoup
from flask import Flask, render_template

from modules.api import admin_api as admin
from modules.notice_manager import summarize_notices


# Every endpoint whose inline auth guard was consolidated.
PROTECTED_ENDPOINTS = """
admin_api_overview
admin_api_hourly
admin_api_tasks
admin_api_users
admin_trigger_update
admin_get_logs
admin_ai_monitor_query
admin_ai_monitor_result
admin_ai_monitor_reset_session
admin_ai_monitor_image
admin_get_notices
admin_create_notice
admin_update_notice
admin_delete_notice
admin_publish_notice
admin_get_notice_stats
admin_get_tip_ads
admin_get_tip_ad
admin_create_tip_ads
admin_put_tip_ads
admin_delete_tip_ads
admin_backgrounds
admin_delete_background
admin_delete_user
admin_clear_cache
admin_get_user_data
admin_load_nicknames
admin_create_backup
admin_get_backups
admin_download_backup
admin_delete_backup
admin_dxdata_status
admin_update_dxdata
admin_dxdata_audit
admin_dxdata_audit_correction
admin_dxdata_audit_versions
admin_get_notifications
admin_clear_notifications
admin_vapid_public_key
admin_add_push_subscription
admin_remove_push_subscription
admin_list_devtokens
admin_create_devtoken
admin_update_devtoken
admin_delete_devtoken
""".split()


@pytest.fixture
def app():
    application = Flask(__name__)
    application.secret_key = 'test-only-key'
    application.register_blueprint(admin.admin_api)
    return application


@pytest.mark.parametrize('name', PROTECTED_ENDPOINTS)
def test_denied_endpoints_keep_http_contract(app, name):
    # Blueprint names need not match the Python module name.
    endpoint = next(key for key in app.view_functions if key.endswith('.' + name))
    rule = next(rule for rule in app.url_map.iter_rules() if rule.endpoint == endpoint)
    with app.test_request_context():
        from flask import url_for
        url = url_for(endpoint, **{argument: 'fixture' for argument in rule.arguments})
    method = next(m for m in sorted(rule.methods) if m not in ('HEAD', 'OPTIONS'))
    with patch.object(admin, 'check_admin_auth', return_value=False) as check:
        response = app.test_client().open(url, method=method)
    assert response.status_code == 401
    assert response.json == {'error': 'Unauthorized'}
    check.assert_called_once_with()


def test_auth_wrapper_runs_body_once_and_preserves_endpoint(app):
    body = Mock(return_value='ok')
    def endpoint(value):
        return body(value)
    wrapped = admin.require_admin(endpoint)
    assert wrapped.__name__ == 'endpoint'
    with app.test_request_context(), patch.object(admin, 'check_admin_auth', return_value=True) as check:
        assert wrapped('value') == 'ok'
    check.assert_called_once_with()
    body.assert_called_once_with('value')


def test_real_admin_session_and_local_bridge_rules(app):
    from flask import session
    with app.test_request_context():
        session['admin_authenticated'] = True
        assert admin.check_admin_auth() is True
    with app.test_request_context(headers={'X-JiETNG-Monitor-Token': 'valid'}, environ_base={'REMOTE_ADDR': '127.0.0.1'}):
        with patch.object(admin, 'verify_service_bridge_token', return_value=True) as verify:
            assert admin.check_admin_auth() is True
            verify.assert_called_once_with('valid')
    with app.test_request_context(headers={'X-JiETNG-Monitor-Token': 'valid'}, environ_base={'REMOTE_ADDR': '203.0.113.5'}):
        with patch.object(admin, 'verify_service_bridge_token', return_value=True) as verify:
            assert admin.check_admin_auth() is False
            verify.assert_not_called()


def test_dxdata_correction_passes_region_and_selection(app):
    client = app.test_client()
    with client.session_transaction() as session:
        session['admin_authenticated'] = True
    payload = {'revision': 'r', 'region': 'intl', 'issue_index': 2, 'song_id': 'abc',
               'difficulty': 'master', 'field': 'internalLevelValue', 'value': '13.4'}
    with patch.object(admin, 'save_music_level_correction', return_value={'status': 'complete'}) as save:
        response = client.post('/admin/dxdata_audit/correction', json=payload)
    assert response.status_code == 200
    save.assert_called_once_with('r', 'intl', 2, 'abc', 'master', 'internalLevelValue', '13.4')


def test_dxdata_writes_require_csrf(app):
    from flask_wtf.csrf import CSRFProtect
    CSRFProtect(app)
    client = app.test_client()
    with client.session_transaction() as session:
        session['admin_authenticated'] = True
    for path in ('/admin/dxdata_audit', '/admin/dxdata_audit/correction', '/admin/dxdata_audit/versions'):
        assert client.post(path, json={}).status_code == 400


def test_bulk_versions_passes_revision_and_region(app):
    client = app.test_client()
    with client.session_transaction() as session:
        session['admin_authenticated'] = True
    with patch.object(admin, 'save_music_version_corrections', return_value={'status': 'complete'}) as save:
        response = client.post('/admin/dxdata_audit/versions', json={'revision': 'r', 'region': 'intl'})
    assert response.status_code == 200
    save.assert_called_once_with('r', 'intl')


def test_dxdata_note_check_needs_no_sega_credentials(app):
    client = app.test_client()
    with client.session_transaction() as session:
        session['admin_authenticated'] = True
    with patch.object(admin, 'start_note_count_check', return_value='notes-job') as start:
        response = client.post('/admin/dxdata_audit', json={'mode': 'notes'})
    assert response.status_code == 202
    assert response.json['id'] == 'notes-job'
    start.assert_called_once_with()


def test_note_correction_uses_report_not_client_values(app):
    client = app.test_client()
    with client.session_transaction() as session:
        session['admin_authenticated'] = True
    with patch.object(admin, 'save_note_count_correction', return_value={'status': 'complete'}) as save:
        response = client.post('/admin/dxdata_audit/correction', json={
            'revision': 'r', 'issue_index': 3, 'song_id': 'a', 'difficulty': 'master',
            'field': 'noteCounts', 'value': -999})
    assert response.status_code == 200
    save.assert_called_once_with('r', 3, 'a', 'master')


def test_notice_stats_share_one_user_snapshot():
    users = {
        'a': {'notice_interactions': {'n1': {'read': True, 'vote': 'support'}, 'n2': {'read': True}}},
        'b': {'notice_interactions': {'n1': {'read': True, 'vote': 'oppose'}, 'deleted': {'read': True}}},
        'c': {},
    }
    result = summarize_notices(['n1', 'n2', 'n3'], users)
    assert result['n1'] == dict(total_users=3, read_count=2, support_count=1,
                                oppose_count=1, read_percentage=66.67,
                                vote_percentage=100.0, no_vote_count=0)
    assert result['n2']['no_vote_count'] == 1
    assert result['n3']['read_percentage'] == 0
    assert summarize_notices(['n'], {})['n']['vote_percentage'] == 0


def test_admin_template_renders_config_and_serves_assets():
    root = Path(__file__).resolve().parents[1]
    source = (root / 'templates/admin_panel.html').read_text()
    stats = {key: 0 for key in re.findall(r'stats\.([a-zA-Z_0-9]+)', source)}
    stats.update(dau_30d=[], image_command_breakdown=[], memory_components=[
        dict(key='ocr', name='OCR', description='Table OCR', memory_mb=512, percent=50),
        dict(key='playwright', name='Playwright', description='Browser', memory_mb=256, percent=25),
    ])
    application = Flask(__name__, template_folder=str(root / 'templates'),
                        static_folder=str(root / 'assets'), static_url_path='/static')
    with application.test_request_context():
        html = render_template('admin_panel.html', stats=stats, total_users=0, logs='',
                               language_options=[], default_language='ja',
                               csrf_token=lambda: 'csrf-test-token')
    page = BeautifulSoup(html, 'html.parser')
    runtime = page.find('h2', string='Runtime Pressure').find_parent('section')
    assert 'csrf-test-token' in html
    assert len(runtime.select('[data-memory-component]')) == 2
    assert '512 MiB' in runtime.get_text()
    assert page.select_one('.process-memory-panel') is None
    assert 'Process Memory' in page.select_one('.system-summary').get_text()
    assert html.index('window.JIETNG_ADMIN_CONFIG') < html.index('src="/static/admin-panel.js?')
    assert '/static/admin-panel.css?v=' in html
    for name in ('admin-panel.css', 'admin-monitor.css', 'admin-panel.js', 'admin-user-editor.js'):
        assert '/static/' + name in html
        response = application.test_client().get('/static/' + name)
        assert response.status_code == 200
        response.close()
