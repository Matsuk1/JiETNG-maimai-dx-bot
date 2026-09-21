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
COMMENT_RE, SPACE_RE = re.compile(r'>>[^\n]*'), re.compile(r'\s+')
TIMING_RE, DURATION_RE = re.compile(r'\([^()]+\)|\{[^{}]+\}'), re.compile(r'\[[0-9.:#+\-]+\]')
MULTI_TAP_RE, TOUCH_RE = re.compile(r'[1-8]{2,}'), re.compile(r'(?:[ABDE][1-8]|C[12]?)(h?f?)(~?)')
HEAD_RE, HOLD_RE = re.compile(r'[1-8]([bx$@?!]*)(.*)'), re.compile(r'h[bx]*~?[bx]*')
SLIDE_RE = re.compile(r'(?:(?:pp|qq|[-^<>vpqszw])[1-8]|V[1-8]{2})(?:~?)(?:(?:(?:pp|qq|[-^<>vpqszw])[1-8]|V[1-8]{2})~?)*b?')
DIRECTORY_RE, NOTE_FIELD_RE = re.compile(r'music(\d{6})(?:_[LR])?'), re.compile(r'inote_\d+')


def source_directory():
    return Path(os.environ.get('SIMAI_CHART_DIR', 'simai_muconvert'))


def source_signature():
    root = source_directory()
    signatures = [(str(root), root.is_dir())]
    for path in sorted(root.glob('*/maidata.txt')):
        stat = path.stat()
        signatures.append((str(path), stat.st_size, stat.st_mtime_ns))
    return signatures


def count_notes(chart):
    chart = COMMENT_RE.sub('', chart)
    chart = SPACE_RE.sub('', chart)
    if not chart.endswith('E'):
        raise ValueError('缺少谱面结束标记 E')
    chart = chart[:-1]
    chart = TIMING_RE.sub('', chart)
    chart = DURATION_RE.sub('~', chart)
    counts = dict.fromkeys(FIELDS[:-1], 0)
    for token in re.split(r'[,/`]', chart):
        if not token or token == '0':
            continue
        if MULTI_TAP_RE.fullmatch(token):
            counts['tap'] += len(token)
            continue
        touch = TOUCH_RE.fullmatch(token)
        if touch:
            flags, duration = touch.groups()
            if duration and 'h' not in flags:
                raise ValueError(f'无效 TOUCH: {token}')
            counts['hold' if 'h' in flags else 'touch'] += 1
            continue
        head = HEAD_RE.match(token)
        if not head:
            raise ValueError(f'不支持的音符: {token[:100]}')
        flags, tail = head.groups()
        if not tail:
            if '?' in flags or '!' in flags:
                raise ValueError(f'无效 TAP: {token}')
            counts['break' if 'b' in flags else 'tap'] += 1
        elif HOLD_RE.fullmatch(tail):
            counts['break' if 'b' in flags + tail else 'hold'] += 1
        else:
            branches = tail.split('*')
            for branch in branches:
                # One connected chain is one judged slide, even with per-segment durations.
                if not SLIDE_RE.fullmatch(branch) or '~' not in branch:
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


def _load_records(paths):
    records, issues = [], []
    for path in paths:
        try:
            content = path.read_text(encoding='utf-8-sig')
            # Only a field at the start of a line ends the previous value.
            pairs = re.findall(r'^&([^=\r\n]+)=(.*?)(?=^&[^=\r\n]+=|\Z)',
                               content, re.M | re.S)
            metadata = dict(pairs)
            if len(pairs) != len(metadata) or 'title' not in metadata:
                raise ValueError('缺少标题或存在重复字段')
            number = DIRECTORY_RE.fullmatch(path.parent.name)
            if not number:
                raise ValueError('无法确定目录的谱面类型')
            music_id = int(number[1])
            chart_type = 'utage' if music_id >= 100000 else 'dx' if music_id >= 10000 else 'std'
            blocks = [(int(k[6:]), v) for k, v in metadata.items() if NOTE_FIELD_RE.fullmatch(k)]
            if not blocks:
                raise ValueError('没有谱面块')
            for slot, body in blocks:
                if slot != 7:
                    records.append(({
                        'title': metadata['title'].strip(), 'type': chart_type,
                        'difficulty': DIFFICULTIES.get(slot, f'inote_{slot}'),
                        'source': f'{path.parent.name}/maidata.txt', 'slot': slot,
                    }, body))
        except (OSError, UnicodeError, ValueError) as exc:
            issues.append({'kind': 'note_parse_error', 'chart': {'title': path.parent.name, 'source': f'{path.parent.name}/maidata.txt'}, 'message': str(exc)})
    return records, issues


def audit_note_counts(songs, directory=None):
    root = Path(directory) if directory is not None else source_directory()
    paths = sorted(root.glob('*/maidata.txt'))
    if not paths:
        return {'status': 'unavailable', 'message': '未找到 Simai 谱面库，请上传 simai_muconvert 或设置 SIMAI_CHART_DIR。', 'issues': [], 'summary': {}}
    # Ignore banquet exports before reading them, including paired L/R files.
    paths = [p for p in paths if not (
        (number := DIRECTORY_RE.fullmatch(p.parent.name))
        and int(number[1]) >= 100000)]
    index = defaultdict(list)
    for song in songs:
        for sheet in song.get('sheets', []):
            if sheet.get('type', song.get('type')) == 'utage' or sheet.get('difficulty') == 'utage':
                continue
            index[(_title(song['title']), sheet.get('type', song.get('type')), sheet['difficulty'])].append((song, sheet))
    records, issues = _load_records(paths)
    identities = Counter((_title(c['title']), c['type'], c['difficulty']) for c, _ in records)
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
    summary = {'files': len(paths), 'charts': len(records), 'matched': 0, 'equal': 0, 'mismatches': 0, 'unmatched': 0, 'parse_errors': len(issues)}
    covered = set()
    for record_index, (chart, body) in enumerate(records):
        key = (_title(chart['title']), chart['type'], chart['difficulty'])
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
    priority = {'note_mismatch': 0, 'note_parse_error': 1, 'note_unmatched': 2}
    issues.sort(key=lambda issue: priority[issue['kind']])
    return {'status': 'complete', 'summary': summary, 'issues': issues}
