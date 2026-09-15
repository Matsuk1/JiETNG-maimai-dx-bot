import copy
from unittest.mock import patch

import pytest

from modules.messages.service import generate_calc_carousel, generate_calc_result_flex


def texts(value):
    if isinstance(value, dict):
        if value.get('type') == 'text':
            yield value['text']
        for child in value.values():
            yield from texts(child)
    elif isinstance(value, list):
        for child in value:
            yield from texts(child)


def test_touch_visibility_precision_and_tolerance_rounding():
    notes = dict(tap=100, hold=20, slide=10, touch=15, **{'break': 5})
    scores = {'tap_great': .03, 'touch_great': .01}
    original = copy.deepcopy((notes, scores))
    with patch('modules.messages.service.get_user_language', return_value='en'):
        message = generate_calc_result_flex(notes, scores)
    displayed = list(texts(message.to_dict()))
    assert 'TOUCH' in displayed and 'Touch Great' in displayed
    assert '-0.0300000%' in displayed
    tolerance = message.contents.to_dict()['body']['contents'][-1]
    assert '16' in tolerance['contents'][0]['contents'][1]['text']
    assert '33' in tolerance['contents'][1]['contents'][1]['text']
    assert (notes, scores) == original


@pytest.mark.parametrize('touch', [None, 0])
def test_absent_touch_rows_are_hidden(touch):
    notes = {'tap': 100, 'hold': 20, 'slide': 10, 'break': 5}
    if touch is not None:
        notes['touch'] = touch
    displayed = list(texts(generate_calc_result_flex(notes, {'touch_great': .01}).to_dict()))
    assert 'TOUCH' not in displayed and 'Touch Great' not in displayed


@pytest.mark.parametrize('scores', [{}, {'tap_great': 0}, {'tap_great': -1}])
def test_no_tolerance_for_nonpositive_or_missing_loss(scores):
    notes = {'tap': 100, 'hold': 20, 'slide': 10, 'break': 5}
    displayed = list(texts(generate_calc_result_flex(notes, scores).to_dict()))
    assert '100.5000%' not in displayed
    assert '100.0000%' not in displayed


def test_carousel_card_order_and_single_language_lookup():
    notes = {'tap': 100, 'hold': 20, 'slide': 10, 'break': 5}
    first = (notes, {'tap_great': .01}, 'master', 13.7)
    second = (notes, {'tap_great': .02}, 'custom', None)
    with patch('modules.messages.service.get_user_language', return_value='en') as language:
        single = generate_calc_carousel([first], 'user')
    language.assert_called_once_with('user')
    assert single.contents.to_dict()['type'] == 'bubble'
    carousel = generate_calc_carousel([first, second]).contents.to_dict()
    headers = [card['header']['contents'][0]['text'] for card in carousel['contents']]
    assert headers == ['MASTER (Lv. 13.7)', 'CUSTOM']
    assert carousel['contents'][1]['header']['backgroundColor'] == '#007AFF'
