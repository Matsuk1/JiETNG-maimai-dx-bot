from unittest.mock import Mock, patch

import pytest
from flask import Flask

from modules.api import admin_api as admin


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
