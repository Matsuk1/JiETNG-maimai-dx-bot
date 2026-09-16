from unittest.mock import patch

import pytest

from modules.monitoring import codex_agent
from modules.score_recognition import recognizer


def sample():
    notes = dict(tap=100, hold=20, slide=10, touch=0, **{'break': 2})
    song = dict(id='test', title='Test', type='std', sheets=[
        dict(difficulty='master', noteCounts=notes)])
    parsed = dict(title='Test', achievement=101., sub_judgement={
        name: dict(critical_perfect=count, perfect=0, great=0, good=0, miss=0)
        for name, count in notes.items()})
    return song, parsed


def test_fallback_revalidates_image_result_and_does_not_mutate_raw_rows():
    song, parsed = sample()
    original = {'parsed': {'title': 'Unreadable', 'sub_judgement': {}}}
    with patch.object(recognizer, 'read_dxdata', return_value=([song], None)), patch.object(
        codex_agent, 'recognize_score_with_codex', return_value=parsed) as ask:
        result = recognizer.validate_recognized_judgement(original, image_bytes=b'image')
    ask.assert_called_once_with(b'image')
    assert result['source'] == 'codex'
    assert result['validation']['achievement_calc']['consistent'] is True
    assert original['parsed']['sub_judgement'] == {}


@pytest.mark.parametrize('mode', ['unavailable', 'timeout', 'bad_achievement', 'negative', 'missing', 'inconsistent'])
def test_fallback_failure_keeps_original(mode):
    song, parsed = sample()
    if mode == 'bad_achievement': parsed['achievement'] = float('nan')
    if mode == 'negative': parsed['sub_judgement']['tap']['great'] = -1
    if mode == 'missing': parsed['sub_judgement']['tap']['perfect'] = None
    if mode == 'inconsistent': parsed['achievement'] = 90
    response = None if mode == 'unavailable' else parsed
    original = {'parsed': {'title': 'Unknown', 'sub_judgement': {}}}
    with patch.object(recognizer, 'read_dxdata', return_value=([song], None)), patch.object(
        codex_agent, 'recognize_score_with_codex', return_value=response,
        side_effect=TimeoutError if mode == 'timeout' else None):
        assert recognizer.validate_recognized_judgement(original, image_bytes=b'image') is original


@pytest.mark.parametrize('mode', ['valid', 'manual', 'no_image', 'completion'])
def test_local_success_or_manual_input_never_calls_codex(mode):
    song, parsed = sample()
    result = {'parsed': parsed if mode == 'valid' else {}}
    if mode == 'completion': result['validation'] = {'calc_completion_candidates': [{}]}
    with patch.object(recognizer, 'read_dxdata', return_value=([song], None)), patch.object(
        codex_agent, 'recognize_score_with_codex') as ask:
        recognizer.validate_recognized_judgement(result,
            image_bytes=None if mode == 'no_image' else b'image', preserve_input=mode == 'manual')
    ask.assert_not_called()


def test_ocr_server_has_no_monitor_tools_or_web():
    server = codex_agent._CodexAppServer(ocr_only=True)
    with patch.object(codex_agent, '_codex_path', return_value='codex'):
        command = server._command()
    assert not any('mcp_servers' in arg for arg in command)
    assert 'web_search="disabled"' in command
    assert 'features.shell_tool=false' in command
    assert 'features.image_generation=false' in command


def test_disabled_connection_does_not_start_codex():
    with patch.object(codex_agent, 'AI_MONITOR_ENABLED', False), patch.object(
        codex_agent._ocr_server, 'ask') as ask:
        assert codex_agent.recognize_score_with_codex(b'image') is None
    ask.assert_not_called()


def image_bytes():
    from io import BytesIO
    from PIL import Image
    with BytesIO() as output:
        Image.new('RGB', (32, 32), 'white').save(output, format='PNG')
        return output.getvalue()


def test_four_point_detection_failure_uses_original_image_and_requested_version():
    song, parsed = sample()
    raw = image_bytes()
    with patch.object(recognizer, '_load_ocr_module', return_value=((), None, None)), patch.object(
        recognizer, '_engine', side_effect=ValueError('Could not confirm four corners')), patch.object(
        recognizer, 'read_dxdata', return_value=([song], None)) as read, patch.object(
        codex_agent, 'recognize_score_with_codex', return_value=parsed) as ask:
        result = recognizer.recognize_score_image_bytes(raw, ver='intl')
    ask.assert_called_once_with(raw)
    read.assert_called_with('intl')
    assert result['source'] == 'codex'


def test_local_ocr_success_does_not_call_codex():
    from unittest.mock import Mock
    raw = image_bytes()
    expected = {'parsed': {'title': 'Test'}}
    process = Mock(return_value=expected)
    with patch.object(recognizer, '_load_ocr_module', return_value=((), None, process)), patch.object(
        recognizer, '_engine', return_value=object()), patch.object(
        codex_agent, 'recognize_score_with_codex') as ask:
        assert recognizer.recognize_score_image_bytes(raw) is expected
    ask.assert_not_called()


def test_detection_failure_without_codex_preserves_original_error():
    with patch.object(recognizer, '_load_ocr_module', side_effect=ValueError('four corners')), patch.object(
        codex_agent, 'recognize_score_with_codex', return_value=None):
        with pytest.raises(ValueError, match='four corners'):
            recognizer.recognize_score_image_bytes(image_bytes())


def test_invalid_upload_is_not_sent_to_codex():
    with patch.object(codex_agent, 'recognize_score_with_codex') as ask:
        with pytest.raises(recognizer.InvalidScoreImageError):
            recognizer.recognize_score_image_bytes(b'not an image')
    ask.assert_not_called()
