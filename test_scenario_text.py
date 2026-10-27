import struct,unittest
from scenario_text import patch,parse,read_words,encode,timing_commands,BASE,START,END
from lz_halfword import pack,check_stream_budget

def fixture():
 d=bytearray(333824)
 struct.pack_into('<2I',d,START,BASE+START+0x80,BASE+START+0x180)
 for table,starts,words in [
  (START+0x80,[START+0x20,START+0x40],[[11,12,0x3001],[0x200a,0x200b,0x3001]]),
  (START+0x180,[START+0x100,START+0x120],[[11,12,0x3001],[14,0x3001]])]:
  for i,(pos,w) in enumerate(zip(starts,words)):
   struct.pack_into('<I',d,table+i*4,BASE+pos)
   struct.pack_into('<'+'H'*len(w),d,pos,*w)
 struct.pack_into('<I',d,START+0x188,0xffffffff)
 struct.pack_into('<I',d,END-4,BASE+END+8)
 d[END:END+16]=bytes(range(16))
 return bytes(d)

class ScenarioTests(unittest.TestCase):
 def test_nickname_preserves_variable_and_restores_palette(self):
  words=encode(['Hi, {nickname}!'],[0x2002,0x3001])
  at=words.index(0x2002)
  self.assertEqual(words[at:at+3],[0x2002,0x3003,0])
  self.assertEqual(words[-3:],[0x3003,255,0x3001])
  with self.assertRaises(AssertionError):encode(['{nickname}'],[0x3003,0x2002,0x3001])
  with self.assertRaises(AssertionError):encode(['A'*25+'{nickname}'],[0x2002,0x3001])
 def test_timed_text_preserves_speed_commands_and_order(self):
  original=[1,0x3002,15,2,0x3002,255,3,0x3001]
  words=encode(['Go!','{speed_15}..........{speed_255}','WHAM!'],original)
  self.assertEqual(timing_commands(words),[15,255])
  self.assertEqual(words.count(0x3000),2)
  for lines in (['Go!'],['{speed_255}...{speed_15}'],['{speed_15}...{speed_255}{speed_255}'],['{speed_14}...{speed_255}']):
   with self.assertRaises(AssertionError):encode(lines,original)
 def test_repacking_preserves_untranslated_entries_and_scripts(self):
  original=fixture();groups=parse(original)
  out,report=patch(original,{'bank_entries':{'0':{'1':['Month {month} Day {day}']}}})
  for g in groups:
   for e in g['entries']:
    pos=struct.unpack_from('<I',out,g['table']+e['id']*4)[0]-BASE
    actual=read_words(out,pos)
    if g['group']==0 and e['id']==1:
     self.assertIn(0x200a,actual);self.assertIn(0x200b,actual)
    else:self.assertEqual(actual,e['words'])
  self.assertEqual(out[END-4:],original[END-4:])
  self.assertEqual(out[START+0x188:START+0x18c],b'\xff'*4)
  self.assertEqual(out[START+0x80:START+0x84],out[START+0x180:START+0x184])
  self.assertEqual(report['translated_instances'],1)
 def test_rejects_missing_variable_and_overwide_text(self):
  with self.assertRaises(AssertionError):encode(['{name}'],[0x3001])
  with self.assertRaises(AssertionError):encode(['A'*41],[0x3001])
 def test_addressed_name_keeps_its_argument(self):
  words=encode(['Hey, {addressed_name}!'],[0x2003,0,0x3001])
  at=words.index(0x2003)
  self.assertEqual(words[at:at+2],[0x2003,0])
  with self.assertRaises(AssertionError):encode(['{addressed_name}'],[0x2003,1,0x3001])
 def test_rejects_occupied_runtime_area(self):
  d=bytearray(fixture());d[0x30c00]=1
  with self.assertRaises(AssertionError):patch(d,{})
 def test_parameterized_names_localize_suffix_and_preserve_speaker(self):
  for command in range(0x2003,0x2009):
   for argument in (0,1,10,19):
    words=encode([f'Hello, {{v{command:04x}_{argument}}}!'],[command,argument,0x3001])
    at=words.index(0x2003)
    self.assertEqual(words[at:at+4],[0x2003,argument,0x3003,0])
    self.assertEqual(words[-3:],[0x3003,255,0x3001])
  with self.assertRaises(AssertionError):encode(['{v2004_19}'],[0x2004,2,0x3001])
  with self.assertRaises(AssertionError):encode(['{v2004_19}'],[0x3002,0x2004,19,0x3001])
  with self.assertRaises(AssertionError):encode(['{name}'],[0x3003,0x2001,0x3001])
  with self.assertRaises(AssertionError):encode(['A'*25+'{v2008_19}'],[0x2008,19,0x3001])
 def test_cd_budget_rejects_long_copy_and_accepts_bounded_encoding(self):
  # A literal followed by an extended copy of 30,000 words.
  bad=struct.pack('<6H',0x6000,1,1,30000,0,0)
  with self.assertRaises(ValueError):check_stream_budget(bad)
  prefix=struct.pack('<32H',*range(32))
  self.assertLessEqual(check_stream_budget(pack(prefix+b'\x01\x00'*30000)),40000)

if __name__=='__main__':unittest.main()
