import copy
from unittest.mock import patch

import pytest

from modules.commands.command_parsers import parse_fix_record_command
from modules.i18n import localized_catalog, select_text
from modules.messages.scores import generate_score_recognition_flex
from modules.score_rules import JUDGEMENT_ROWS


def result_fixture():
    return {
        'parsed': {'title': 'Alpha Beta', 'achievement': 100.1234,
                   'sub_judgement': {row: dict(critical_perfect=100, perfect=2, great=1, good=0, miss=0)
                                     for row in JUDGEMENT_ROWS}},
        'validation': {'song_id': '1', 'difficulty': 'master', 'type': 'dx',
                       'achievement_calc': {'consistent': True, 'complete': True}},
    }


def nodes(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from nodes(child)


@pytest.mark.parametrize('consistent,complete,inferred,manual,compact', [
    (True, True, False, False, False),
    (True, True, True, False, True),
    (False, False, False, True, False),
    (None, False, False, True, False),
    (True, False, True, True, False),
])
def test_validation_hint_and_copy_command(consistent, complete, inferred, manual, compact):
    result = result_fixture()
    result['validation']['achievement_calc'].update(consistent=consistent, complete=complete)
    if inferred:
        result['validation']['calc_corrections'] = [{'inferred_row': True}]
    original = copy.deepcopy(result)
    with patch('modules.messages.scores.get_user_language', return_value='en'):
        payload = generate_score_recognition_flex(result).to_dict()
    catalog = localized_catalog('message_manager.score_recognition')
    text = lambda key: select_text(catalog[key], language='en')
    displayed = [node.get('text') for node in nodes(payload)]
    assert (text('manual_fix_hint') in displayed) is manual
    assert text('compact_fix' if compact else 'copy_fix') in displayed
    clipboard = next(node['clipboardText'] for node in nodes(payload) if node.get('type') == 'clipboard')
    assert parse_fix_record_command(clipboard) == (
        'Alpha Beta', 100.1234, result['parsed']['sub_judgement'])
    assert result == original


def test_missing_row_and_empty_result():
    result = result_fixture()
    del result['parsed']['sub_judgement']['break']
    result['validation']['uncertain_cells'] = [{'row': 'break', 'row_missing': True}]
    payload = generate_score_recognition_flex(result).to_dict()
    assert sum(node.get('text') == '-?' for node in nodes(payload)) == 5
    assert 'footer' not in generate_score_recognition_flex({}).contents.to_dict()


def test_candidate_carousel_keeps_order_and_labels():
    results = [result_fixture(), result_fixture()]
    for index, result in enumerate(results, 1):
        result['validation'].update(calc_completion_candidate_index=index, calc_completion_candidate_count=2)
    message = generate_score_recognition_flex(results)
    assert message.alt_text == 'Alpha Beta #1/2 / Alpha Beta #2/2'
    assert len(message.contents.to_dict()['contents']) == 2
