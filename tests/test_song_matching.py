"""OCR title matching retains its precedence and stable song identities."""
import pytest

from modules.song_matcher import match_recognized_song_title, song_identity_key


@pytest.mark.parametrize('query,title,kind', [
    ('Alpha Beta', 'Alpha Beta', 'exact'),
    ('极圈', '極圏', 'ocr_confusable'),
    ('ばびぶべぼ', 'ぱぴぷぺぽ', 'ocr_kana'),
    ('Beta Alpha', 'Alpha Beta', 'rolling_exact'),
])
def test_ocr_match_types(query, title, kind):
    song = {'id': '1', 'type': 'dx', 'title': title}
    assert match_recognized_song_title(query, [song]) == ([song], kind)


def test_exact_match_limit_and_chart_identity():
    std = {'id': '1', 'type': 'std', 'title': 'Alpha Beta'}
    dx = dict(std, type='dx')
    assert match_recognized_song_title('Alpha Beta', [std, dx], 1) == ([std], 'exact')
    assert song_identity_key(std) != song_identity_key(dx)
    assert match_recognized_song_title('', [std, dx]) == ([], 'none')
