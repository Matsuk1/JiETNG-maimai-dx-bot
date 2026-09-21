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
        result = recognizer._recognize_ai_result(b'image')
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
        assert recognizer._recognize_ai_result(b'image') == {'parsed': {}}


@pytest.mark.parametrize('mode', ['valid', 'manual', 'no_image', 'completion', 'failed'])
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


def test_four_point_detection_failure_never_calls_codex():
    with patch.object(recognizer, '_load_ocr_module', side_effect=ValueError('four corners')), patch.object(
        codex_agent, 'recognize_score_with_codex') as ask:
        with pytest.raises(ValueError, match='four corners'):
            recognizer.recognize_score_image_bytes(image_bytes(), ver='intl')
    ask.assert_not_called()


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


@pytest.mark.parametrize('ocr_only', [True, False])
@pytest.mark.parametrize('model', ['monitor-model', ''])
def test_ocr_uses_monitor_model_and_default_reasoning(ocr_only, model):
    server = codex_agent._CodexAppServer(ocr_only=ocr_only)
    with patch.object(codex_agent, 'AI_MONITOR_MODEL', model), patch.object(
        server, '_request', return_value={'thread': {'id': 'test'}}) as request:
        server._new_thread(100)
    params = request.call_args.args[1]
    if model:
        assert params['model'] == model
    else:
        assert 'model' not in params
    with patch.object(codex_agent, '_codex_path', return_value='codex'):
        command = server._command()
    assert not any('model_reasoning_effort' in argument for argument in command)


@pytest.mark.parametrize('title,achievement,reason', [
    ('Test', 90, 'achievement_mismatch'),
    ('No corresponding song', 101, 'chart_not_matched'),
])
def test_rejected_vision_logs_its_own_values_and_failure_reason(caplog, title, achievement, reason):
    song, parsed = sample()
    parsed.update(title=title, achievement=achievement)
    original = {'parsed': {'title': 'Original OCR title'}}
    with patch.object(recognizer, 'read_dxdata', return_value=([song], None)), patch.object(
        codex_agent, 'recognize_score_with_codex', return_value=parsed):
        assert recognizer._recognize_ai_result(b'image') == {'parsed': {}}
    assert f'reason={reason}' in caplog.text
    assert repr(title) in caplog.text
    assert 'rows=' in caplog.text


def test_main_screen_totals_reject_skipped_or_shifted_rows(caplog):
    song, parsed = sample()
    parsed['judgement_totals'] = {'critical_perfect': 999}
    original = {'parsed': {}}
    with patch.object(codex_agent, 'recognize_score_with_codex', return_value=parsed):
        assert recognizer._recognize_ai_result(b'image') == {'parsed': {}}
    assert 'column_total_mismatch' in caplog.text


def test_vision_receives_only_unmodified_original(tmp_path):
    (tmp_path / 'auth.json').write_text('{}')
    raw = image_bytes()
    with patch.dict('os.environ', CODEX_HOME=str(tmp_path)), patch.object(
        codex_agent, 'AI_MONITOR_ENABLED', True), patch.object(
        codex_agent, '_codex_path', return_value='codex'), patch.object(
        codex_agent._ocr_server, 'ask', return_value={'text': '{}'}) as ask, patch.object(
        codex_agent._ocr_server, 'release'):
        codex_agent.recognize_score_with_codex(raw)
    inputs = ask.call_args.args[4]
    assert inputs == [(".png", raw)]
    assert 'upper-half detail' not in ask.call_args.args[1]


def test_correct_title_with_overfull_break_reports_row_mismatch(caplog):
    song, parsed = sample()
    parsed['sub_judgement']['break']['great'] = 1
    original = {'parsed': {}}
    with patch.object(recognizer, 'read_dxdata', return_value=([song], None)), patch.object(
        codex_agent, 'recognize_score_with_codex', return_value=parsed):
        assert recognizer._recognize_ai_result(b'image') == {'parsed': {}}
    assert 'reason=chart_judgement_mismatch' in caplog.text
    assert "'break': 1" in caplog.text
    assert 'reason=chart_not_matched' not in caplog.text


def test_explicit_ai_recognition_uses_requested_version(monkeypatch):
    monkeypatch.delenv('JIETNG_AI_REC_ALLOWED_USERS', raising=False)
    song, parsed = sample()
    raw = image_bytes()
    with patch.object(recognizer, 'read_dxdata', return_value=([song], None)) as read, patch.object(
        codex_agent, 'recognize_score_with_codex', return_value=parsed) as ask:
        result = recognizer.recognize_score_with_ai(raw, ver='intl')
    ask.assert_called_once_with(raw)
    read.assert_called_with('intl')
    assert result['source'] == 'codex'
