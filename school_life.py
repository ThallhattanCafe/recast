"""Patch the opening scenario using paired Latin glyphs; no emulator/code changes.

The game fetches each glyph as 200 bytes from TIM pixel base + glyph_id*200.
Unused zero-filled ranges can therefore hold additional glyphs without changing
the original Japanese glyphs. Text pointers and event commands remain intact.
"""
import json, struct
from pathlib import Path

BASE = 0x800d0000
PIXELS = 384

def patch(data, spec):
    original = bytes(data)
    out = bytearray(data)
    if spec.get('runtime_pairs'):
        from latin_runtime import runtime_blob
        assert not any(original[0x30c00:0x31000]), 'Runtime code area occupied'
        out[0x30c00:0x31000]=runtime_blob()
    latin = {c:i+1 for i,c in enumerate('1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz')}
    latin.update({' ':0, '?':66, '!':74, '.':77, ',':170, "'":180, ':':86, '-':168, '(':184, ')':185})
    pairs = {}
    # Preserve the Latin/kana set and every Japanese glyph still referenced
    # by an untranslated text entry. Dead kanji slots can safely hold English.
    replaced={(g,int(s)) for g in (0,1) for s in spec['dialogue']}
    replaced.update({(0,4),(1,4)})
    replaced.update((int(g),int(s)) for g,rows in spec.get('bank_entries',{}).items() for s in rows)
    live=set(range(297))
    if spec.get('reclaim_unused_kanji'):
        for group in range(64):
            table=struct.unpack_from('<I',original,0x31000+group*4)[0]-BASE
            if not 0x31000<table<0x4a000:break
            previous=0
            for sid in range(4096):
                pos=struct.unpack_from('<I',original,table+sid*4)[0]-BASE
                if not 0x31000<pos<table or pos<=previous:break
                previous=pos
                if (group,sid) in replaced:continue
                while True:
                    code=struct.unpack_from('<H',original,pos)[0];pos+=2
                    if code==0x3001:break
                    if code<746:live.add(code)
    reclaimed=set(range(297,746))-live if spec.get('reclaim_unused_kanji') else set()
    # Font bank ends before the text at 0x31000; the second range is unused.
    slots = iter(list(range(746,1001)) + sorted(reclaimed) + list(range(1146,1513)))
    def glyph(pair):
        if spec.get('runtime_pairs'):
            assert all(c in latin for c in pair), ('Unsupported ASCII',pair)
            pairs[pair]=0x8000 | (ord(pair[0])<<7) | ord(pair[1])
            return pairs[pair]
        if pair not in pairs:
            while True:
                index = next(slots)
                pos = PIXELS + index*200
                if index in reclaimed:break
                assert not any(original[pos:pos+200]), ('Occupied font slot',index)
                if not any(out[pos:pos+200]):break
            pixels = []
            for y in range(20):
                for ch in pair:
                    src = original[PIXELS+latin[ch]*200+y*10:PIXELS+latin[ch]*200+y*10+10]
                    row = [n for byte in src for n in (byte&15,byte>>4)]
                    # Merge neighbouring source pixels to retain thin strokes.
                    pixels.extend(a or b for a,b in zip(row[::2],row[1::2]))
            packed=bytes(pixels[i] | pixels[i+1]<<4 for i in range(0,400,2))
            out[pos:pos+200]=packed
            pairs[pair]=index
        return pairs[pair]
    def encode(text):
        # The original name variable expands at runtime. Reserve the full
        # eight 20-pixel glyphs allowed by the character-creation field.
        assert len(text.replace('{name}',' '*16))<=40, ('Line exceeds dialogue width',text)
        if '{name}' in text:
            before,after=text.split('{name}')
            return encode(before)+[0x2001,0x3003,0]+encode(after)+[0x3003,255]
        text += ' '*(len(text)%2)
        return [glyph(text[i:i+2]) for i in range(0,len(text),2)]
    def read_string(pos):
        words=[]
        while True:
            v=struct.unpack_from('<H',original,pos)[0];pos+=2;words.append(v)
            if v==0x3001:return words
    translated=[]
    for group in (0,1):
        table=struct.unpack_from('<I',original,0x31000+group*4)[0]-BASE
        for sid,lines in spec['dialogue'].items():
            sid=int(sid);pos=struct.unpack_from('<I',original,table+sid*4)[0]-BASE
            old=read_string(pos)
            words=[]
            assert len(lines)<=4
            for line in lines:
                if words:words.append(0x3000)
                words.extend(encode(line))
            words.append(0x3001)
            # Alignment bytes before the next pointer are also safe capacity.
            count=spec.get('dialogue_counts',[57,57])[group]
            assert 0<=sid<count
            end=table if sid==count-1 else struct.unpack_from('<I',original,table+(sid+1)*4)[0]-BASE
            assert pos<end<=table
            if any('{name}' in line for line in lines):
                assert 0x2001 in old, 'Name variable not present in original'
            assert len(words)*2<=end-pos, ('Text too long',group,sid,len(words)*2,end-pos)
            out[pos:end]=struct.pack('<'+'H'*len(words),*words).ljust(end-pos,b'\0')
            translated.append({'group':group,'id':sid,'offset':pos,'english':lines})
        pos=struct.unpack_from('<I',original,table+4*4)[0]-BASE
        old=read_string(pos);words=[];segment=[];choice=0
        def flush():
            nonlocal choice
            if not segment:return
            new=encode(spec['choices'][choice]);choice+=1
            assert len(new)<=len(segment)
            words.extend(new+[0x61e]*(len(segment)-len(new)));segment.clear()
        for code in old:
            if code in (0x61e,0x3000,0x3001):flush();words.append(code)
            else:segment.append(code)
        assert choice==7 and len(words)==len(old)
        out[pos:pos+len(words)*2]=struct.pack('<'+'H'*len(words),*words)
    # Additional banks use absolute text pointers, so long English entries can
    # occupy checked unused space without shifting event code or file offsets.
    cursor=0x4a000
    relocated=[]
    for group,entries in spec.get('bank_entries',{}).items():
        group=int(group)
        table=struct.unpack_from('<I',original,0x31000+group*4)[0]-BASE
        for sid,lines in entries.items():
            sid=int(sid)
            pointer=table+sid*4
            oldpos=struct.unpack_from('<I',original,pointer)[0]-BASE
            assert 0x31000<oldpos<table and lines and len(lines)<=4
            words=[]
            for line in lines:
                if words:words.append(0x3000)
                words.extend(encode(line))
            words.append(0x3001)
            raw=struct.pack('<'+'H'*len(words),*words)
            cursor=(cursor-len(raw))&~3
            assert cursor>=0x380d0, 'Relocated text exceeds unused area'
            assert not any(original[cursor:cursor+len(raw)])
            assert not any(out[cursor:cursor+len(raw)]), 'Text/font collision'
            out[cursor:cursor+len(raw)]=raw
            struct.pack_into('<I',out,pointer,BASE+cursor)
            relocated.append({'group':group,'id':sid,'offset':cursor,'english':lines})
    return bytes(out), {'dialogue_instances':len(translated),'choice_instances':14,'paired_glyphs':len(pairs),'reclaimable_kanji':len(reclaimed),'entries':translated,'relocated_entries':relocated}
