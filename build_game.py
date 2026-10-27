"""Build a patched SLPS-02120 disc using a separately supplied manifest.

Python 3 standard library only. Does not modify the input image.
Sector algorithm reference: https://github.com/qeedquan/ecm/blob/master/unecm.c
"""
from pathlib import Path
import argparse,hashlib,json,struct,shutil,collections
from lz_halfword import pack,unpack,check_stream_budget

ROWS=['1234567890AB','CDEFGHIJKLMN','OPQRSTUVWXYZ','abcdefghijkl','mnopqrstuvwx','yz@#%?&()/+*']
ENC={c:r*16+k for r,row in enumerate(ROWS) for k,c in enumerate(row)}
ENC.update({' ':4095,'.':112,'!':99,'?':85,'-':113})
FORWARD=[0]*256;BACKWARD=[0]*256;EDC=[0]*256
for i in range(256):
    j=(i<<1)^ (0x11d if i&128 else 0)
    FORWARD[i]=j;BACKWARD[i^j]=i
    crc=i
    for _ in range(8):crc=(crc>>1)^(0xd8018001 if crc&1 else 0)
    EDC[i]=crc

def repair_sector(raw):
    b=bytearray(raw)
    assert len(b)==2352 and b[15]==2 and not (b[18]&32),'Expected Mode 2 Form 1'
    assert b[16:20]==b[20:24],'Inconsistent XA subheaders'
    crc=0
    for v in b[16:2072]:crc=(crc>>8)^EDC[(crc^v)&255]
    struct.pack_into('<I',b,2072,crc)
    address=b[12:16];b[12:16]=bytes(4)
    def parity(major_count,minor_count,major_mult,minor_inc,dst):
        size=major_count*minor_count
        for major in range(major_count):
            index=(major>>1)*major_mult+(major&1);a=0;c=0
            for _ in range(minor_count):
                v=b[12+index];index=(index+minor_inc)%size
                a=FORWARD[a^v];c^=v
            a=BACKWARD[FORWARD[a]^c]
            b[dst+major]=a;b[dst+major+major_count]=a^c
    parity(86,24,2,86,2076);parity(52,43,86,88,2248)
    b[12:16]=address
    return bytes(b)

def digest(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def build(source,destination,manifest_path):
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    source=source.resolve();destination=destination.resolve()
    target=destination/(manifest['output_name']+'.bin')
    if source==target:raise ValueError('Input and output must be different')
    if source.stat().st_size!=manifest['source_size'] or digest(source)!=manifest['source_sha256']:
        raise ValueError('Source image does not match the verified Japanese disc')
    # Read, verify, and stage every change before creating an output.
    sectors={};original_sectors={};ranges=[]
    with source.open('rb') as f:
        def readfile(lba,size):
            data=bytearray()
            for k in range((size+2047)//2048):
                f.seek((lba+k)*2352+24);data.extend(f.read(2048))
            return bytes(data[:size])
        def stage(base_lba,off,expected,new,label):
            assert len(new)==len(expected)
            ranges.append((base_lba*2048+off,base_lba*2048+off+len(expected),label))
            for i,(old,value) in enumerate(zip(expected,new)):
                lba=base_lba+(off+i)//2048;pos=24+(off+i)%2048
                if lba not in sectors:
                    f.seek(lba*2352);original=f.read(2352)
                    if repair_sector(original)!=original:
                        raise ValueError(f'Original sector {lba} fails EDC/ECC round-trip')
                    sectors[lba]=bytearray(original);original_sectors[lba]=original
                if original_sectors[lba][pos]!=old:
                    raise ValueError(f'Unexpected bytes: {label} at {off+i:#x}')
                sectors[lba][pos]=value
        def replacement(entry):
            capacity=entry['capacity'];text=entry['english']
            if len(text)>capacity:raise ValueError(f'Text too long: {text}')
            encoded=[ENC[c] for c in text]+[4095]*(capacity-len(text))
            return struct.pack('<H',capacity)+struct.pack('<'+'H'*capacity,*encoded)
        for entry in manifest['translations']:
            off=entry['offset'];new=replacement(entry)
            expected=bytes.fromhex(entry['original_hex'])
            # The character count remains unchanged; unused positions use the
            # renderer's explicit 0x0fff blank glyph. No pointers are relocated.
            stage(entry['lba'],off,expected,new,entry['file'])
        for entry in manifest.get('binary_patches',[]):
            stage(entry['lba'],entry['offset'],bytes.fromhex(entry['original_hex']),bytes.fromhex(entry['new_hex']),entry['file'])
        compressed_sizes={}
        school_reports=[]
        graphic_reports=[]
        for asset in manifest.get('graphic_assets',[]):
            from palette_patch import patch
            original=readfile(asset['lba'],asset['size'])
            spec=json.loads(manifest_path.with_name(asset['spec']).read_text(encoding='utf-8'))
            expanded,graphic_report=patch(unpack(original),spec)
            compressed=pack(expanded,min_size=((asset['size']-1)//2048)*2048+2)
            assert unpack(compressed)==expanded
            check_stream_budget(compressed)
            assert compressed[:4]==original[:4], 'Compressed file fingerprint changed'
            if len(compressed)>asset['size']:raise ValueError('Graphics asset exceeds allocation')
            compressed_sizes[asset['file']]={'stream':len(compressed),'allocation':asset['size']}
            stage(asset['lba'],0,original,compressed.ljust(asset['size'],b'\0'),asset['file'])
            graphic_reports.append(graphic_report)
        for asset in manifest.get('school_life_assets',[]):
            if asset.get('module')=='scenario_text':
                from scenario_text import patch
            else:
                from school_life import patch
            original=readfile(asset['lba'],asset['size'])
            spec=json.loads(manifest_path.with_name(asset['spec']).read_text(encoding='utf-8'))
            expanded,school_report=patch(unpack(original),spec)
            compressed=pack(expanded,min_size=((asset['size']-1)//2048)*2048+2)
            assert unpack(compressed)==expanded
            check_stream_budget(compressed)
            assert compressed[:4]==original[:4], 'Compressed file fingerprint changed'
            if len(compressed)>asset['size']:raise ValueError('School-life asset exceeds allocation')
            compressed_sizes[asset['file']]={'stream':len(compressed),'allocation':asset['size']}
            stage(asset['lba'],0,original,compressed.ljust(asset['size'],b'\0'),asset['file'])
            school_reports.append(school_report)
        for overlay in manifest.get('compressed_overlays',[]):
            original=readfile(overlay['lba'],overlay['size'])
            expanded=bytearray(unpack(original))
            for entry in manifest['translations']:
                if entry['file']!=overlay['uncompressed_file']:continue
                off=entry['offset'];expected=bytes.fromhex(entry['original_hex'])
                assert expanded[off:off+len(expected)]==expected,'Compressed overlay text mismatch'
                expanded[off:off+len(expected)]=replacement(entry)
            compressed=pack(expanded,min_size=((overlay['size']-1)//2048)*2048+2)
            assert unpack(compressed)==expanded
            check_stream_budget(compressed)
            assert compressed[:4]==original[:4], 'Compressed file fingerprint changed'
            if len(compressed)>overlay['size']:raise ValueError('Compressed overlay exceeds original allocation')
            compressed_sizes[overlay['file']]={'stream':len(compressed),'allocation':overlay['size']}
            stage(overlay['lba'],0,original,compressed.ljust(overlay['size'],b'\0'),overlay['file'])
    ordered=sorted(ranges)
    for previous,current in zip(ordered,ordered[1:]):
        if previous[1]>current[0]:raise ValueError(f'Overlapping translation entries: {previous[2]}, {current[2]}')
    changed={lba:repair_sector(raw) for lba,raw in sectors.items() if raw!=original_sectors[lba]}
    destination.mkdir(parents=True,exist_ok=True)
    if target.exists():raise FileExistsError(f'Refusing to overwrite: {target}')
    shutil.copyfile(source,target)
    with target.open('r+b') as f:
        for lba,raw in changed.items():f.seek(lba*2352);f.write(raw)
    cue=target.with_suffix('.cue')
    cue.write_text(f'FILE "{target.name}" BINARY\n  TRACK 01 MODE2/2352\n    INDEX 01 00:00:00\n',encoding='ascii')
    # Compare the entire images: all differences must be confined to the exact
    # staged sectors, and each staged sector must match the expected rebuild.
    with source.open('rb') as a,target.open('rb') as b:
        lba=0
        while True:
            old=a.read(2352);new=b.read(2352)
            if not old:assert not new;break
            assert new==changed.get(lba,old),f'Unexpected modification at sector {lba}'
            lba+=1
    report={'version':manifest['version'],'source_sha256':manifest['source_sha256'],'output_sha256':digest(target),
            'translated_string_instances':len(manifest['translations']),'modified_files':sorted(set(e['file'] for e in manifest['translations'])|set(compressed_sizes)|set(e['file'] for e in manifest.get('binary_patches',[]))),
            'compressed_overlay_roundtrip':'passed','compressed_overlay_sizes':compressed_sizes,
            'modified_sectors':sorted(changed),'source_sector_edc_ecc_roundtrip':'passed',
            'full_disc_comparison':'passed','school_life':school_reports,'graphics':graphic_reports,'emulator_testing':'See README.txt; binary checks alone do not prove gameplay compatibility.'}
    (destination/'build-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2));return target

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path);parser.add_argument('--output-dir',type=Path,default=Path('build'))
    parser.add_argument('--manifest',type=Path,required=True,help='Local manifest; translation data is not bundled with Recast')
    args=parser.parse_args();build(args.source,args.output_dir,args.manifest)
