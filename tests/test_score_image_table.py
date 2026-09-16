from modules.images.records import _score_judgement_table


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
