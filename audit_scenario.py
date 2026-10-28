"""Audit a local scenario revision without including its dialogue in the report."""
import argparse
import json
from pathlib import Path
import re
import struct

from scenario_text import BASE, END, encode, parse, patch, read_words, source_variables, timing_commands


def effective_entries(spec):
    """Include legacy opening translations; explicit bank entries take priority."""
    entries = {}
    opening = spec.get('opening', {})
    for group in (0, 1):
        for entry, lines in opening.get('dialogue', {}).items():
            entries[group, int(entry)] = lines
    for banks in (opening.get('bank_entries', {}), spec.get('bank_entries', {})):
        for group, rows in banks.items():
            for entry, lines in rows.items():
                entries[int(group), int(entry)] = lines
    return entries


def check_revision(before, after, corrections):
    if before.get('opening') != after.get('opening'):
        raise ValueError('Legacy opening changed; review it separately before auditing bank overrides')
    previous, current = effective_entries(before), effective_entries(after)
    approved = {}
    for correction in corrections:
        key = tuple(correction['entry'])
        if len(key) != 2 or key in approved:
            raise ValueError('Correction entries must be unique [bank, entry] pairs')
        approved[key] = correction
    used = set()
    for key, old in previous.items():
        if key not in current:
            raise ValueError(f'Previous translation removed: {key}')
        if current[key] == old:
            continue
        correction = approved.get(key)
        if not correction or correction['before'] != old or correction['after'] != current[key]:
            raise ValueError(f'Changed translation needs an exact reviewed correction: {key}')
        used.add(key)
    if used != set(approved):
        raise ValueError('Unused or stale reviewed corrections')
    return previous, current


def check_expectations(entries, expectations):
    """Check reviewer-selected words, not an inferred character gender."""
    for expectation in expectations:
        key = tuple(expectation['entry'])
        if key not in entries:
            raise ValueError(f'Expectation refers to a missing translation: {key}')
        text = ' '.join(entries[key])
        for field, required in (('contains', True), ('excludes', False)):
            for word in expectation.get(field, []):
                found = bool(re.search(r'(?<!\w)' + re.escape(word) + r'(?!\w)', text, re.IGNORECASE))
                if found != required:
                    raise ValueError(f'Wording expectation failed at {key}: {field} {word!r}')


def audit(source, before, after, corrections=(), expectations=()):
    previous, current = check_revision(before, after, corrections)
    groups = parse(source, allow_sparse_gender=after.get('allow_sparse_gender', False))
    known = {(g['group'], e['id']) for g in groups for e in g['entries']}
    if not set(current) <= known:
        raise ValueError('Translation references a bank or entry absent from the parsed source')
    check_expectations(current, expectations)
    output, _ = patch(source, after)
    prepared = source
    if 'opening' in after:
        from school_life import patch as patch_opening
        prepared, _ = patch_opening(source, after['opening'])
    risky, changed = [], []
    for group in groups:
        for entry in group['entries']:
            key = (group['group'], entry['id'])
            lines = after.get('bank_entries', {}).get(str(key[0]), {}).get(str(key[1]))
            pointer = group['table'] + entry['id'] * 4
            old_offset = struct.unpack_from('<I', prepared, pointer)[0] - BASE
            expected = encode(lines, entry['words']) if lines is not None else read_words(prepared, old_offset)
            new_offset = struct.unpack_from('<I', output, pointer)[0] - BASE
            if read_words(output, new_offset) != expected:
                raise ValueError(f'Repacked pointer content mismatch: {key}')
            if lines is None or lines == previous.get(key):
                continue
            variables = [(0x2003, v[1]) if len(v) == 2 and 0x2003 <= v[0] <= 0x2008 else v
                         for v in source_variables(entry['words'])]
            if source_variables(expected) != variables or timing_commands(expected) != timing_commands(entry['words']):
                raise ValueError(f'Variables or timing changed: {key}')
            changed.append(list(key))
            reasons = []
            if len(lines) == 4:
                reasons.append('four lines')
            if variables:
                reasons.append('dynamic name or date')
            if timing_commands(expected):
                reasons.append('timed text')
            if reasons:
                risky.append({'entry': list(key), 'reasons': reasons})
    if output[END:] != source[END:]:
        raise ValueError('Event code changed')
    return {'result': 'passed', 'new_entries': len(set(current) - set(previous)),
            'reviewed_corrections': len(corrections), 'wording_expectations': len(expectations),
            'changed_entries': changed, 'layouts_to_review': risky,
            'all_pointer_contents_checked': True, 'variables_timing_event_code_preserved': True,
            'scope': 'Structural and reviewer-supplied wording checks only; no automatic translation-quality or gameplay certification.'}


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='Original decompressed scenario, supplied locally')
    parser.add_argument('--before', required=True, type=Path)
    parser.add_argument('--after', required=True, type=Path)
    parser.add_argument('--corrections', type=Path)
    parser.add_argument('--expectations', type=Path)
    parser.add_argument('--report', required=True, type=Path)
    args = parser.parse_args()
    report = audit(args.source.read_bytes(), read_json(args.before), read_json(args.after),
                   read_json(args.corrections) if args.corrections else [],
                   read_json(args.expectations) if args.expectations else [])
    args.report.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(f"PASS: {report['new_entries']} new entries; {report['reviewed_corrections']} reviewed corrections")


if __name__ == '__main__':
    main()
