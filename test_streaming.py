"""Regressions for the CD loader's padding and first-word validation."""
import unittest,struct
from lz_halfword import pack,unpack,check_stream_budget

class StreamingTests(unittest.TestCase):
    def test_long_repeated_tail_stays_within_cd_decode_budget(self):
        # MGT01's long compressed tail exposed a ring overwrite at the old
        # 16-word limit even though an offline round-trip still succeeded.
        data=struct.pack('<64H',*range(64))+bytes(240000)
        packed=pack(data,min_size=100002)
        self.assertEqual(unpack(packed),data)
        self.assertLessEqual(check_stream_budget(packed),16000)

    def test_expanded_stream_keeps_content_and_fingerprint(self):
        data=struct.pack('<16H',*range(16))+bytes(80000)+b'\x34\x12'*6000
        compact=pack(data)
        larger=pack(data,min_size=40002)
        self.assertEqual(unpack(larger),data)
        self.assertGreaterEqual(len(larger),40002)
        self.assertLess(len(larger),40010)
        self.assertEqual(larger[:4],compact[:4])

    def test_short_references_can_be_expanded(self):
        data=struct.pack('<32H',*range(32))+struct.pack('<512H',*([1,2,3,4,5,6,7,8]*64))
        compact=pack(data)
        larger=pack(data,min_size=802)
        self.assertEqual(unpack(larger),data)
        self.assertEqual(larger[:4],compact[:4])
        self.assertGreaterEqual(len(larger),802)

if __name__=='__main__':unittest.main()
