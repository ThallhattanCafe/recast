"""MIPS-I text-upload extension for two ASCII characters per original tile.

The old Japanese path is retained. A high-bit text word carries two 7-bit
ASCII characters; the helper downsamples their existing glyphs into a tile.
DrawSync completes the previous upload before the scratch tile is reused.
"""
import struct
CODE=0x80100c00
TABLE=0x80100e00
BUFFER=0x80100f00
HOOK=0x800af8ec
RESUME=0x800af910
REG={'zero':0,'v0':2,'v1':3,'a0':4,'a1':5,'a2':6,'a3':7,
     **{f't{i}':8+i for i in range(8)},'s0':16,'s4':20,'t8':24,'t9':25,'sp':29,'ra':31}
class Assembler:
    def __init__(self,base):self.base=base;self.words=[];self.labels={};self.fix=[]
    def label(self,name):self.labels[name]=self.base+len(self.words)*4
    def emit(self,word):self.words.append(word)
    def i(self,op,rt,rs,imm):self.emit((op<<26)|(REG[rs]<<21)|(REG[rt]<<16)|(imm&65535))
    def r(self,fn,rd,rs,rt,sh=0):self.emit((REG[rs]<<21)|(REG[rt]<<16)|(REG[rd]<<11)|(sh<<6)|fn)
    def shift(self,fn,rd,rt,n):self.r(fn,rd,'zero',rt,n)
    def branch(self,op,rs,rt,label):self.fix.append((len(self.words),op,rs,rt,label));self.emit(0)
    def jump(self,target,link=False):self.emit(((3 if link else 2)<<26)|((target>>2)&0x3ffffff))
    def nop(self):self.emit(0)
    def finish(self):
        for i,op,rs,rt,label in self.fix:
            delta=(self.labels[label]-(self.base+i*4+4))//4
            assert -32768<=delta<32768
            self.words[i]=(op<<26)|(REG[rs]<<21)|(REG[rt]<<16)|(delta&65535)
        return struct.pack('<'+'I'*len(self.words),*self.words)

def hook():
    a=Assembler(HOOK)
    a.i(12,'v1','a2',0x8000)
    a.branch(4,'v1','zero','normal');a.i(9,'a1','s0',12)
    a.jump(CODE);a.nop()
    a.label('normal');a.i(9,'v0','zero',200)
    a.r(25,'zero','a2','v0');a.r(18,'v0','zero','zero')
    a.r(33,'a1','a1','v0')
    assert a.base+len(a.words)*4==RESUME
    a.i(15,'v1','zero',0x801f);a.i(35,'v1','v1',0x6360)
    a.i(43,'a1','sp',0x58);a.i(35,'v0','v1',0x1c)
    a.i(43,'s4','sp',0x54);a.r(9,'ra','v0','zero')
    a.r(33,'a0','s4','zero')
    result=a.finish();assert len(result)==64
    return result

def runtime_blob():
    a=Assembler(CODE)
    a.i(9,'sp','sp',-32);a.i(43,'ra','sp',24);a.i(43,'a2','sp',16)
    a.jump(0x80062384,True);a.r(33,'a0','zero','zero')
    a.i(35,'a3','sp',16);a.i(35,'ra','sp',24);a.i(9,'sp','sp',32)
    a.i(9,'t9','zero',0)
    a.shift(2,'a0','a3',7)
    a.label('character');a.i(12,'a0','a0',127)
    a.shift(0,'a0','a0',1)
    a.i(15,'v1','zero',TABLE>>16);a.i(13,'v1','v1',TABLE&65535)
    a.r(33,'a0','a0','v1');a.i(37,'a0','a0',0)
    a.i(9,'v0','zero',200);a.r(25,'zero','a0','v0');a.r(18,'t0','zero','zero')
    a.r(33,'t0','t0','s0');a.i(9,'t0','t0',12)
    a.i(15,'t1','zero',BUFFER>>16);a.i(13,'t1','t1',BUFFER&65535)
    a.r(33,'t1','t1','t9');a.i(9,'t2','zero',20)
    a.label('row');a.i(9,'t3','zero',5)
    a.label('pixel');a.i(36,'t4','t0',0);a.i(36,'t5','t0',1)
    a.i(12,'t6','t4',15);a.branch(5,'t6','zero','first');a.shift(2,'t8','t4',4)
    a.r(33,'t6','t8','zero')
    a.label('first');a.i(12,'t7','t5',15)
    a.branch(5,'t7','zero','second');a.shift(2,'t8','t5',4)
    a.r(33,'t7','t8','zero')
    a.label('second');a.shift(0,'t7','t7',4);a.r(37,'t6','t6','t7')
    a.i(40,'t6','t1',0);a.i(9,'t0','t0',2);a.i(9,'t3','t3',-1)
    a.branch(5,'t3','zero','pixel');a.i(9,'t1','t1',1)
    a.i(9,'t2','t2',-1);a.branch(5,'t2','zero','row');a.i(9,'t1','t1',5)
    a.branch(5,'t9','zero','done');a.i(9,'t9','zero',5)
    a.jump(a.labels['character']);a.r(33,'a0','a3','zero')
    a.label('done');a.i(15,'a1','zero',BUFFER>>16)
    a.jump(RESUME);a.i(13,'a1','a1',BUFFER&65535)
    code=a.finish();assert len(code)<=512
    blob=bytearray(1024);blob[:len(code)]=code
    latin={c:i+1 for i,c in enumerate('1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz')}
    latin.update({' ':0,'?':66,'!':74,'.':77,',':170,"'":180,':':86,'-':168,'(':184,')':185})
    for c,glyph in latin.items():struct.pack_into('<H',blob,512+ord(c)*2,glyph)
    return bytes(blob)
