import copy
from unittest.mock import patch

import pytest

from modules.score_recognition import recognizer


@pytest.fixture
def chart():
    notes = dict(tap=100, hold=20, slide=10, touch=5, **{'break': 2})
    song = dict(id='test', title='Test Song', type='dx', sheets=[
        dict(difficulty='master', noteCounts=notes),
    ])
    rows = {name: dict(critical_perfect=value, perfect=0, great=0, good=0, miss=0)
            for name, value in notes.items()}
    return song, rows


@pytest.mark.parametrize('layout', ['dxnet', 'photo'])
@pytest.mark.parametrize('preserve', [False, True])
def test_valid_chart_remains_complete_and_keeps_original_rows(chart, layout, preserve):
    song, rows = chart
    original = copy.deepcopy(rows)
    result = dict(parsed=dict(title='Test Song', achievement=101.0, sub_judgement=rows),
                  crop_metadata=dict(layout=layout))
    with patch.object(recognizer, 'read_dxdata', return_value=([song], None)):
        output = recognizer.validate_recognized_judgement(result, preserve_input=preserve)
    assert output is result
    assert rows == original
    validation = output['validation']
    assert validation['song_id'] == 'test'
    assert validation['achievement_calc']['consistent'] is True
    assert validation['achievement_calc']['complete'] is True
    assert validation['row_offset'] == validation['column_offset'] == 0
    assert not validation['uncertain_cells']
    assert not validation['calc_corrections']


@pytest.mark.parametrize('mode', ['missing_cell', 'overfull'])
def test_single_cell_repairs_are_reported_without_mutating_ocr_rows(chart, mode):
    song, rows = chart
    if mode == 'missing_cell':
        del rows['tap']['perfect']
    else:
        rows['tap']['critical_perfect'] = 1100
    original = copy.deepcopy(rows)
    result = dict(parsed=dict(title='Test Song', achievement=101.0, sub_judgement=rows))
    with patch.object(recognizer, 'read_dxdata', return_value=([song], None)):
        output = recognizer.validate_recognized_judgement(result, allow_ocr_alignment=False)
    assert rows == original
    assert output['parsed']['sub_judgement']['tap']['critical_perfect'] == 100
    field, expected = ('perfect', 0) if mode == 'missing_cell' else ('critical_perfect', 100)
    assert any(item['row'] == 'tap' and item['field'] == field
               and item['validated'] == expected for item in output['validation']['calc_corrections'])


def test_empty_judgement_does_not_load_song_database():
    result = {'parsed': {'sub_judgement': {}}}
    with patch.object(recognizer, 'read_dxdata') as read:
        assert recognizer.validate_recognized_judgement(result) is result
    read.assert_not_called()
