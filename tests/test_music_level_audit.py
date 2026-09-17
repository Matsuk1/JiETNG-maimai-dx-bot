import asyncio
from unittest.mock import AsyncMock

from lxml import etree
import pytest

from modules import maimai_manager as maimai
from modules.dxdata_manager import audit_music_levels


SELECT = '<select name="level"><option value="17">13</option><option value="18">13+</option></select>'


def block(title, difficulty='master', kind='dx', level='13'):
    return (f'<div class="music_{difficulty}_score_back w_450">'
            f'<div class="music_name_block">{title}</div>'
            f'<div class="music_lv_block">{level}</div>'
            f'<img class="music_kind_icon" src="/img/music_{kind}.png"></div>')


def test_parser_preserves_order_unplayed_and_difficulty():
    dom = etree.HTML(SELECT + block('B', 'remaster') + block('A', kind='standard'))
    assert maimai.parse_music_level_options(dom) == {'13': '17', '13+': '18'}
    rows = maimai.parse_music_level_records(dom, '13')
    assert [(r['title'], r['type'], r['difficulty']) for r in rows] == [
        ('B', 'dx', 'remaster'), ('A', 'std', 'master')]


@pytest.mark.parametrize('html', ['<input name="segaId">', SELECT,
                                 SELECT + '<div class="music_name_block">A</div>'])
def test_invalid_or_empty_pages_fail(html):
    with pytest.raises(RuntimeError):
        maimai.parse_music_level_records(etree.HTML(html), '13')


def test_fetch_uses_discovered_values_and_rejects_partial_results(monkeypatch):
    class Session:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            self.closed = True

    session = Session()
    monkeypatch.setattr(maimai, '_create_session', lambda *a, **kw: session)
    fetch = AsyncMock(side_effect=[etree.HTML(SELECT), etree.HTML(SELECT + block('A')), None])
    monkeypatch.setattr(maimai, 'fetch_dom', fetch)
    with pytest.raises(RuntimeError):
        asyncio.run(maimai.get_music_level_lists({'test': 'cookie'}))
    assert session.closed
    assert fetch.call_args_list[1].args[1].endswith('/search/?level=17')
    assert fetch.call_args_list[2].args[1].endswith('/search/?level=18')


def audit(values, *, order='ascending'):
    songs = [{'title': title, 'type': 'dx', 'sheets': [
        {'difficulty': 'master', 'level': '13', 'internalLevelValue': value}]} for title, value in values]
    rows = [{'title': title, 'type': 'dx', 'difficulty': 'master'} for title, _ in values]
    return audit_music_levels([{'level': '13', 'charts': rows}], {'songs': songs}, order=order)


def test_equal_values_and_both_directions():
    assert not audit([('A', 13), ('B', 13), ('C', 13.5)])['issues']
    assert not audit([('A', 13.5), ('B', 13)], order='descending')['issues']
    report = audit([('A', 13.5), ('B', 13.1)])
    assert report['issues'][0]['kind'] == 'order_conflict'
    assert report['issues'][0]['before']['title'] == 'A'


def test_only_order_conflicts_are_reported():
    report = audit([('A', 13.7), ('B', None), ('C', 13.1)])
    assert {i['kind'] for i in report['issues']} == {'order_conflict'}


def test_match_chart_identity_upstream_schema_version_and_ambiguity():
    sheet = {'type': 'std', 'difficulty': 'expert', 'level': '13+',
             'internalLevelValue': 13.5, 'multiverInternalLevelValue': {'current': 13.6}}
    songs = [{'title': 'Ａ', 'sheets': [sheet]}]
    groups = [{'level': '13+', 'charts': [{'title': 'A', 'type': 'std', 'difficulty': 'expert'},
                                        {'title': 'A', 'type': 'dx', 'difficulty': 'expert'}]}]
    report = audit_music_levels(groups, {'songs': songs}, version='current')
    assert not report['issues']
    assert report['levels'][0]['charts'][0]['internalLevelValue'] == 13.6
    report = audit_music_levels(groups, {'songs': songs * 2})
    assert not report['issues']


def test_real_page_fixture():
    from pathlib import Path
    dom = etree.HTML((Path(__file__).parent / 'fixtures/music_level_13.html').read_text())
    options = maimai.parse_music_level_options(dom)
    assert len(options) == 23
    assert options['13'] == '19' and options['13+'] == '20'
    rows = maimai.parse_music_level_records(dom, '13')
    assert [r['title'] for r in rows] == ['Overdose', 'Colorful Starting Line', '勝手に生きましょ']


def test_blank_song_and_distinct_same_name_charts_are_preserved():
    rows = maimai.parse_music_level_records(etree.HTML(SELECT + block('\u3000') + block('Link') * 2), '13')
    assert rows[0]['title'] == '\u3000'
    assert len(rows) == 3
    data = {'songs': [{'title': 'Link', 'type': 'dx', 'sheets': [
        {'difficulty': 'master', 'level': '13', 'internalLevelValue': 13}]}]}
    report = audit_music_levels([{'level': '13', 'charts': rows}], data)
    assert not report['issues']


def test_low_levels_have_no_plus_bucket():
    data = {'songs': [{'title': 'A', 'type': 'dx', 'sheets': [
        {'difficulty': 'basic', 'level': '6', 'internalLevelValue': 6.9}]}]}
    report = audit_music_levels([{'level': '6', 'charts': [
        {'title': 'A', 'type': 'dx', 'difficulty': 'basic'}]}], data)
    assert not report['issues']



@pytest.mark.parametrize('region,host', [('jp', 'maimaidx.jp'), ('intl', 'maimaidx-eng.com')])
def test_fetch_uses_regional_host(monkeypatch, region, host):
    class Session:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
    monkeypatch.setattr(maimai, '_create_session', lambda *a, **kw: Session())
    fetch = AsyncMock(side_effect=[etree.HTML(SELECT), etree.HTML(SELECT + block('A'))])
    monkeypatch.setattr(maimai, 'fetch_dom', fetch)
    result = asyncio.run(maimai.get_music_level_lists({}, ['13'], ver=region))
    assert result[0]['url'].startswith(f'https://{host}/')
    assert all(call.args[2] == region for call in fetch.call_args_list)



@pytest.fixture
def audit_files(monkeypatch, tmp_path):
    import json
    from modules import dxdata_manager as manager
    config = manager.config
    for key, filename in [('DXDATA_FILE', 'dxdata.json'), ('OVERRIDE_FILE', 'override.csv'),
                          ('JP_OVERRIDE_FILE', 'jp_override.csv'),
                          ('INTL_OVERRIDE_FILE', 'intl_override.csv')]:
        monkeypatch.setattr(config, key, str(tmp_path / filename))
    monkeypatch.setattr(manager, '_AUDIT_REPORT_PATH', tmp_path / 'audit.json')
    monkeypatch.setattr(manager, '_AUDIT_LOCK_PATH', tmp_path / 'audit.lock')
    data = {'songs': [{'title': name, 'id': name, 'type': 'dx', 'sheets': [
        {'difficulty': 'master', 'level': '13', 'internalLevelValue': constant,
         'regions': {'jp': True, 'intl': True}}]} for name, constant in [('A', 13.5), ('B', 13.1)]], 'versions': []}
    (tmp_path / 'dxdata.json').write_text(json.dumps(data))
    (tmp_path / 'override.csv').write_text('unrelated,dx,version,old\n')
    config._dxdata_cache.clear()
    groups = [{'level': '13', 'charts': [{'title': name, 'type': 'dx', 'difficulty': 'master'} for name in ('A', 'B')]}]
    report = {'status': 'complete', 'analysis_version': manager._AUDIT_ANALYSIS_VERSION, 'revision': 'revision', 'fingerprint': manager._audit_fingerprint(), 'regions': {}}
    for region in ('jp', 'intl'):
        result = manager._recheck_music_levels(region, groups)
        result.update(status='complete', fetched_at='original')
        report['regions'][region] = result
    manager._persist_audit(report)
    yield manager, tmp_path
    config._dxdata_cache.clear()


def test_intl_save_isolated_and_rechecks(audit_files):
    import csv
    manager, path = audit_files
    manual_before = [(path / f).read_bytes() for f in ('override.csv',)]
    report = manager.save_music_level_correction('revision', 'intl', 0, 'A', 'master', 'internalLevelValue', 13)
    assert [(path / f).read_bytes() for f in ('override.csv',)] == manual_before
    with (path / 'intl_override.csv').open() as stream:
        rows = list(csv.reader(stream))
    assert rows == [['A', 'dx', 'sheets', '0', 'internalLevelValue', '13.0']]
    assert manager.config.read_dxdata('intl')[0][0]['sheets'][0]['internalLevelValue'] == 13.0
    assert manager.config.read_dxdata('jp')[0][0]['sheets'][0]['internalLevelValue'] == 13.5
    assert report['regions']['intl']['summary']['order_conflicts'] == 0
    assert report['regions']['jp']['summary']['order_conflicts'] == 1
    assert 'levels' not in report['regions']['intl']
    assert manager._load_audit_report()['regions']['intl']['levels']
    with pytest.raises(ValueError, match='Report changed'):
        manager.save_music_level_correction('revision', 'intl', 0, 'A', 'master', 'internalLevelValue', 13)


def test_jp_save_uses_independent_generated_override(audit_files):
    manager, path = audit_files
    manual_before = [(path / f).read_bytes() for f in ('override.csv',)]
    report = manager.save_music_level_correction('revision', 'jp', 0, 'A', 'master', 'internalLevelValue', 13)
    assert [(path / f).read_bytes() for f in ('override.csv',)] == manual_before
    assert (path / 'jp_override.csv').exists()
    assert not (path / 'intl_override.csv').exists()
    assert report['regions']['intl']['summary']['order_conflicts'] == 1
    assert report['regions']['jp']['summary']['order_conflicts'] == 0


@pytest.mark.parametrize('field,value', [('internalLevelValue', 'nan'), ('internalLevelValue', 13.25),
                                       ('internalLevelValue', True), ('level', '99'), ('title', 'bad')])
def test_invalid_corrections_never_write(audit_files, field, value):
    manager, path = audit_files
    before = (path / 'override.csv').read_bytes()
    with pytest.raises(ValueError):
        manager.save_music_level_correction('revision', 'intl', 0, 'A', 'master', field, value)
    assert (path / 'override.csv').read_bytes() == before
    assert not (path / 'intl_override.csv').exists()


def test_stale_data_and_unrelated_chart_rejected(audit_files):
    manager, path = audit_files
    with pytest.raises(ValueError, match='Select'):
        manager.save_music_level_correction('revision', 'intl', 0, 'C', 'master', 'internalLevelValue', '13')
    with (path / 'dxdata.json').open('a') as stream:
        stream.write(' ')
    assert manager.get_music_level_report()['stale']
    with pytest.raises(ValueError, match='changed'):
        manager.save_music_level_correction('revision', 'intl', 0, 'A', 'master', 'internalLevelValue', '13')


def test_region_failure_keeps_success_and_never_persists_credentials(audit_files, monkeypatch):
    import json
    manager, path = audit_files
    monkeypatch.setattr(manager, 'login_to_maimai', AsyncMock(return_value={'cookie': 'secret-cookie'}))
    groups = manager._load_audit_report()['regions']['jp']['levels']
    monkeypatch.setattr(manager, 'get_music_level_lists', AsyncMock(side_effect=[groups, RuntimeError('Official site rate limit')]))
    monkeypatch.setattr(manager, 'get_music_version_lists', AsyncMock(return_value=[]))
    guard = manager._audit_lock(); guard.__enter__()
    report = {'status': 'running', 'regions': {}}
    manager._run_check(report, 'private-user', 'private-password', 0, guard)
    saved = manager._load_audit_report()
    assert saved['regions']['jp']['status'] == 'complete'
    assert saved['regions']['intl']['status'] == 'failed'
    assert saved['status'] == 'complete'
    text = json.dumps(saved)
    assert 'private-' not in text and 'secret-cookie' not in text


def test_generated_file_replaced_not_imported_or_appended(audit_files):
    import csv
    manager, path = audit_files
    target = path / 'intl_override.csv'
    target.write_text('old-song,dx,sheets,3,internalLevelValue,14.0\n')
    report = manager._load_audit_report()
    report['fingerprint'] = manager._audit_fingerprint()
    manager._persist_audit(report)
    # Leave conflict unresolved so the same field can be edited again.
    saved = manager.save_music_level_correction('revision', 'intl', 0, 'A', 'master', 'internalLevelValue', 13.4)
    manager.save_music_level_correction(saved['revision'], 'intl', 0, 'A', 'master', 'internalLevelValue', 13)
    with target.open() as stream:
        assert list(csv.reader(stream)) == [['A', 'dx', 'sheets', '0', 'internalLevelValue', '13.0']]


def test_current_selection_set_survives_multiple_saves(audit_files):
    import csv
    manager, path = audit_files
    saved = manager.save_music_level_correction('revision', 'intl', 0, 'A', 'master', 'internalLevelValue', 13.4)
    manager.save_music_level_correction(saved['revision'], 'intl', 0, 'B', 'master', 'internalLevelValue', 13.5)
    with (path / 'intl_override.csv').open() as stream:
        assert list(csv.reader(stream)) == [
            ['A', 'dx', 'sheets', '0', 'internalLevelValue', '13.4'],
            ['B', 'dx', 'sheets', '0', 'internalLevelValue', '13.5']]


def test_manual_overrides_win_and_baseline_excludes_generated(audit_files):
    manager, path = audit_files
    (path / 'jp_override.csv').write_text('A,dx,sheets,0,internalLevelValue,12.0\n')
    (path / 'intl_override.csv').write_text('A,dx,sheets,0,internalLevelValue,12.5\n')
    assert manager.config.read_dxdata('jp')[0][0]['sheets'][0]['internalLevelValue'] == 12.0
    assert manager.config.read_dxdata('intl')[0][0]['sheets'][0]['internalLevelValue'] == 12.5
    assert manager.config.read_dxdata('jp', include_generated=False)[0][0]['sheets'][0]['internalLevelValue'] == 13.5
    (path / 'override.csv').write_text('A,dx,sheets,0,internalLevelValue,13.3\n')
    (path / 'intl_override.csv').write_text('A,dx,sheets,0,internalLevelValue,13.2\n')
    assert manager.config.read_dxdata('jp')[0][0]['sheets'][0]['internalLevelValue'] == 13.3
    assert manager.config.read_dxdata('intl')[0][0]['sheets'][0]['internalLevelValue'] == 13.3


def test_music_version_parser_and_selected_validation():
    selector = '<select name="version"><option value="0" selected>maimai</option><option value="13">でらっくす</option></select>'
    dom = etree.HTML(selector + block('A'))
    assert maimai.parse_music_version_options(dom) == {'0': 'maimai', '13': 'でらっくす'}
    assert maimai.parse_music_version_records(dom, '0')[0]['title'] == 'A'
    with pytest.raises(RuntimeError, match='different music version'):
        maimai.parse_music_version_records(dom, '13')
    with pytest.raises(RuntimeError, match='difficulty'):
        maimai.parse_music_version_records(etree.HTML(selector + block('A', difficulty='expert')), '0')


def test_version_fetch_uses_master_and_regional_host(monkeypatch):
    class Session:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
    selector = '<select name="version"><option value="0" selected>maimai</option></select>'
    monkeypatch.setattr(maimai, '_create_session', lambda *a, **kw: Session())
    fetch = AsyncMock(return_value=etree.HTML(selector + block('A')))
    monkeypatch.setattr(maimai, 'fetch_dom', fetch)
    groups = asyncio.run(maimai.get_music_version_lists({}, ver='intl'))
    assert groups[0]['url'] == 'https://maimaidx-eng.com/maimai-mobile/record/musicVersion/search/?version=0&diff=3'
    assert fetch.await_count == 1


def test_versions_are_compared_by_chart_type_and_link_is_skipped():
    from modules.dxdata_manager import audit_music_versions
    songs = [{'title': 'A', 'id': 'std', 'type': 'std', 'version': 'maimai', 'sheets': [{'difficulty': 'master'}]},
             {'title': 'A', 'id': 'dx', 'type': 'dx', 'version': 'maimaiでらっくす', 'sheets': [{'difficulty': 'master'}]},
             {'title': 'Link', 'id': 'l1', 'type': 'std', 'version': 'wrong', 'sheets': [{'difficulty': 'master'}]},
             {'title': 'Link', 'id': 'l2', 'type': 'std', 'version': 'wrong', 'sheets': [{'difficulty': 'master'}]}]
    groups = [{'version': 'GreeN', 'charts': [{'title': 'A', 'type': 'std', 'difficulty': 'master'},
                                          {'title': 'Link', 'type': 'std', 'difficulty': 'master'}]},
              {'version': 'でらっくす', 'charts': [{'title': 'A', 'type': 'dx', 'difficulty': 'master'}]}]
    issues = audit_music_versions(groups, {'songs': songs})
    assert len(issues) == 1
    assert issues[0]['chart']['song_id'] == 'std'
    assert issues[0]['chart']['version'] == 'maimai'
    assert issues[0]['official_version'] == 'GreeN'


def test_version_save_uses_song_version_csv_path(audit_files):
    import csv
    manager, path = audit_files
    report = manager._load_audit_report()
    versions = [{'version': 'GreeN', 'charts': [{'title': 'A', 'type': 'dx', 'difficulty': 'master'}]}]
    result = manager._recheck_music_levels('intl', report['regions']['intl']['levels'], version_lists=versions)
    result.update(status='complete', fetched_at='original')
    report['regions']['intl'] = result
    manager._persist_audit(report)
    index = next(i for i, issue in enumerate(result['issues']) if issue['kind'] == 'version_mismatch')
    saved = manager.save_music_level_correction('revision', 'intl', index, 'A', 'master', 'version', 'GreeN')
    with (path / 'intl_override.csv').open() as stream:
        assert list(csv.reader(stream)) == [['A', 'dx', 'version', 'GreeN']]
    assert saved['regions']['intl']['summary']['version_mismatches'] == 0


def test_audit_ignores_all_previous_overrides(audit_files):
    manager, path = audit_files
    (path / 'override.csv').write_text('A,dx,sheets,0,internalLevelValue,1.0\n')
    (path / 'intl_override.csv').write_text('A,dx,sheets,0,internalLevelValue,2.0\n')
    (path / 'jp_override.csv').write_text('A,dx,sheets,0,internalLevelValue,3.0\n')
    (path / 'intl_override.csv').write_text('A,dx,sheets,0,internalLevelValue,4.0\n')
    groups = manager._load_audit_report()['regions']['jp']['levels']
    for region in ('jp', 'intl'):
        result = manager._recheck_music_levels(region, groups)
        assert result['issues'][0]['before']['internalLevelValue'] == 13.5
        assert result['summary']['order_conflicts'] == 1


def test_updating_data_does_not_bake_in_handwritten_overrides(audit_files, monkeypatch):
    import json
    manager, path = audit_files
    source = json.loads((path / 'dxdata.json').read_text())
    (path / 'override.csv').write_text('A,dx,sheets,0,internalLevelValue,1.0\n')
    monkeypatch.setattr(manager, 'load_dxdata', lambda url: source)
    monkeypatch.setattr(manager, 'load_dxdata_version_history', lambda: None)
    monkeypatch.setattr(manager, 'save_dxdata_version_history', lambda stats: None)
    output = path / 'updated.json'
    assert manager.update_dxdata_with_comparison(['test-source'], str(output))['success']
    data = json.loads(output.read_text())
    assert data['songs'][0]['sheets'][0]['internalLevelValue'] == 13.5


def test_intl_official_splash_labels_match_dxdata():
    from modules.dxdata_manager import audit_music_versions
    for label, version in [('スプラッシュ', 'Splash'), ('スプラッシュ PLUS', 'Splash PLUS')]:
        groups = [{'version': label, 'charts': [{'title': 'A', 'type': 'dx', 'difficulty': 'master'}]}]
        data = {'songs': [{'title': 'A', 'type': 'dx', 'version': version, 'sheets': [{'difficulty': 'master'}]}]}
        assert not audit_music_versions(groups, data)


def inference_for(report, title):
    for issue in report['issues']:
        for key in ('before', 'after'):
            if issue[key]['title'] == title:
                return issue[key]['inference']
    raise AssertionError('Expected conflicting chart')


def test_order_inference_excludes_target_and_provides_neighbor_evidence():
    result = inference_for(audit([('A', 13.2), ('Target', 13.5), ('B', 13.3), ('C', 13.4)]), 'Target')
    assert (result['min'], result['max'], result['status']) == (13.2, 13.3, 'range')
    assert result['before']['title'] == 'A' and result['after']['title'] == 'B'
    assert result['after']['position'] == 3


def test_equal_neighbors_give_a_single_inferred_value():
    result = inference_for(audit([('A', 13.3), ('Target', 13.5), ('B', 13.3)]), 'Target')
    assert (result['min'], result['max'], result['status']) == (13.3, 13.3, 'exact')


def test_inference_supports_descending_order_and_missing_constants():
    result = inference_for(audit([('A', 13.4), ('Target', 13.1), ('Unknown', None), ('B', 13.3)],
                                 order='descending'), 'Target')
    assert (result['min'], result['max']) == (13.3, 13.4)
    assert result['after']['title'] == 'B'


def test_conflicting_anchors_are_not_used_to_prove_each_other():
    result = inference_for(audit([('A', 13.4), ('B', 13.2), ('Target', 13.5), ('C', 13.3), ('D', 13.1)]), 'Target')
    assert result['status'] == 'level_only'
    assert result['before'] is None and result['after'] is None
    assert result['excluded_anchors'] == 4
    assert (result['min'], result['max']) == (13.0, 13.5)


def test_ambiguous_link_and_out_of_bucket_values_cannot_anchor_inference():
    result = inference_for(audit([('Outside', 14), ('A', 13.3), ('Link', 13.4),
                                 ('Link', 13.1), ('Target', 13.5), ('B', 13.3)]), 'Target')
    assert (result['min'], result['max'], result['status']) == (13.3, 13.3, 'exact')
    assert result['before']['title'] == 'A'


def test_single_sided_inference_is_bounded_by_official_level():
    result = inference_for(audit([('Target', 13.5), ('After', 13.2)]), 'Target')
    assert (result['min'], result['max'], result['status']) == (13.0, 13.2, 'range')
    assert result['before'] is None


def test_level_fetch_skips_below_twelve(monkeypatch):
    class Session:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
    selector = '<select name="level"><option value="16">11+</option><option value="17">12</option><option value="18">12+</option></select>'
    monkeypatch.setattr(maimai, '_create_session', lambda *a, **kw: Session())
    monkeypatch.setattr(maimai.asyncio, 'sleep', AsyncMock())
    fetch = AsyncMock(side_effect=[etree.HTML(selector), etree.HTML(selector + block('A', level='12')), etree.HTML(selector + block('B', level='12+'))])
    monkeypatch.setattr(maimai, 'fetch_dom', fetch)
    groups = asyncio.run(maimai.get_music_level_lists({}))
    assert [g['level'] for g in groups] == ['12', '12+']
    assert all('level=16' not in call.args[1] for call in fetch.call_args_list)


def test_version_fetch_filters_using_official_level(monkeypatch):
    class Session:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
    selector = '<select name="version"><option value="0" selected>maimai</option></select>'
    monkeypatch.setattr(maimai, '_create_session', lambda *a, **kw: Session())
    monkeypatch.setattr(maimai, 'fetch_dom', AsyncMock(return_value=etree.HTML(selector + block('Low',level='11+') + block('Keep',level='12'))))
    groups = asyncio.run(maimai.get_music_version_lists({}))
    assert [r['title'] for r in groups[0]['charts']] == ['Keep']


def test_old_low_level_snapshots_do_not_produce_issues():
    from modules.dxdata_manager import audit_music_versions
    data = {'songs': [{'title': name, 'type': 'dx', 'version': 'wrong', 'sheets': [
        {'difficulty': 'master', 'internalLevelValue': value}]} for name,value in [('A',11.9),('B',11.6)]]}
    rows = [{'title': name, 'type': 'dx', 'difficulty': 'master','level':'11+'} for name in ('A','B')]
    assert not audit_music_levels([{'level':'11+','charts':rows}],data)['issues']
    assert not audit_music_versions([{'version':'maimai','charts':rows}],data)


def test_screenshot_link_remaster_is_ignored_even_when_uniquely_matched():
    names = ['Now or Never', 'アージェントシンメトリー', '雨露霜雪', 'The Cursed Doll',
             'ぽわわん劇場', 'チューリングの跡', 'Link', 'D✪N’T ST✪P R✪CKIN’']
    rows = []
    songs = []
    for name in names:
        difficulty = 'remaster' if name in ('Link', 'D✪N’T ST✪P R✪CKIN’') else 'expert' if name in ('雨露霜雪', 'チューリングの跡') else 'master'
        kind = 'std' if difficulty == 'remaster' else 'dx'
        rows.append({'title':name,'type':kind,'difficulty':difficulty})
        songs.append({'title':name,'type':kind,'version':'wrong','sheets':[
            {'difficulty':difficulty,'internalLevelValue':13 if name=='Link' else 13.5}]})
    result = audit_music_levels([{'level':'13','charts':rows}], {'songs':songs})
    assert result['issues'] == []
    # The uniquely matched Link must never become an anchor either.
    assert 'internalLevelValue' not in next(r for r in result['levels'][0]['charts'] if r['title']=='Link')


@pytest.mark.parametrize('kind', ['std', 'dx'])
def test_unique_link_master_is_ignored_for_version_checks(kind):
    from modules.dxdata_manager import audit_music_versions
    groups = [{'version':'maimai','charts':[{'title':'Link','type':kind,'difficulty':'master','level':'13'}]}]
    data = {'songs':[{'title':'Link','type':kind,'version':'wrong','sheets':[{'difficulty':'master'}]}]}
    assert audit_music_versions(groups,data) == []


def test_old_report_is_reanalyzed_without_another_login(audit_files, monkeypatch):
    manager, path = audit_files
    report = manager._load_audit_report()
    report.pop('analysis_version')
    manager._persist_audit(report)
    login = AsyncMock()
    monkeypatch.setattr(manager,'login_to_maimai',login)
    first = manager.get_music_level_report()
    assert first['analysis_version'] == manager._AUDIT_ANALYSIS_VERSION
    assert first['revision'] != 'revision'
    assert manager.get_music_level_report()['revision'] == first['revision']
    login.assert_not_called()


def test_oath_act_screenshot_only_proposes_the_inconsistent_chart():
    values = [('Re:Unknown X', 12.5), ('Oath Act', 12.6), ('紅に染まる恋の花', 12.5), ('泡沫、哀のまほろば', 12.5)]
    songs = [{'title': name, 'type': 'dx', 'sheets': [{'difficulty': 'master', 'internalLevelValue': value}]} for name,value in values]
    rows = [{'title':name,'type':'dx','difficulty':'master'} for name,_ in values]
    result = audit_music_levels([{'level':'12','charts':rows}], {'songs':songs})
    issue = result['issues'][0]
    assert [row['title'] for row in issue['correction_candidates']] == ['Oath Act']
    assert issue['correction_candidates'][0]['inference']['min'] == 12.5
    assert issue['correction_candidates'][0]['inference']['max'] == 12.5
    assert issue['after']['title'] == '紅に染まる恋の花'
    assert issue['after']['inference']['min'] == issue['after']['internalLevelValue']


def test_no_save_proposal_when_only_level_bounds_remain():
    report = audit([('A',13.4), ('B',13.2), ('Target',13.5), ('C',13.3), ('D',13.1)])
    for issue in report['issues']:
        assert all(row['inference']['status'] != 'level_only' for row in issue['correction_candidates'])


@pytest.mark.parametrize('region', ['jp', 'intl'])
def test_bulk_versions_preserves_constants_and_other_files(audit_files, region):
    import csv
    manager, path = audit_files
    report = manager.save_music_level_correction('revision', region, 0, 'A', 'master', 'internalLevelValue', 13)
    report = manager._load_audit_report()
    versions = [{'version': 'GreeN', 'charts': [
        {'title': name, 'type': 'dx', 'difficulty': 'master'} for name in ('A', 'B')]}]
    result = manager._recheck_music_levels(region, report['regions'][region]['levels'],
                                         report['corrections'][region], versions)
    result.update(status='complete', fetched_at='original')
    report['regions'][region] = result
    manager._persist_audit(report)
    saved = manager.save_music_version_corrections(report['revision'], region)
    with (path / f'{region}_override.csv').open() as stream:
        assert list(csv.reader(stream)) == [
            ['A', 'dx', 'sheets', '0', 'internalLevelValue', '13.0'],
            ['A', 'dx', 'version', 'GreeN'], ['B', 'dx', 'version', 'GreeN']]
    assert saved['regions'][region]['summary']['version_mismatches'] == 0
    other = 'jp' if region == 'intl' else 'intl'
    assert not (path / f'{other}_override.csv').exists()
    assert (path / 'override.csv').read_text() == 'unrelated,dx,version,old\n'
    with pytest.raises(ValueError, match='Report changed'):
        manager.save_music_version_corrections(report['revision'], region)


def test_bulk_versions_validates_all_before_writing(audit_files):
    manager, path = audit_files
    report = manager._load_audit_report()
    report['regions']['intl']['issues'] = [
        {'kind': 'version_mismatch', 'official_version': 'GreeN',
         'chart': {'song_id': song_id, 'difficulty': 'master'}} for song_id in ('A', 'missing')]
    manager._persist_audit(report)
    with pytest.raises(ValueError, match='ambiguous'):
        manager.save_music_version_corrections('revision', 'intl')
    assert not (path / 'intl_override.csv').exists()
