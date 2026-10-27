"""Regression checks for the terminal dialogue entry and dynamic player name.

The fixture is synthetic and contains no game data.
"""
import struct, unittest
from school_life import patch, BASE

def fixture():
    data=bytearray(0x35000)
    for group in (0,1):
        start=0x31100+group*0x1800
        table=start+57*64
        struct.pack_into('<I',data,0x31000+group*4,BASE+table)
        for sid in range(57):
            pos=start+sid*64
            struct.pack_into('<I',data,table+sid*4,BASE+pos)
            words=[1,0x3001]
            if sid==4:words=[v for i in range(7) for v in (1,0x61e)]+[0x3001]
            if sid==45:words=[1,0x2001,0x3003,0,1,0x3003,255,0x3001]
            struct.pack_into('<'+'H'*len(words),data,pos,*words)
    return bytes(data)

class SchoolLifeTests(unittest.TestCase):
    def test_final_entry_and_name_preserve_tables_and_surroundings(self):
        original=fixture()
        result,report=patch(original,{'dialogue':{'45':['Well done, {name}!'],'56':['Study hard!']},'choices':['A']*7,'dialogue_counts':[57,57]})
        self.assertEqual(report['dialogue_instances'],4)
        for group in (0,1):
            table=struct.unpack_from('<I',original,0x31000+group*4)[0]-BASE
            self.assertEqual(result[table:table+57*4],original[table:table+57*4])
            pos=struct.unpack_from('<I',original,table+45*4)[0]-BASE
            words=struct.unpack_from('<32H',result,pos)
            i=words.index(0x2001)
            self.assertEqual(words[i+1:i+3],(0x3003,0))
            self.assertIn(0x3001,words)
            # Untranslated page immediately before the final entry is intact.
            last=struct.unpack_from('<I',original,table+56*4)[0]-BASE
            self.assertEqual(result[last-64:last],original[last-64:last])
            if group==1:
                self.assertEqual(result[table:],original[table:])

    def test_rejects_inserting_a_name_in_an_unrelated_page(self):
        with self.assertRaisesRegex(AssertionError,'Name variable'):
            patch(fixture(),{'dialogue':{'39':['Hello, {name}!']},'choices':['A']*7})

if __name__=='__main__':unittest.main()
