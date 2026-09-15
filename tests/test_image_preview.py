import json
from unittest.mock import patch
from devtools.image_preview.server import create_app, CASES, FIXTURES, clean_data


def test_all_fixture_cases_load_without_database_or_network():
    client = create_app().test_client()
    cases = client.get('/api/examples').get_json()
    assert len(cases) == len(CASES)
    for case in cases:
        response = client.get('/api/examples/' + case['id'])
        assert response.status_code == 200
        assert isinstance(response.get_json(), dict)
        assert (FIXTURES / (case['id'] + '.json')).is_file()


def test_invalid_data_and_cross_origin_requests_are_rejected():
    client = create_app().test_client()
    assert client.post('/api/render/thumbnail', json=[]).status_code == 400
    assert client.post('/api/render/unknown', json={}).status_code == 404
    assert client.post('/api/render/thumbnail', json={}, headers={'Origin':'https://example.com'}).status_code == 403
    assert client.get('/', headers={'Host':'example.com'}).status_code == 403
    response = client.post('/api/render/thumbnail', json={})
    assert response.status_code == 422
    assert 'error' in response.get_json()


def test_render_response_and_failure_reporting():
    client = create_app().test_client()
    with patch('devtools.image_preview.server.render_case', return_value=(b'png', (300,150))):
        response = client.post('/api/render/thumbnail', json={'record': {}})
    assert response.headers['X-Image-Width'] == '300'
    assert response.headers['X-Image-Height'] == '150'
    assert response.mimetype == 'image/png'
    assert response.headers['Cache-Control'] == 'no-store'
    with patch('devtools.image_preview.server.render_case', side_effect=ValueError('invalid score')):
        response = client.post('/api/render/thumbnail', json={})
    assert response.status_code == 422
    assert 'invalid score' in response.get_json()['error']


def test_preview_sanitizes_remote_covers_without_mutating_input():
    data = {'record': {'cover_url':'https://example.com/private', 'cover_name':'../../../secret'}}
    assert clean_data(data)['record'] == {'cover_url':None, 'cover_name':'cover.png'}
    assert data['record']['cover_url'].startswith('https://')
