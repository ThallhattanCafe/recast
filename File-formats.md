# Manifest and text formats

These notes describe the current implementation. The formats are not a stable compatibility promise, and no real-game translation bundle is included.

## Build manifest

| Field | Meaning |
| --- | --- |
| `version` | Version recorded in the report. |
| `output_name` | Plain output basename, without `.bin`. |
| `source_size` | Exact source BIN size. |
| `source_sha256` | SHA-256 of that source. |
| `translations` | Fixed-length text entries; may be empty. |
| `binary_patches` | Optional checked byte replacements. |
| `graphic_assets` | Optional compressed graphics assets. |
| `school_life_assets` | Optional compressed scenarios. |
| `compressed_overlays` | Optional overlays rebuilt from text entries. |

A fixed text entry uses `file`, `lba`, `offset`, `capacity`, `english`, and `original_hex`. The replacement occupies the same number of bytes. Its alphabet is defined by `ENC` in `build_game.py` and differs from the scenario alphabet.

A binary patch uses `file`, `lba`, `offset`, `original_hex`, and `new_hex`. Old and new lengths must match.

A graphics or scenario asset uses `file`, `lba`, `size`, and `spec`. Set `module` to `scenario_text` for the general scenario repacker; otherwise the opening-scenario patcher is used. `size` is the original compressed allocation. An overlay instead uses `uncompressed_file` to match text entries.

Manifests and specs are trusted local inputs, not sandboxed programs. Review unfamiliar files before using them.

## Scenario specification

`bank_entries` maps bank numbers to entry numbers, both as JSON keys. Each entry is an array of one to four lines. This example is invented:

```json
{"bank_entries": {"0": {"1": ["Hello, {name}!"]}}}
```

Supported placeholders include `{family}`, `{name}`, `{nickname}`, `{month}`, `{day}`, `{addressed_name}`, and parameterized names such as `{v2005_10}`. The corresponding variable must exist in the source. Addressed names retain their speaker argument and normalize Japanese suffix variants for English.

Timing tokens such as `{speed_15}` and `{speed_255}` must retain the source values, order, and count. Longer English can still change rendering duration; check it in the emulator.

Plain scenario text supports ASCII letters, digits, spaces, and `?!.,':-()`. Curly quotes, accents, and arbitrary Unicode are unsupported.

### Missing gender bank

Set `"allow_sparse_gender": true` in a scenario spec for the observed male-only layout: bank 0 exists, bank 1 is null, and shared banks follow it. Bank numbers stay unchanged, so the first shared bank remains bank 2. Parsing stops at other holes. Leave the option off for ordinary layouts; this is not a general repair switch for malformed data.

### Native date tables

Some date controls index individual glyph cells rather than ordinary dialogue strings. Packed Latin text would change those cell positions. These tokens preserve the native layout:

- `{native_date_alphabet}` replaces only the month/day labels with M/D, retaining the ten digit indices, space and terminator. It must be the entire entry and the source must match the expected table shape.
- `{native_date_labels}` preserves the six label cells and terminator, changing only the month/day cells to M/D. It also requires an entry of its own and a matching source shape.
- `{source_line_1}`, `{source_line_2}` and `{source_line_3}` copy the corresponding original numeric grid rows, numbered after the first line. Only digits and the native spacing glyph are accepted. Dialogue, names and control commands cannot be copied this way.

These glyph IDs and shapes are specific to the supported game. They are not a general date-format API. See `test_native_tables.py` for generated examples and rejection cases.

### Reviewing a revision

`audit_scenario.py` reads two local scenario specs and an original decompressed asset. Its optional correction file is a JSON array of exact before/after edits. This example is invented:

```json
[{"entry": [0, 0], "before": ["Hello."], "after": ["Good morning."]}]
```

The optional expectations file checks words selected by a reviewer:

```json
[{"entry": [1, 0], "contains": ["her"], "excludes": ["him", "they", "them", "their"]}]
```

Each `entry` is `[bank, entry_number]`. Matching is case-insensitive and uses word boundaries. These checks do not infer gender or judge translation quality. Specify expectations only after reading the source and scene context; plural pronouns can be correct elsewhere.

Legacy `opening.dialogue` and `opening.bank_entries` count as existing translations. An explicit bank override needs the same reviewed correction as any other edit. Changing the legacy opening specification itself requires a separate review. The report contains counts, entry IDs and layout flags, not dialogue text.

## Graphics specification

A graphics spec has `asset` and a `patches` list. Each patch supplies `label`, `text`, `pixel_offset`, `width`, `height`, `rect`, `original_sha256`, and `pixels`.

`rect` is `[x, y, width, height]`. The old hash covers unpacked palette indices in row order. `pixels` is Base85-encoded zlib data containing one index per byte; every index must be below sixteen. The patcher writes these into the original low/high nibbles.

## Opening scenario

`school_life.py` has its own layout-specific format: `dialogue`, seven `choices`, and optional `dialogue_counts`, `runtime_pairs`, `reclaim_unused_kanji`, and `bank_entries`. Read its synthetic tests before adapting it. This path is not interchangeable with the general repacker.

