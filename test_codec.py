"""Regression checks for the game's two different LZ decoder behaviors."""
import struct,unittest
from lz_halfword import pack,unpack
class CodecTests(unittest.TestCase):
 def test_streaming_rejects_zero_runs(self):
  # One zero-run of two words followed by the end marker.
  stream=struct.pack('<4H',0xc000,0x1000,0,0)
  self.assertEqual(unpack(stream,allow_zero_runs=True),bytes(4))
  with self.assertRaises(ValueError):unpack(stream)
 def test_roundtrips_without_zero_runs(self):
  samples=[bytes(8000),b'\x12\x34'*10000,
   struct.pack('<4096H',*range(4096)),
   struct.pack('<16H',*([0x1234,0x5678,0,0]*4))]
  for data in samples:
   with self.subTest(length=len(data)):self.assertEqual(unpack(pack(data)),data)
if __name__=='__main__':unittest.main()
