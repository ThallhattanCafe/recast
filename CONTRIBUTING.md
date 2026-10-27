# Contributing

Keep changes small enough to explain and test. A codec fix and an unrelated documentation rewrite are easier to review separately.

Use synthetic fixtures in bug reports. Include the command, Python version, expected behaviour, and actual result. For game-specific failures, identify the revision and affected asset or scene without attaching the disc or extracted content.

Before submitting a change, run the unit tests and `python demo.py`.

Do not add translation scripts, patch manifests, ROMs, BIOS files, extracted assets, screenshots, emulator binaries, saves, or personal filesystem paths. Check the actual staged files; `.gitignore` cannot catch everything.

If a change affects loading or rendering, describe the emulator check separately from the unit tests. Mention any modified states used to reach the scene.

A useful pull request explains the failure, the fix, and what was checked. There is no need for a long template.
