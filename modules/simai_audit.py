"""Read-only note-count audit for MuConvert's musicNNNNNN/maidata.txt export.

Notation: https://w.atwiki.jp/simai/pages/1003.html
Chains count once per branch; touch holds belong to dxdata's hold bucket.
Unknown syntax fails the chart instead of publishing partial counts.
"""
import os
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

FIELDS = ('tap', 'hold', 'slide', 'touch', 'break', 'total')
DIFFICULTIES = {2: 'basic', 3: 'advanced', 4: 'expert', 5: 'master', 6: 'remaster', 7: 'utage'}


def source_directory():
    return Path(os.environ.get('SIMAI_CHART_DIR', 'simai_muconvert'))


def source_signature():
    root = source_directory()
    return [(str(root), root.is_dir())] + [
        (str(p), p.stat().st_size, p.stat().st_mtime_ns)
        for p in sorted(root.glob('*/maidata.txt'))]


def count_notes(chart):
    chart = re.sub(r'>>[^\n]*', '', chart)
    chart = re.sub(r'\s+', '', chart)
    if not chart.endswith('E'):
        raise ValueError('缺少谱面结束标记 E')
    chart = chart[:-1]
    chart = re.sub(r'\([^()]+\)|\{[^{}]+\}', '', chart)
    chart = re.sub(r'\[[0-9.:#+\-]+\]', '~', chart)
    counts = dict.fromkeys(FIELDS[:-1], 0)
    for token in re.split(r'[,/`]', chart):
        if not token or token == '0':
            continue
        if re.fullmatch(r'[1-8]{2,}', token):
            counts['tap'] += len(token)
            continue
        touch = re.fullmatch(r'(?:[ABDE][1-8]|C[12]?)(h?f?)(~?)', token)
        if touch:
            flags, duration = touch.groups()
            if duration and 'h' not in flags:
                raise ValueError(f'无效 TOUCH: {token}')
            counts['hold' if 'h' in flags else 'touch'] += 1
            continue
        head = re.match(r'[1-8]([bx$@?!]*)(.*)', token)
        if not head:
            raise ValueError(f'不支持的音符: {token[:100]}')
        flags, tail = head.groups()
        if not tail:
            if '?' in flags or '!' in flags:
                raise ValueError(f'无效 TAP: {token}')
            counts['break' if 'b' in flags else 'tap'] += 1
        elif re.fullmatch(r'h[bx]*~?[bx]*', tail):
            counts['break' if 'b' in flags + tail else 'hold'] += 1
        else:
            branches = tail.split('*')
            for branch in branches:
                # One connected chain is one judged slide, even with per-segment durations.
                if not re.fullmatch(r'(?:(?:pp|qq|[-^<>vpqszw])[1-8]|V[1-8]{2})(?:~?)(?:(?:(?:pp|qq|[-^<>vpqszw])[1-8]|V[1-8]{2})~?)*b?', branch) or '~' not in branch:
                    raise ValueError(f'不支持的 SLIDE: {token[:100]}')
                counts['break' if branch.endswith('b') else 'slide'] += 1
            if '?' not in flags and '!' not in flags:
                counts['break' if 'b' in flags else 'tap'] += 1
    counts['total'] = sum(counts.values())
    return counts


def _title(value):
    return unicodedata.normalize('NFKC', value).strip()


def _expected_counts(sheet, chart_type):
    counts = dict(sheet.get('noteCounts') or {})
    if chart_type == 'std' and counts.get('touch') is None:
        counts['touch'] = 0
    return counts


def _chart_type(directory_name):
    match = re.fullmatch(r'music(\d{6})(?:_[LR])?', directory_name)
    if not match:
        raise ValueError('无法确定目录的谱面类型')
    music_id = int(match[1])
    return 'utage' if music_id >= 100000 else 'dx' if music_id >= 10000 else 'std'


def _read_chart_file(path):
    content = path.read_text(encoding='utf-8-sig')
    # Only a new field at the start of a line ends the previous value. Titles and
    # artists may contain literal ampersands (for example, "あひる & KTA").
    pairs = re.findall(
        r'^&([^=\r\n]+)=(.*?)(?=^&[^=\r\n]+=|\Z)',
        content,
        re.M | re.S,
    )
    metadata = dict(pairs)
    if len(pairs) != len(metadata) or 'title' not in metadata:
        raise ValueError('缺少标题或存在重复字段')

    blocks = [
        (int(key[6:]), value)
        for key, value in metadata.items()
        if re.fullmatch(r'inote_\d+', key)
    ]
    if not blocks:
        raise ValueError('没有谱面块')

    chart_type = _chart_type(path.parent.name)
    source = f'{path.parent.name}/maidata.txt'
    return [
        ({
            'title': metadata['title'].strip(),
            'type': chart_type,
            'difficulty': DIFFICULTIES.get(slot, f'inote_{slot}'),
            'source': source,
            'slot': slot,
        }, body)
        for slot, body in blocks
        if slot != 7
    ]


def _load_records(paths):
    records, issues = [], []
    for path in paths:
        try:
            records.extend(_read_chart_file(path))
        except (OSError, UnicodeError, ValueError) as exc:
            issues.append({
                'kind': 'note_parse_error',
                'chart': {
                    'title': path.parent.name,
                    'source': f'{path.parent.name}/maidata.txt',
                },
                'message': str(exc),
            })
    return records, issues


def _song_index(songs):
    index = defaultdict(list)
    for song in songs:
        for sheet in song.get('sheets', []):
            chart_type = sheet.get('type', song.get('type'))
            difficulty = sheet.get('difficulty')
            if chart_type == 'utage' or difficulty == 'utage':
                continue
            index[(_title(song['title']), chart_type, difficulty)].append((song, sheet))
    return index


def _link_record_matches(records, index):
    # Link is the only special case: compare partial category agreement within
    # the same difficulty. Require a unique best match in both directions.
    link_scores, link_parsed = {}, {}
    for record_index, (chart, body) in enumerate(records):
        if _title(chart['title']) != 'Link' or chart['type'] == 'utage':
            continue
        key = ('Link', chart['type'], chart['difficulty'])
        try:
            actual = link_parsed[record_index] = count_notes(body)
        except ValueError:
            continue
        for candidate_index, (_, sheet) in enumerate(index.get(key, [])):
            expected = _expected_counts(sheet, chart['type'])
            # STD's inapplicable TOUCH bucket is not evidence of song identity.
            fields = [f for f in FIELDS if not (chart['type'] == 'std' and f == 'touch')]
            score = sum(type(expected.get(f)) is int and expected[f] == actual[f] for f in fields)
            link_scores[(record_index, key, candidate_index)] = score
    link_matches = {}
    for record_index, (chart, _) in enumerate(records):
        if _title(chart['title']) != 'Link':
            continue
        key = ('Link', chart['type'], chart['difficulty'])
        choices = [(i, link_scores.get((record_index, key, i), 0))
                   for i in range(len(index.get(key, [])))]
        best = max((score for _, score in choices), default=0)
        winners = [i for i, score in choices if score == best and score > 0]
        if len(winners) != 1:
            continue
        candidate_index = winners[0]
        # Do not let two source files claim the same dxdata chart.
        rivals = [score for (r, k, i), score in link_scores.items()
                  if k == key and i == candidate_index and r != record_index]
        if all(best > score for score in rivals):
            link_matches[record_index] = candidate_index
    return link_matches, link_parsed


def _record_key(chart):
    return _title(chart['title']), chart['type'], chart['difficulty']


def _compare_records(records, index, issues, file_count):
    identities = Counter(_record_key(chart) for chart, _ in records)
    link_matches, link_parsed = _link_record_matches(records, index)
    summary = {'files': file_count, 'charts': len(records), 'matched': 0, 'equal': 0,
               'mismatches': 0, 'unmatched': 0, 'parse_errors': len(issues)}
    covered = set()
    for record_index, (chart, body) in enumerate(records):
        key = _record_key(chart)
        candidates = index.get(key, [])
        candidate_index = 0
        ambiguous = len(candidates) != 1 or identities[key] != 1
        if ambiguous and record_index in link_matches:
            candidate_index = link_matches[record_index]
            ambiguous = False
            chart['match_method'] = 'link_partial_counts'
        if ambiguous or chart['type'] == 'utage':
            summary['unmatched'] += 1
            issues.append({'kind': 'note_unmatched', 'chart': chart, 'message': '宴谱需单独映射' if chart['type'] == 'utage' else '找不到唯一的歌曲、类型和难度匹配', 'candidates': len(candidates)})
            continue
        song, sheet = candidates[candidate_index]
        chart['song_id'] = song.get('id')
        summary['matched'] += 1
        covered.add((key, candidate_index))
        try:
            actual = link_parsed[record_index] if record_index in link_parsed else count_notes(body)
        except ValueError as exc:
            summary['parse_errors'] += 1
            issues.append({'kind': 'note_parse_error', 'chart': chart, 'message': str(exc)})
            continue
        expected = _expected_counts(sheet, chart['type'])
        differences = {k: {'dxdata': expected.get(k), 'simai': actual[k]} for k in FIELDS
                       if type(expected.get(k)) is not int or expected[k] != actual[k]}
        if differences:
            summary['mismatches'] += 1
            issues.append({'kind': 'note_mismatch', 'chart': chart, 'differences': differences})
        else:
            summary['equal'] += 1
    summary['dxdata_uncovered'] = sum((key, i) not in covered for key, candidates in index.items() for i in range(len(candidates)))
    return summary


def audit_note_counts(songs, directory=None):
    root = Path(directory) if directory is not None else source_directory()
    all_paths = sorted(root.glob('*/maidata.txt'))
    if not all_paths:
        return {
            'status': 'unavailable',
            'message': '未找到 Simai 谱面库，请上传 simai_muconvert 或设置 SIMAI_CHART_DIR。',
            'issues': [],
            'summary': {},
        }

    # Ignore banquet exports before reading them, including paired L/R files.
    paths = []
    for path in all_paths:
        try:
            if _chart_type(path.parent.name) == 'utage':
                continue
        except ValueError:
            # Keep malformed directory names so the loader reports them.
            pass
        paths.append(path)
    records, issues = _load_records(paths)
    summary = _compare_records(records, _song_index(songs), issues, len(paths))
    priority = {'note_mismatch': 0, 'note_parse_error': 1, 'note_unmatched': 2}
    issues.sort(key=lambda issue: priority[issue['kind']])
    return {'status': 'complete', 'summary': summary, 'issues': issues}
