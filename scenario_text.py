"""Repack scenario strings without moving pointer tables, fonts or event code."""
import struct,re
from latin_runtime import runtime_blob
BASE=0x800d0000
START=0x31000
END=0x4a000
LATIN=set('1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz ?!.,\':-()')
VARIABLES={'family':0x2000,'name':0x2001,'nickname':0x2002,'month':0x200a,'day':0x200b}

def timing_commands(words):
    result=[];i=0
    while i<len(words):
        v=words[i];i+=1
        if v in (0x3002,0x3003) or 0x2003<=v<=0x2008:
            assert i<len(words),'Missing command argument'
            if v==0x3002:result.append(words[i])
            i+=1
    return result

def source_variables(words):
    """Walk commands so an argument can never masquerade as a variable."""
    found=[];i=0
    while i<len(words):
        v=words[i];i+=1
        if v in (0x3002,0x3003) or 0x2003<=v<=0x2008:
            assert i<len(words),'Missing command argument'
            if 0x2003<=v<=0x2008:found.append((v,words[i]))
            i+=1
        elif v in VARIABLES.values():found.append((v,))
    return found

def read_words(data,pos):
    words=[]
    while pos<END:
        v=struct.unpack_from('<H',data,pos)[0];pos+=2;words.append(v)
        if v==0x3001:return words
    raise ValueError('Unterminated text')

def parse(data, allow_sparse_gender=False):
    tables=[]
    for p in range(START,START+256,4):
        t=struct.unpack_from('<I',data,p)[0]-BASE
        # Gedo is male-only: slot 1 is null, but common banks follow it.
        # Accept only this observed hole, and keep original bank numbers.
        if allow_sparse_gender and p==START+4 and t==-BASE:
            following=struct.unpack_from('<I',data,p+4)[0]-BASE
            if START<following<END:continue
        if not START<t<END:break
        tables.append(((p-START)//4,t))
    result=[]
    for g,t in tables:
        starts=[]
        for p in range(t,END,4):
            x=struct.unpack_from('<I',data,p)[0]-BASE
            if not START<x<t or (starts and x<=starts[-1]):break
            starts.append(x)
        assert starts
        result.append({'group':g,'table':t,'entries':[
            {'id':i,'offset':a,'end':b,'words':read_words(data,a)}
            for i,(a,b) in enumerate(zip(starts,starts[1:]+[t]))]})
    return result

def encode(lines,original):
    assert 1<=len(lines)<=4
    variables=source_variables(original)
    result=[]
    for line in lines:
        visible=re.sub(r'\{speed_\d+\}','',line)
        width=len(re.sub(r'\{(?:month|day)\}',' '*4,re.sub(r'\{(?:name|family|nickname|addressed_name|v200[3-8]_\d+)\}',' '*16,visible)))
        assert width<=40,('Line too wide',line)
        if result:result.append(0x3000)
        date=('{month}' in line or '{day}' in line)
        name=False
        if date:result.extend([0x3003,1])
        for segment in re.split(r'(\{\w+\})',line):
            if segment.startswith('{'):
                # These native tables are indexed by glyph, not by packed Latin pair.
                # Keep their cell count/order and the debug date-grid cursor spacing.
                if segment=='{native_date_alphabet}':
                    assert lines==[segment] and len(original)==14
                    assert original[:10]==[10,1,2,3,4,5,6,7,8,9]
                    assert original[12:]==[1566,0x3001]
                    result.extend(original[:10]+[23,14,1566]) # M, D, space
                    continue
                if segment=='{native_date_labels}':
                    assert lines==[segment] and len(original)==7
                    assert [original[i] for i in [0,1,3,4,6]]==[1566,1566,1566,1566,0x3001]
                    result.extend([1566,1566,23,1566,1566,14])
                    continue
                native=re.fullmatch(r'\{source_line_([123])\}',segment)
                if native:
                    source_lines=[[]]
                    for word in original[:-1]:
                        if word==0x3000:source_lines.append([])
                        else:source_lines[-1].append(word)
                    n=int(native[1]);assert n<len(source_lines)
                    row=source_lines[n]
                    assert row and all(word==1566 or 1<=word<=10 for word in row), 'Only original numeric grid rows may be reused'
                    result.extend(row)
                    continue
                speed=re.fullmatch(r'\{speed_(\d+)\}',segment)
                if speed:
                    value=int(speed[1])
                    assert value in timing_commands(original),('Timing command absent',segment)
                    result.extend([0x3002,value]);continue
                dynamic=re.fullmatch(r'\{v(200[3-8])_(\d+)\}',segment)
                if segment=='{addressed_name}' or dynamic:
                    pair=(int(dynamic[1],16),int(dynamic[2])) if dynamic else (0x2003,0)
                    assert pair in variables,('Addressed-name variable absent',segment)
                    # All six commands use the same speaker-indexed friendship
                    # thresholds for family/given/nickname selection. 2004..8
                    # additionally append Japanese honorifics. English dialogue
                    # uses the same chosen name without those suffixes.
                    result.extend([0x2003,pair[1],0x3003,0]);name=True;continue
                var=VARIABLES[segment[1:-1]]
                assert (var,) in variables,('Variable absent from source',segment)
                result.append(var)
                # Name drawing changes the active palette in the original.
                if var in (0x2000,0x2001,0x2002):result.extend([0x3003,0]);name=True
            else:
                assert set(segment)<=LATIN,('Unsupported characters',segment)
                segment+=' '*(len(segment)%2)
                result.extend(0x8000|(ord(segment[i])<<7)|ord(segment[i+1]) for i in range(0,len(segment),2))
        if date or name:result.extend([0x3003,255])
    result.append(0x3001)
    assert timing_commands(result)==timing_commands(original),'Timing command order/count changed'
    return result

def patch(data,spec):
    original=bytes(data);out=bytearray(original);groups=parse(original, allow_sparse_gender=spec.get('allow_sparse_gender',False))
    prepared=original;legacy_report=None
    if 'opening' in spec:
        from school_life import patch as opening_patch
        prepared,legacy_report=opening_patch(original,spec['opening'])
    assert not any(original[0x30c00:START]),'Runtime region occupied'
    out[0x30c00:START]=runtime_blob()
    # Only reclaim positively identified string allocations and the zero tail.
    spans=[];entries=[];translated=[]
    for g in groups:
        for e in g['entries']:
            spans.append((e['offset'],e['end']))
            lines=spec.get('bank_entries',{}).get(str(g['group']),{}).get(str(e['id']))
            previous=struct.unpack_from('<I',prepared,g['table']+e['id']*4)[0]-BASE
            words=encode(lines,e['words']) if lines is not None else read_words(prepared,previous)
            raw=struct.pack('<'+'H'*len(words),*words)
            entries.append((g['table']+e['id']*4,raw))
            if lines is not None:translated.append({'group':g['group'],'id':e['id'],'english':lines})
    tail=max(g['table']+len(g['entries'])*4 for g in groups)
    # Some scenarios have a 0xffffffff sentinel and an event pointer just
    # before 0x4a000. Preserve both, and reclaim only their intervening zeros.
    tail=(tail+7)&~3
    free_end=next((p for p in range(tail,END) if original[p]),END)&~3
    if free_end>tail:spans.append((tail,free_end))
    merged=[]
    for a,b in sorted(spans):
        if merged and merged[-1][1]==a:merged[-1]=(merged[-1][0],b)
        else:merged.append((a,b))
    for a,b in merged:out[a:b]=bytes(b-a)
    free=list(merged);locations={}
    for raw in sorted({raw for _,raw in entries},key=lambda x:(-len(x),x)):
        size=(len(raw)+3)&~3
        choices=[(b-a,i) for i,(a,b) in enumerate(free) if b-a>=size]
        if not choices:raise ValueError(f'Text allocation full; need {size} bytes')
        _,i=min(choices);a,b=free[i];locations[raw]=a
        out[a:a+len(raw)]=raw;free[i]=(a+size,b)
    for pointer,raw in entries:struct.pack_into('<I',out,pointer,BASE+locations[raw])
    # Read back every pointer, including untranslated strings, and preserve scripts.
    for pointer,raw in entries:
        pos=struct.unpack_from('<I',out,pointer)[0]-BASE
        assert bytes(out[pos:pos+len(raw)])==raw
    assert out[END:]==original[END:]
    assert out[START:START+(max(g['group'] for g in groups)+1)*4]==original[START:START+(max(g['group'] for g in groups)+1)*4]
    return bytes(out),{'translated_instances':len(translated),'entries':translated,'opening':legacy_report,
                       'unique_strings':len(locations),'free_text_bytes':sum(b-a for a,b in free)}
