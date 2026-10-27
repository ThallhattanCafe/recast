import unittest,hashlib,zlib,base64,copy
from palette_patch import patch

class PaletteTests(unittest.TestCase):
    def fixture(self):
        data=b'HEAD'+bytes([0x21,0x43,0x65,0x87])+b'TAIL'
        entry=dict(label='test',text='Test',pixel_offset=4,width=4,height=2,
                   rect=[1,0,2,2],original_sha256=hashlib.sha256(bytes([2,3,6,7])).hexdigest(),
                   pixels=base64.b85encode(zlib.compress(bytes([9,10,11,12]))).decode())
        return data,{'asset':'test','patches':[entry]}
    def test_nibbles_and_surrounding_bytes_preserved(self):
        data,spec=self.fixture();result,_=patch(data,spec)
        self.assertEqual(result,b'HEAD'+bytes([0x91,0x4a,0xb5,0x8c])+b'TAIL')
    def test_wrong_original_rejected(self):
        data,spec=self.fixture()
        with self.assertRaises(AssertionError):patch(data[:4]+bytes(4)+data[8:],spec)
    def test_overlapping_pixels_rejected(self):
        data,spec=self.fixture();spec['patches'].append(copy.deepcopy(spec['patches'][0]))
        with self.assertRaises(AssertionError):patch(data,spec)
    def test_out_of_bounds_rectangle_rejected(self):
        data,spec=self.fixture();spec['patches'][0]['rect']=[3,0,2,2]
        with self.assertRaises(AssertionError):patch(data,spec)

if __name__=='__main__':unittest.main()
