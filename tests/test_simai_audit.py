import json

import pytest

from modules.simai_audit import audit_note_counts, count_notes


@pytest.mark.parametrize(('chart', 'expected'), [
    ('(120){4}12,3b,4x,5h[4:1],Chf[4:1],B1f,E', (3, 2, 0, 1, 1, 7)),
    ('1b-4[4:1]b*-6[4:1],2?-5[4:1],3!-6[4:1],E', (0, 0, 3, 0, 2, 5)),
    ('1-3-5[4:1],2-4[4:1]-6[4:1],3V57[4:1],E', (3, 0, 3, 0, 0, 6)),
    ('1$b,2@-5[4:1],3hbx[4:1],C,B1h[4:1],E', (1, 1, 1, 1, 2, 6)),
    ('1`2,0,>> comment\n3, E', (3, 0, 0, 0, 0, 3)),
])
def test_judged_note_counts(chart, expected):
    assert tuple(count_notes(chart).values()) == expected


@pytest.mark.parametrize('chart', ['1,', '9,E', '1-4,E', '1k,E', 'B9,E', '1[4:1],E', '1-4[bad],E'])
def test_unknown_syntax_fails_closed(chart):
    with pytest.raises(ValueError):
        count_notes(chart)


def write_chart(root, name='music000008', chart='1,E', title='Song'):
    directory = root / name
    directory.mkdir(exist_ok=True)
    (directory / 'maidata.txt').write_text(f'&title={title}\n&inote_5={chart}\n', encoding='utf-8')


def song():
    return {'id': 'a', 'title': 'Song', 'type': 'std', 'sheets': [
        {'difficulty': 'master', 'noteCounts': {'tap': 1, 'hold': 0, 'slide': 0, 'touch': None, 'break': 0, 'total': 1}}]}


def test_matching_null_std_touch_and_difference(tmp_path):
    write_chart(tmp_path)
    data = song()
    assert audit_note_counts([data], tmp_path)['summary']['equal'] == 1
    data['sheets'][0]['noteCounts']['tap'] = 2
    report = audit_note_counts([data], tmp_path)
    assert report['issues'][0]['differences'] == {'tap': {'dxdata': 2, 'simai': 1}}
    assert data['sheets'][0]['noteCounts']['touch'] is None


def test_duplicate_sources_and_targets_not_guessed(tmp_path):
    write_chart(tmp_path)
    assert audit_note_counts([song(), song()], tmp_path)['summary']['unmatched'] == 1
    write_chart(tmp_path, 'music000009')
    report = audit_note_counts([song()], tmp_path)
    assert report['summary']['unmatched'] == 2
    assert report['summary']['matched'] == 0


def test_types_missing_source_and_parse_error(tmp_path):
    assert audit_note_counts([], tmp_path)['status'] == 'unavailable'
    write_chart(tmp_path, chart='unknown,E')
    write_chart(tmp_path, 'music010008')
    write_chart(tmp_path, 'music110008_L')
    report = audit_note_counts([song()], tmp_path)
    assert report['summary']['parse_errors'] == 1
    assert report['summary']['unmatched'] == 1
    assert report['summary']['equal'] == 0


def test_note_job_persistence_staleness_and_lock(monkeypatch, tmp_path):
    from modules import dxdata_manager as manager
    monkeypatch.setattr(manager, '_AUDIT_REPORT_PATH', tmp_path / 'audit.json')
    monkeypatch.setattr(manager, '_AUDIT_LOCK_PATH', tmp_path / 'audit.lock')
    monkeypatch.setenv('SIMAI_CHART_DIR', str(tmp_path / 'charts'))
    monkeypatch.setattr(manager.config, 'read_dxdata', lambda *a, **kw: ([song()], []))
    root = tmp_path / 'charts'
    root.mkdir()
    write_chart(root)
    # Dispatch synchronously while preserving the production lock ownership.
    class ImmediateThread:
        def __init__(self, target, args, **kwargs):
            self.target, self.args = target, args
        def start(self):
            self.target(*self.args)
    monkeypatch.setattr(manager.threading, 'Thread', ImmediateThread)
    with manager._audit_lock():
        with pytest.raises(ValueError, match='already running'):
            manager.start_note_count_check()
    manager.start_note_count_check()
    report = manager.get_music_level_report()
    assert report['notes']['summary']['equal'] == 1
    assert report['notes']['stale'] is False
    write_chart(root, chart='12,E')
    assert manager.get_music_level_report()['notes']['stale'] is True
    assert json.loads((tmp_path / 'audit.json').read_text())['notes']['summary']['equal'] == 1


def test_full_check_keeps_notes_when_login_fails(monkeypatch, tmp_path):
    from modules import dxdata_manager as manager
    monkeypatch.setattr(manager, '_AUDIT_REPORT_PATH', tmp_path / 'audit.json')
    monkeypatch.setattr(manager, '_AUDIT_LOCK_PATH', tmp_path / 'audit.lock')
    monkeypatch.setattr(manager, '_check_notes', lambda: {'status': 'complete', 'summary': {'equal': 1}})
    async def login(*args, **kwargs):
        return None
    monkeypatch.setattr(manager, 'login_to_maimai', login)
    guard = manager._audit_lock()
    guard.__enter__()
    report = {'regions': {}, 'fingerprint': 'original'}
    manager._run_check(report, 'id', 'password', 0, guard)
    assert report['notes']['summary']['equal'] == 1
    assert report['status'] == 'complete'
    assert all(r['status'] == 'failed' for r in report['regions'].values())


@pytest.fixture
def note_correction_files(monkeypatch, tmp_path):
    from modules import dxdata_manager as manager
    for key, name in [('DXDATA_FILE', 'dxdata.json'), ('AUTO_OVERRIDE_FILE', 'auto_override.csv'),
                      ('OVERRIDE_FILE', 'override.csv'), ('JP_OVERRIDE_FILE', 'jp.csv'),
                      ('INTL_OVERRIDE_FILE', 'intl.csv')]:
        monkeypatch.setattr(manager.config, key, str(tmp_path / name))
    monkeypatch.setattr(manager, '_AUDIT_REPORT_PATH', tmp_path / 'audit.json')
    monkeypatch.setattr(manager, '_AUDIT_LOCK_PATH', tmp_path / 'audit.lock')
    monkeypatch.setenv('SIMAI_CHART_DIR', str(tmp_path))
    data = song()
    data['sheets'][0]['internalLevelValue'] = 12.0
    (tmp_path / 'dxdata.json').write_text(json.dumps({'songs': [data], 'versions': []}))
    write_chart(tmp_path, chart='12,E')
    manager.config._dxdata_cache.clear()
    yield manager, tmp_path
    manager.config._dxdata_cache.clear()


def persist_note_report(manager):
    notes = manager._check_notes()
    notes['fingerprint'] = manager._note_fingerprint()
    manager._persist_audit({'status': 'complete', 'revision': 'r', 'regions': {},
                           'analysis_version': manager._AUDIT_ANALYSIS_VERSION, 'notes': notes})


def test_save_note_correction_preserves_rows_applies_both_regions(note_correction_files):
    import csv
    m, path = note_correction_files
    auto = path / 'auto_override.csv'
    auto.write_text('Other,dx,sheets,0,noteCounts,tap,42\n')
    raw = (path / 'dxdata.json').read_bytes()
    persist_note_report(m)
    # Warm both caches before saving.
    for region in ('jp', 'intl'):
        assert m.config.read_dxdata(region)[0][0]['sheets'][0]['noteCounts']['tap'] == 1
    report = m.save_note_count_correction('r', 0, 'a', 'master')
    rows = list(csv.reader(auto.open()))
    assert ['Other', 'dx', 'sheets', '0', 'noteCounts', 'tap', '42'] in rows
    assert ['Song', 'std', 'sheets', '0', 'noteCounts', 'tap', '2'] in rows
    assert ['Song', 'std', 'sheets', '0', 'noteCounts', 'total', '2'] in rows
    assert len(rows) == 3
    assert report['notes']['summary']['mismatches'] == 0
    assert report['notes']['summary']['equal'] == 1
    assert (path / 'dxdata.json').read_bytes() == raw
    for region in ('jp', 'intl'):
        assert m.config.read_dxdata(region)[0][0]['sheets'][0]['noteCounts']['tap'] == 2
    assert m.config.read_dxdata(include_generated=False)[0][0]['sheets'][0]['noteCounts']['tap'] == 1
    with pytest.raises(ValueError, match='Report changed'):
        m.save_note_count_correction('r', 0, 'a', 'master')


def test_auto_override_cache_invalidation_and_manual_priority(note_correction_files):
    m, path = note_correction_files
    assert m.config.read_dxdata()[0][0]['sheets'][0]['noteCounts']['tap'] == 1
    (path / 'auto_override.csv').write_text('Song,std,sheets,0,noteCounts,tap,22\n')
    assert m.config.read_dxdata()[0][0]['sheets'][0]['noteCounts']['tap'] == 22
    (path / 'override.csv').write_text('Song,std,sheets,0,noteCounts,tap,33\n')
    assert m.config.read_dxdata()[0][0]['sheets'][0]['noteCounts']['tap'] == 33
    assert m.config.read_dxdata(include_manual=False)[0][0]['sheets'][0]['noteCounts']['tap'] == 22


def test_note_save_rejects_stale_and_wrong_selection(note_correction_files):
    m, path = note_correction_files
    persist_note_report(m)
    with pytest.raises(ValueError, match='unambiguous'):
        m.save_note_count_correction('r', 0, 'wrong', 'master')
    assert not (path / 'auto_override.csv').exists()
    (path / 'auto_override.csv').write_text('Other,dx,sheets,0,noteCounts,tap,42\n')
    with pytest.raises(ValueError, match='changed'):
        m.save_note_count_correction('r', 0, 'a', 'master')
    assert (path / 'auto_override.csv').read_text() == 'Other,dx,sheets,0,noteCounts,tap,42\n'


def test_one_save_does_not_save_other_songs_or_difficulties(note_correction_files):
    import copy
    import csv
    m, path = note_correction_files
    data = json.loads((path / 'dxdata.json').read_text())
    first = data['songs'][0]
    expert = copy.deepcopy(first['sheets'][0])
    expert['difficulty'] = 'expert'
    first['sheets'].append(expert)
    second = copy.deepcopy(first)
    second.update(id='b', title='Other')
    data['songs'].append(second)
    (path / 'dxdata.json').write_text(json.dumps(data))
    (path / 'music000008' / 'maidata.txt').write_text('&title=Song\n&inote_5=12,E\n&inote_4=123,E\n')
    write_chart(path, 'music000009', chart='1234,E', title='Other')
    persist_note_report(m)
    assert m._load_audit_report()['notes']['summary']['mismatches'] == 3
    result = m.save_note_count_correction('r', 0, 'a', 'master')
    rows = list(csv.reader((path / 'auto_override.csv').open()))
    assert len(rows) == 2
    assert all(row[:5] == ['Song', 'std', 'sheets', '0', 'noteCounts'] for row in rows)
    assert result['notes']['summary']['mismatches'] == 2
    remaining = {(i['chart']['song_id'], i['chart']['difficulty'])
                 for i in result['notes']['issues'] if i['kind'] == 'note_mismatch'}
    assert remaining == {('a', 'expert'), ('b', 'master')}
    songs, _ = m.config.read_dxdata()
    assert songs[0]['sheets'][0]['noteCounts']['tap'] == 2
    assert songs[0]['sheets'][1]['noteCounts']['tap'] == 1
    assert songs[1]['sheets'][0]['noteCounts']['tap'] == 1


def test_saving_does_not_rerun_note_check(note_correction_files, monkeypatch):
    m, path = note_correction_files
    persist_note_report(m)
    checked_at = m._load_audit_report()['notes']['checked_at']
    def unexpected_check():
        pytest.fail('Saving must not run a full note check')
    monkeypatch.setattr(m, '_check_notes', unexpected_check)
    result = m.save_note_count_correction('r', 0, 'a', 'master')
    assert result['notes']['issues'] == []
    assert result['notes']['summary']['equal'] == 1
    assert result['notes']['summary']['mismatches'] == 0
    assert result['notes']['checked_at'] == checked_at
    assert result['notes']['saved_at']
    assert result['notes']['stale'] is False


@pytest.mark.parametrize('title', ['L4TS:2018 (feat. あひる & KTA)', 'A&B', 'A &title=B', 'A = B & C'])
def test_metadata_keeps_ampersands_and_multiline_charts(tmp_path, title):
    data = song()
    data['title'] = title
    directory = tmp_path / 'music000008'
    directory.mkdir()
    (directory / 'maidata.txt').write_text(
        f'&artist=Artist A & Artist B\n&title={title}\n&first=0\n'
        '&inote_5=(120){4}\n1,\nE\n&des_5=Designer A & B\n', encoding='utf-8')
    result = audit_note_counts([data], tmp_path)
    assert result['summary']['equal'] == 1
    assert result['summary']['parse_errors'] == 0
    assert result['issues'] == []


def test_other_same_name_songs_are_not_disambiguated_by_counts(tmp_path):
    import copy
    a = song()
    b = copy.deepcopy(a)
    b['id'] = 'b'
    b['sheets'][0]['noteCounts'].update(tap=2, total=2)
    write_chart(tmp_path, chart='1,E')
    write_chart(tmp_path, 'music000009', chart='12,E')
    result = audit_note_counts([b, a], tmp_path)
    assert result['summary']['unmatched'] == 2
    assert result['summary']['matched'] == 0



def test_link_partial_categories_match_but_keep_differences(tmp_path):
    import copy
    a = song()
    a['title'] = 'Link'
    a['sheets'][0]['noteCounts'].update(tap=2, hold=1, slide=0, touch=None, **{'break': 1, 'total': 4})
    b = copy.deepcopy(a)
    b['id'] = 'b'
    b['sheets'][0]['noteCounts'].update(tap=10, hold=4, slide=3, **{'break': 8, 'total': 25})
    write_chart(tmp_path, chart='1/2/3,4h[4:1],5b,E', title='Link')
    result = audit_note_counts([b, a], tmp_path)
    assert result['summary']['matched'] == 1
    issue = result['issues'][0]
    assert issue['chart']['song_id'] == 'a'
    assert issue['chart']['match_method'] == 'link_partial_counts'
    assert set(issue['differences']) == {'tap', 'total'}


def test_link_tied_partial_counts_remain_unmatched(tmp_path):
    import copy
    a = song()
    a['title'] = 'Link'
    b = copy.deepcopy(a)
    b['id'] = 'b'
    write_chart(tmp_path, title='Link', chart='12,E')
    result = audit_note_counts([a, b], tmp_path)
    assert result['summary']['unmatched'] == 1


def test_link_sources_cannot_claim_same_chart(tmp_path):
    data = song()
    data['title'] = 'Link'
    write_chart(tmp_path, title='Link')
    write_chart(tmp_path, 'music000009', title='Link')
    result = audit_note_counts([data], tmp_path)
    assert result['summary']['matched'] == 0
    assert result['summary']['unmatched'] == 2


def test_utage_ignored_in_sources_and_dxdata_coverage(tmp_path):
    import copy
    write_chart(tmp_path)
    for name in ('music110001', 'music110002_L', 'music110002_R'):
        write_chart(tmp_path, name)
        (tmp_path / name / 'maidata.txt').write_bytes(b'\xff')
    with (tmp_path / 'music000008' / 'maidata.txt').open('a') as stream:
        stream.write('&inote_7=invalid,E\n')
    banquet = copy.deepcopy(song())
    banquet.update(id='banquet', type='utage')
    banquet['sheets'][0]['difficulty'] = 'utage'
    mixed = copy.deepcopy(song())
    mixed.update(id='mixed', title='Mixed')
    mixed['sheets'][0]['type'] = 'utage'
    result = audit_note_counts([song(), banquet, mixed], tmp_path)
    assert result['summary']['charts'] == 1
    assert result['summary']['files'] == 1
    assert result['summary']['equal'] == 1
    assert result['summary']['dxdata_uncovered'] == 0
    assert result['issues'] == []
