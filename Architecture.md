# How Recast works

The builder checks the source image, stages changes in memory, and validates their original bytes and sizes. It then copies the source, writes the changed sectors, and compares the entire output with the expected rebuild.

## Disc layer

The supported image uses 2352-byte raw sectors. Mode 2 Form 1 user data occupies 2048 bytes starting at byte 24. Every changed sector receives repaired EDC/ECC. The generated CUE describes a single MODE2/2352 track.

A manifest supplies file locations and allocations. Recast does not discover every file or identify an unknown game automatically.

## Compression

The LZ codec works on 16-bit words. The game's memory decoder and CD streaming decoder differ around zero runs, so the encoder avoids zero-run tokens.

A stream can decompress correctly offline and still fail in-game. Long copies can keep the decoder busy while the next CD input arrives. Copies after the first sixteen tokens are capped at eight words. The builder checks a conservative limit of 16,000 decoded bytes per input sector.

The first token group stays stable because the loader checks its fingerprint. Where the allocation requires it, references are expanded into literals so the terminator lands in the final occupied CD sector. Adding empty sectors after an early terminator is not equivalent.

## Text

The scenario repacker encodes replacements, deduplicates strings, and fits them into identified string allocations and a checked zero-filled tail. It updates string pointers while keeping tables and event code in place.

Parse the original asset. The parser expects ordered original strings before their tables; deduplicated output does not meet that assumption. Inspect a patched asset using the original table metadata and the output pointers.

The Latin helper packs two seven-bit ASCII characters into one high-bit text word and combines existing glyph pixels into a scratch tile. It waits for the previous upload before reusing the tile. Its addresses and executable hook are specific to SLPS-02120.

Inserting the runtime blob into an asset does not install the executable hook. A complete external manifest must include the matching binary patch.

## Graphics

The graphics patcher replaces four-bit palette indices in rectangles. It checks the old rectangle's hash, bounds, new index values, and overlap. It does not change the palette or upscale textures.
