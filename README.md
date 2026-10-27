# Recast

PSX (original PlayStation) game translation tools for unpacking data, repacking text, and rebuilding checked disc images.

Recast handles the part after translation: fitting text back into the game, keeping names and control codes intact, and rebuilding the disc without disturbing unrelated sectors. It started with the PS1 version of *Shiritsu Justice Gakuen: Nekketsu Seishun Nikki 2* (SLPS-02120). Its current offsets and runtime hooks are specific to that revision.

This repository contains the tools, tests, and documentation. It does not include translation data or a playable English patch. Recast does not translate dialogue automatically.

## Try it

You need Python 3.11 or later. There are no third-party Python dependencies.

```sh
python -m unittest discover -s . -p "test_*.py"
python demo.py
python build_game.py --help
```

The tests and demo use synthetic data. You do not need a game image to run them.

To build a disc, supply your own compatible manifest, its referenced specifications, and the exact source image the manifest expects:

```sh
python build_game.py "path/to/original.bin" --manifest "path/to/translation-data/translations.json" --output-dir "build"
```

No real-game manifest is included here. The builder writes a separate BIN, a CUE, and a build report. It refuses to replace an existing output BIN.

## What's here

| File | Job |
| --- | --- |
| `build_game.py` | Apply a manifest, repair sector checksums, and verify the rebuilt disc. |
| `lz_halfword.py` | Encode and decode halfword LZ streams with CD streaming limits. |
| `scenario_text.py` | Repack dialogue while preserving table locations and event code. |
| `latin_runtime.py` | Assemble the MIPS helper for paired Latin glyphs. |
| `school_life.py` | Handle the opening scenario's older text and glyph layout. |
| `palette_patch.py` | Replace checked rectangles in four-bit indexed graphics. |
| `test_*.py` | Regression tests using synthetic fixtures. |
| `demo.py` | A small codec and text-encoding example. |

## Documentation

- [Getting started](Getting-started.md)
- [How it works](Architecture.md)
- [Manifest and text formats](File-formats.md)
- [Testing and troubleshooting](Testing.md)
- [Contributing](CONTRIBUTING.md)
- [Wiki](https://github.com/ThallhattanCafe/recast/wiki)

## Current limits

Recast is not a general PS1 patcher. Related games may share formats, but their addresses and behaviour need to be checked independently. The disc writer currently targets one MODE2/2352 track.

The tools came from the v0.28 translation workflow. That workflow has passed targeted emulator checks, not a complete school-year or real-BIOS playthrough. Passing the tests here does not establish that a particular translation is playable.

Game images, BIOS files, extracted assets, translation scripts, patch manifests, emulator binaries, and saves are excluded. No license has been selected for this repository yet.
