# Recast

PSX (original PlayStation) game translation tools for unpacking data, repacking text, and rebuilding checked disc images.

<p>
  <a href="https://psxdatacenter.com/games/J/S/SLPS-02120.html">
    <img src="https://psxdatacenter.com/images/covers/J/S/SLPS-02120.jpg" width="250" alt="Japanese cover of Shiritsu Justice Gakuen: Nekketsu Seishun Nikki 2">
  </a>
</p>

*Current translation project: Shiritsu Justice Gakuen: Nekketsu Seishun Nikki 2.* Cover art © Capcom; [scan source](https://psxdatacenter.com/games/J/S/SLPS-02120.html).

Recast handles the part after translation: fitting text back into the game, keeping names and control codes intact, and rebuilding the disc without disturbing unrelated sectors.

Current format support is for *Shiritsu Justice Gakuen: Nekketsu Seishun Nikki 2* (SLPS-02120), the current translation project. Recast has not been tested with other games. Format support will expand when a new translation project starts.

This repository contains the tools, tests, and documentation. It does not include translation data or a playable English patch. Recast does not translate dialogue automatically.

The latest update brings in the sparse gender-bank and native date-table handling used to finish the current project's extracted text catalogue. It also adds a local revision audit and synthetic regression tests. Combat-exam instructions and move-list screens are the next translation work in that project; this update does not add support for those remaining screens. See the [change notes](CHANGELOG.md).

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
| `audit_scenario.py` | Check local revisions, reviewed corrections and explicit wording expectations. |
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

## License

Recast's tools and documentation are available under the [MIT License](LICENSE). Game artwork and other third-party material remain the property of their respective owners.

