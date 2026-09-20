from unittest.mock import patch
from modules.images.songs import _makeup_played_data


def test_missing_results_keep_chart_slots_and_do_not_invent_remaster():
    sheets = [dict(difficulty=d, internalLevelValue=i+1)
              for i, d in enumerate(('basic', 'advanced', 'expert', 'master'))]
    record = dict(difficulty='master', score='100.0000%')
    with patch('modules.images.records.thumbnail_html', return_value='CARD'), \
         patch('modules.images.renderer.render_template') as render:
        _makeup_played_data([record], {'sheets': sheets}, 'ja')
    rows = render.call_args.kwargs['played_rows']
    assert [row['label'] for row in rows] == ['BASIC', 'ADVANCED', 'EXPERT', 'MASTER']
    assert [row['card'] for row in rows] == ['', '', '', 'CARD']


def test_empty_results_keep_all_existing_charts():
    with patch('modules.images.renderer.render_template') as render:
        _makeup_played_data([], {'sheets': [dict(difficulty='remaster', internalLevelValue=14.7)]})
    rows = render.call_args.kwargs['played_rows']
    assert len(rows) == 1
    assert rows[0]['card'] == ''
    assert rows[0]['text_color'] == '#72148d'
