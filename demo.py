"""Run a small Recast example without any game files."""
import struct
from lz_halfword import pack, unpack, check_stream_budget
from scenario_text import encode, source_variables


def main():
    source = struct.pack('<64H', *range(64)) + bytes(4096)
    compressed = pack(source)
    assert unpack(compressed) == source
    peak = check_stream_budget(compressed)
    encoded = encode(['Hello, {name}!'], [0x2001, 0x3001])
    assert source_variables(encoded) == [(0x2001,)]
    print(f'Codec round trip: {len(source)} bytes -> {len(compressed)} bytes')
    print(f'Peak decoded bytes per input sector: {peak}')
    print(f'Name-aware text encoded into {len(encoded)} halfwords.')
    print('All example data was generated in memory. No files were written.')


if __name__ == '__main__':
    main()
