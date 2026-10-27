# Getting started

Start with the tests. They exercise the codec, text repacker, and graphics patcher without loading any game files.

```sh
python --version
python -m unittest discover -s . -p "test_*.py"
python demo.py
```

Python 3.11 or later is required because the disc builder uses `hashlib.file_digest`. Everything else also uses the standard library.

## Build with your own data

You need a source BIN, a manifest, and the specification files named by that manifest. Keep the specs beside the manifest. The current builder expects plain filenames in `spec` fields, not nested paths.

```sh
python build_game.py "original.bin" --manifest "translation-data/translations.json" --output-dir "build"
```

The manifest identifies the source by size and SHA-256. A different dump or revision is rejected before output is written. The writer creates a single MODE2/2352 track; it does not import arbitrary CUE layouts.

The output folder receives a BIN, a matching CUE, and `build-report.json`. If that BIN already exists, choose another output folder.

There is no working translation manifest in this repository. Cloning it alone will not produce an English game.

## Encode a text line

This example uses an invented source string with a given-name command:

```python
from scenario_text import encode
words = encode(["Hello, {name}!"], [0x2001, 0x3001])
```

The encoder accepts one to four lines, up to forty columns each. Name placeholders reserve sixteen columns and dates reserve four. A variable must already exist in the source entry.

Keep game images, extracted files, manifests, screenshots, and saves outside the checkout. Run normal Python, without `-O`: the implementation uses assertions for many format checks.
