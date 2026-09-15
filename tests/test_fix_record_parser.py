import pytest

from modules.commands.command_parsers import parse_fix_record_command
from modules.score_recognition.presentation import build_fix_command
from modules.score_rules import JUDGEMENT_ROWS


def test_generated_fix_command_round_trip():
    judgement = {name: dict(critical_perfect=100, perfect=5, great=2, good=1, miss=0)
                 for name in JUDGEMENT_ROWS}
    for title in ('Alpha Beta', ''):
        command = build_fix_command(judgement, title, 99.1234)
        assert parse_fix_record_command(command) == (title, 99.1234, judgement)


def test_comma_percentage_and_legacy_chart_suffix():
    command = '\n'.join(['fix-rcd Alpha [DX]', '100,5000%', *(['1/2/3/4/5'] * 5)])
    title, score, rows = parse_fix_record_command(command)
    assert (title, score) == ('Alpha', 100.5)
    assert rows['break']['miss'] == 5


@pytest.mark.parametrize('achievement', ['102%', '-1', 'nan', '99.12345%'])
def test_invalid_achievement(achievement):
    command = '\n'.join(['fix-rcd Alpha', achievement, *(['0/0/0/0/0'] * 5)])
    with pytest.raises(ValueError, match='achievement'):
        parse_fix_record_command(command)


def test_invalid_rows_and_non_commands():
    for command in ('', 'fix-rcd-help', 'info Alpha'):
        assert parse_fix_record_command(command) is None
    with pytest.raises(ValueError, match='five judgement rows'):
        parse_fix_record_command('fix-rcd Alpha\n100%')
    command = '\n'.join(['fix-rcd Alpha', '100%', '1/2/3/4', *(['0/0/0/0/0'] * 4)])
    with pytest.raises(ValueError, match='slash-separated integers'):
        parse_fix_record_command(command)
