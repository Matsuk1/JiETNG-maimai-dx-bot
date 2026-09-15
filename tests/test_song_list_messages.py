from unittest.mock import patch

import pytest

from modules.messages import service


def nodes(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from nodes(child)


def songs(count):
    return [dict(id=str(i), title=f'Song {i}', artist='Artist', type='dx') for i in range(count)]


def commands(message):
    return [node['data'] for node in nodes(message.to_dict()) if node.get('type') == 'postback']


@pytest.mark.parametrize('count', [0, 1, 14, 15, 16, 30, 31, 45])
def test_pagination_visits_every_song_once(count):
    found = []
    total_pages = max(1, (count + 14) // 15)
    with patch.object(service, 'image_button_data', side_effect=lambda command: f'once:{command}'):
        for page in range(1, total_pages + 1):
            message = service.generate_song_list_flex(None, 'Songs', songs(count), page, 'artist', 'A B')
            actions = commands(message)
            found.extend(action for action in actions if action.startswith('once:'))
            assert (f'artist A B {page + 1}' in actions) == (page < total_pages)
            assert f'Page {page}/{total_pages} · {count} songs' in [
                node.get('text') for node in nodes(message.to_dict())
            ]
    assert found == [f'once:search-song {i}' for i in range(count)]


@pytest.mark.parametrize('page,first', [(-10, 0), (100, 15)])
def test_page_is_clamped(page, first):
    with patch.object(service, 'image_button_data', side_effect=lambda command: command):
        message = service.generate_song_list_flex(None, 'Songs', songs(16), page, 'artist', 'A')
    assert commands(message)[0] == f'search-song {first}'


def test_search_limit_and_record_owner_are_preserved():
    with patch.object(service, 'get_user_language', return_value='en'), patch.object(
        service, 'image_button_data', side_effect=lambda command: f'once:{command}'
    ):
        message = service.generate_search_results_flex('user', songs(25), 'record', 'friend')
    assert commands(message) == [f'once:search-record {i}&id_use=friend' for i in range(20)]


@pytest.mark.parametrize('prefix,sheets,expected', [
    ('artist', None, 'Artist'),
    ('bpm', None, 'BPM: 180'),
    ('designer', {'0': [{'difficulty': 'remaster', 'noteDesigner': 'A'},
                        {'difficulty': 'custom', 'noteDesigner': 'B'}]}, 'A [ReMAS] / B [custom]'),
])
def test_song_subtitles(prefix, sheets, expected):
    song = {**songs(1)[0], 'bpm': 180}
    with patch.object(service, 'image_button_data', return_value='once:search-song 0'):
        message = service.generate_song_list_flex(None, 'Songs', [song], 1, prefix, 'query', sheets)
    assert expected in [node.get('text') for node in nodes(message.to_dict())]
