from modules.message_manager import generate_score_recognition_flex
from modules.score_rules import JUDGEMENT_ROWS


def nodes(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from nodes(child)


def test_common_and_break_totals_keep_values_and_layout():
    keys = ('perfect_high', 'perfect_low', 'great_high', 'great_middle', 'great_low', 'good', 'miss')
    result = {
        'parsed': {'title': 'Test', 'achievement': 98,
                   'sub_judgement': {r: dict(critical_perfect=100, perfect=2, great=3, good=1, miss=0)
                                     for r in JUDGEMENT_ROWS}},
        'validation': {'loss_percentages': {f'{r}_{f}': .01 for r in JUDGEMENT_ROWS for f in ('great', 'good', 'miss')},
                       'break_detail': {**dict.fromkeys(keys, 2), 'loss_percentages': dict.fromkeys(keys, .002)}},
    }
    payload = generate_score_recognition_flex(result).to_dict()
    totals = [n for n in nodes(payload) if n.get('backgroundColor') == '#FDEDEC']
    assert [n['contents'][1]['text'] for n in totals] == ['-0.0400%'] * 4 + ['-0.0280%']
    assert all(n['contents'][0]['text'] == 'TOTAL' and n['layout'] == 'horizontal' for n in totals)
    assert generate_score_recognition_flex({}).contents.to_dict()['type'] == 'bubble'
