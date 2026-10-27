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

## Graphics specification

A graphics spec has `asset` and a `patches` list. Each patch supplies `label`, `text`, `pixel_offset`, `width`, `height`, `rect`, `original_sha256`, and `pixels`.

`rect` is `[x, y, width, height]`. The old hash covers unpacked palette indices in row order. `pixels` is Base85-encoded zlib data containing one index per byte; every index must be below sixteen. The patcher writes these into the original low/high nibbles.

## Opening scenario

`school_life.py` has its own layout-specific format: `dialogue`, seven `choices`, and optional `dialogue_counts`, `runtime_pairs`, `reclaim_unused_kanji`, and `bank_entries`. Read its synthetic tests before adapting it. This path is not interchangeable with the general repacker.
