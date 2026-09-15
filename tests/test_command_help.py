"""Help routing and rendering work from the command-owned module."""
import pytest

from modules.commands.command_help import command_help_message, detect_command_help_key


@pytest.mark.parametrize('query,key', [
    ('HELP', 'help_index'), ('maimai   update', 'maimai_update'),
    ('song info', 'song_info'), ('song record', 'song_record'),
    ('13+ records 2', 'level_records'), ('舞神 plate -uc', 'plate'),
    ('artist', 'search_by_artist'), ('not-a-command', None),
])
def test_help_aliases(query, key):
    assert detect_command_help_key(query) == key


def test_help_messages_and_unknown_key():
    for key in ('help_index', 'b_records', 'bind', 'calc_notes'):
        message = command_help_message(key)
        assert message.alt_text
        assert message.contents.to_dict()['type'] == 'bubble'
    assert command_help_message('not-a-command') is None
