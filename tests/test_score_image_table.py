import pytest

from modules.images.records import _score_judgement_table
from modules.messages.scores import generate_score_recognition_flex
from modules.score_recognition.presentation import flex_combo_status, flex_score_rank
from modules.score_rules import JUDGEMENT_ROWS, combo_status, score_rank


def _nodes(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from _nodes(child)


def test_rank_boundaries():
    boundaries = [(100.5, 'sss+'), (100, 'sss'), (99.5, 'ss+'), (99, 'ss'),
                  (98, 's+'), (97, 's'), (94, 'aaa'), (90, 'aa'), (80, 'a'),
                  (75, 'bbb'), (70, 'bb'), (60, 'b'), (50, 'c'), (0, 'd')]
    for score, expected in boundaries:
        assert score_rank(score) == expected
        assert flex_score_rank(score) == expected.replace('+', 'p')
        if score:
            assert score_rank(score - 0.0001) != expected


def test_missing_rank_and_combo_rows():
    assert score_rank(None) is None
    rows = {row: dict(great=0, good=0, miss=0) for row in JUDGEMENT_ROWS}
    cases = [(None, 101, 'ap+'), (None, 100, 'ap'), ('great', 99, 'fc+'),
             ('good', 98, 'fc'), ('miss', 97, None)]
    for field, score, expected in cases:
        if field:
            rows['tap'][field] = 1
        assert combo_status(score, rows) == expected
        assert flex_combo_status(rows, score) == (expected.replace('+', 'p') if expected else 'dummy')
    del rows['break']
    assert combo_status(100, rows) is None
    assert flex_combo_status(rows, 100) is None


def test_flex_common_and_break_totals_keep_layout():
    keys = ('perfect_high', 'perfect_low', 'great_high', 'great_middle', 'great_low', 'good', 'miss')
    result = {'parsed': {'title': 'Test', 'achievement': 98,
              'sub_judgement': {row: dict(critical_perfect=100, perfect=2, great=3, good=1, miss=0)
                                for row in JUDGEMENT_ROWS}},
              'validation': {'loss_percentages': {
                  f'{row}_{field}': .01 for row in JUDGEMENT_ROWS for field in ('great', 'good', 'miss')},
                  'break_detail': {**dict.fromkeys(keys, 2),
                                   'loss_percentages': dict.fromkeys(keys, .002)}}}
    totals = [node for node in _nodes(generate_score_recognition_flex(result).to_dict())
              if node.get('backgroundColor') == '#FDEDEC']
    assert [node['contents'][1]['text'] for node in totals] == ['-0.0400%'] * 4 + ['-0.0280%']
    assert all(node['contents'][0]['text'] == 'TOTAL' and node['layout'] == 'horizontal'
               for node in totals)


def test_counts_and_loss_totals_remain_distinct():
    table = _score_judgement_table(dict(judgement={'tap': {'great': 3, 'miss': 0}},
        break_detail={}, loss_percentages={'tap_great': .0123}))
    great = table[0]['cells'][2][0]
    assert great['count'] == 3
    assert great['total'] == '-0.03690%'
    assert great['unit'] == '-0.01230%'
    assert table[0]['cells'][0][0]['count'] == '—'
    assert table[0]['cells'][4][0]['zero'] is True
    assert table[1]['cells'][0][0]['count'] == '—'


def test_break_splits_keep_unknown_losses_and_counts_unknown():
    table = _score_judgement_table(dict(judgement={'break': {'critical_perfect': 20}},
        break_detail={'perfect_high': 2, 'perfect_low': 0,
                      'loss_percentages': {'perfect_high': .001}}, loss_percentages={}))
    cells = table[-1]['cells']
    assert cells[0][0]['count'] == 20
    assert [part['label'] for part in cells[1]] == ['P1', 'P2']
    assert cells[1][0]['total'] == '-0.00200%'
    assert cells[1][1]['total'] is None
    assert cells[2][0]['count'] == '—'
    assert cells[2][0]['unit'] is None


@pytest.mark.parametrize('skin', ['default', 'glass'])
def test_templates_keep_section_and_row_loss_totals(skin):
    from pathlib import Path
    from jinja2 import Environment, FileSystemLoader

    root = Path(__file__).resolve().parents[1] / 'templates/images'
    template = Environment(loader=FileSystemLoader(root)).get_template('skins/glass/score.html' if skin == 'glass' else 'score.html')
    html = template.render(
        validation={}, payload={'title': 'Test', 'difficulty_label': 'MASTER'},
        texts={'common_total': 'COMMON TOTAL', 'break_total': 'BREAK TOTAL'},
        table_rows=[], panels=[
            dict(total_label='COMMON TOTAL', total='-0.12000%', rows=[
                dict(label='TAP', total='-0.03000%'),
                dict(label='HOLD', total=None),
            ]),
            dict(total_label='BREAK TOTAL', total='-0.07000%', rows=[
                dict(label='PERFECT', total='-0.02000%'),
                dict(label='GREAT', total='-0.05000%'),
            ]),
        ],
    )
    for text in ('COMMON TOTAL', 'BREAK TOTAL', '-0.12000%', '-0.07000%',
                 '-0.03000%', '-0.02000%', '-0.05000%'):
        assert text in html
    assert 'None' not in html


@pytest.mark.parametrize('skin', ['default', 'glass'])
@pytest.mark.parametrize('validation_context', [{}, {'validation': None}])
def test_legacy_worker_context_keeps_counts_and_totals(skin, validation_context):
    from modules.images.renderer import template

    html = template('score.html', skin=skin,
        payload={'title': 'Legacy score', 'difficulty_label': 'MASTER'},
        texts={'judgement': 'Judgements', 'break': 'BREAK',
               'common_total': 'COMMON TOTAL', 'break_total': 'BREAK TOTAL'},
        rows=[('TAP', [123, 4, 3, 2, 1]), ('BREAK', [20, 5, 0, 0, 0])],
        panels=[dict(total_label='COMMON TOTAL', total='-0.25000%', rows=[])],
        icons=[('data:image/png;base64,test', 130)], **validation_context)
    assert 'Legacy score' in html
    assert '>123</div>' in html and '>20</div>' in html
    assert '-0.25000%' in html
    assert 'data:image/png;base64,test' in html
    assert 'CHECK REQUIRED' in html
