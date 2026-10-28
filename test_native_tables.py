"""Synthetic regressions for sparse banks and glyph-indexed date tables."""
import struct
import unittest

from scenario_text import BASE, START, END, encode, parse, patch, read_words
from test_scenario_text import fixture


class NativeTableTests(unittest.TestCase):
    def test_sparse_bank_numbers_and_null_slot_survive_repacking(self):
        source = bytearray(fixture())
        second = struct.unpack_from('<I', source, START + 4)[0]
        struct.pack_into('<2I', source, START + 4, 0, second)
        self.assertEqual([g['group'] for g in parse(source)], [0])
        groups = parse(source, allow_sparse_gender=True)
        self.assertEqual([g['group'] for g in groups], [0, 2])
        out, report = patch(source, {
            'allow_sparse_gender': True,
            'bank_entries': {'2': {'1': ['Common menu']}},
        })
        self.assertEqual(out[START:START + 12], source[START:START + 12])
        self.assertEqual(out[END - 4:], source[END - 4:])
        self.assertEqual(report['entries'][0]['group'], 2)
        for group in groups:
            for entry in group['entries']:
                pointer = struct.unpack_from('<I', out, group['table'] + entry['id'] * 4)[0] - BASE
                expected = encode(['Common menu'], entry['words']) if (group['group'], entry['id']) == (2, 1) else entry['words']
                self.assertEqual(read_words(out, pointer), expected)

    def test_sparse_option_does_not_skip_arbitrary_holes(self):
        source = bytearray(fixture())
        second = struct.unpack_from('<I', source, START + 4)[0]
        struct.pack_into('<3I', source, START + 4, 0, 0, second)
        self.assertEqual([g['group'] for g in parse(source, True)], [0])
        source = bytearray(fixture())
        struct.pack_into('<2I', source, START + 8, 0, second)
        self.assertEqual([g['group'] for g in parse(source, True)], [0, 1])

    def test_date_alphabet_preserves_digit_indices_and_length(self):
        source = [10, 1, 2, 3, 4, 5, 6, 7, 8, 9, 700, 701, 1566, 0x3001]
        out = encode(['{native_date_alphabet}'], source)
        self.assertEqual(out, source[:10] + [23, 14, 1566, 0x3001])
        self.assertEqual(len(out), len(source))

    def test_date_labels_preserve_cell_positions(self):
        source = [1566, 1566, 700, 1566, 1566, 701, 0x3001]
        self.assertEqual(encode(['{native_date_labels}'], source),
                         [1566, 1566, 23, 1566, 1566, 14, 0x3001])

    def test_grid_rows_preserve_numbers_and_spacing(self):
        rows = [1, 1566, 2, 0x3000, 3, 4, 1566, 0x3000, 10, 1566, 9]
        source = [700, 0x3000] + rows + [0x3001]
        out = encode(['Choose a date', '{source_line_1}', '{source_line_2}', '{source_line_3}'], source)
        self.assertEqual(out[out.index(0x3000):], source[source.index(0x3000):])

    def test_native_tokens_reject_wrong_shapes_or_non_numeric_rows(self):
        cases = [
            (['{native_date_alphabet}'], [0] * 14),
            (['{native_date_labels}'], [0] * 7),
            (['Prefix {native_date_labels}'], [1566, 1566, 700, 1566, 1566, 701, 0x3001]),
            (['{source_line_1}'], [1, 0x3000, 700, 0x3001]),
            (['{source_line_1}'], [1, 0x3000, 0x2001, 0x3001]),
            (['{source_line_1}'], [1, 0x3000, 0x3001]),
            (['{source_line_3}'], [1, 0x3001]),
        ]
        for lines, source in cases:
            with self.subTest(lines=lines, source=source), self.assertRaises(AssertionError):
                encode(lines, source)


if __name__ == '__main__':
    unittest.main()
