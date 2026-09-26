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


def white_snow_result():
    fields = ('critical_perfect', 'perfect', 'great', 'good', 'miss')
    values = dict(tap=[304, 213, 15, 0, 0], hold=[35, 20, 0, 0, 0],
                  slide=[114, 0, 0, 0, 0], touch=[0, 0, 0, 0, 0],
                  **{'break': [149, 4, 0, 0, 0]})
    return {'parsed': {'title': '白ゆき', 'achievement': 100.6651,
                       'sub_judgement': {key: dict(zip(fields, counts)) for key, counts in values.items()}}}


@pytest.mark.parametrize('touch', [None, 0])
def test_std_zero_touch_does_not_block_overfull_break_recovery(touch):
    song = dict(id='white-snow', title='白ゆき', type='std', sheets=[dict(
        difficulty='master', noteCounts=dict(tap=532, hold=55, slide=114, touch=touch, **{'break': 18}))])
    result = white_snow_result()
    with patch.object(recognizer, 'read_dxdata', return_value=([song], None)):
        output = recognizer.validate_recognized_judgement(result)
    assert output['parsed']['sub_judgement']['break'] == dict(
        critical_perfect=14, perfect=4, great=0, good=0, miss=0)
    validation = output['validation']
    assert validation['difficulty'] == 'master'
    assert validation['achievement_calc']['consistent'] is True
    assert validation['achievement_calc']['complete'] is True
    assert validation['calc_corrections'][0]['inferred_row'] is True


@pytest.mark.parametrize('preserve,touch', [(True, None), (False, 10)])
def test_break_recovery_respects_manual_input_and_missing_required_touch(preserve, touch):
    song = dict(id='white-snow', title='白ゆき', type='std', sheets=[dict(
        difficulty='master', noteCounts=dict(tap=532, hold=55, slide=114, touch=touch, **{'break': 18}))])
    with patch.object(recognizer, 'read_dxdata', return_value=([song], None)):
        output = recognizer.validate_recognized_judgement(white_snow_result(), preserve_input=preserve)
    assert not any(item.get('inferred_row') for item in output.get('validation', {}).get('calc_corrections', []))


def test_missing_dxdata_note_counts_are_derived_from_complete_ocr_rows():
    fields = ('critical_perfect', 'perfect', 'great', 'good', 'miss')
    values = {
        'tap': [373, 155, 13, 3, 3],
        'hold': [38, 16, 1, 0, 0],
        'slide': [91, 0, 1, 0, 0],
        'touch': [20, 0, 0, 0, 0],
        'break': [63, 5, 0, 0, 0],
    }
    rows = {name: dict(zip(fields, counts)) for name, counts in values.items()}
    original = copy.deepcopy(rows)
    song = dict(id='happycore', title='The Happycore Idol', type='dx', sheets=[dict(
        difficulty='master', noteCounts={name: None for name in values},
    )])
    result = dict(parsed=dict(
        title='The Happycore Idol', achievement=100.3551, sub_judgement=rows,
    ))

    with patch.object(recognizer, 'read_dxdata', return_value=([song], None)):
        output = recognizer.validate_recognized_judgement(result)

    assert rows == original
    validation = output['validation']
    assert validation['achievement_calc']['consistent'] is True
    assert validation['achievement_calc']['complete'] is True
    assert validation['matching_rows'] == 5
    assert validation['inferred_note_count_rows'] == list(values)
    assert not validation['uncertain_cells']
    assert not validation['calc_corrections']


def test_explicit_zero_note_count_is_not_replaced_by_ocr_total(chart):
    song, rows = chart
    song['sheets'][0]['noteCounts']['touch'] = 0
    rows['touch']['critical_perfect'] = 5
    result = dict(parsed=dict(
        title='Test Song', achievement=101.0, sub_judgement=rows,
    ))

    with patch.object(recognizer, 'read_dxdata', return_value=([song], None)):
        output = recognizer.validate_recognized_judgement(
            result, allow_ocr_alignment=False, preserve_input=True,
        )

    assert 'validation' not in output
