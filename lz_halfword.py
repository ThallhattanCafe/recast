"""Halfword LZ compatible with SLPS-02120's streaming decoder at 0x80015eac.

The in-memory routine at 0x8001617c also supports zero runs.
The active CD streaming routine does NOT: distance zero copies stale output
memory to itself. Never emit those tokens in a disc asset.
"""
import struct,collections
def unpack(data, *, allow_zero_runs=False):
 pos=0;out=[]
 def word():
  nonlocal pos
  v=struct.unpack_from('<H',data,pos)[0];pos+=2;return v
 while len(out)<10000000:
  flags=word()
  for bit in range(15,-1,-1):
   token=word()
   if not(flags&(1<<bit)):out.append(token);continue
   count=token>>11;distance=token&2047
   if count==0:count=word()
   if distance==0:
    if count==0:return struct.pack('<'+'H'*len(out),*out)
    if not allow_zero_runs:raise ValueError('Zero-run token is unsafe for the CD streaming decoder')
    out.extend([0]*count)
   else:
    if distance>len(out):raise ValueError('Invalid backreference')
    for _ in range(count):out.append(out[-distance])
 raise ValueError('Output limit exceeded')
def pack(data, *, min_size=0):
 if len(data)%2:raise ValueError('Odd-length input')
 words=struct.unpack('<'+'H'*(len(data)//2),data);n=len(words)
 chains=collections.defaultdict(lambda:collections.deque(maxlen=128))
 tokens=[];i=0
 while i<n:
  # CD completion interrupts can overwrite the input slot while a long copy
  # is still running. Bound later copies to 8 words. The former 16-word
  # cap could still overrun the ring while loading MGT01 after April events.
  # Keep the first group
  # unchanged because the game's file table fingerprints its flag word.
  best=0;dist=0;limit=min(65535 if len(tokens)<16 else 8,n-i)
  if i+1<n:
   key=(words[i],words[i+1])
   for at in reversed(chains[key]):
    delta=i-at
    if delta>2047:break
    j=0
    while j<limit and words[at+j]==words[i+j]:j+=1
    if j>best:best=j;dist=delta
    if best==limit:break
  if best>=2:
   vals=[(best<<11)|dist] if best<=31 else [dist,best]
   tokens.append((1,vals));count=best
  else:tokens.append((0,[words[i]]));count=1
  for at in range(i,i+count):
   if at+1<n:chains[(words[at],words[at+1])].append(at)
  i+=count
 tokens.append((1,[0,0]))
 # The streaming caller keeps decoding until the directory's byte count has
 # been consumed. An early terminator followed by whole padding sectors can
 # overwrite output. Expand references to literals so EOF is in the last CD
 # sector, without adding any decompressed bytes.
 if min_size:
  token_count=len(tokens);payload_words=sum(len(v) for _,v in tokens)
  expanded=[];source_pos=0
  for token_index,(flag,vals) in enumerate(tokens):
   count=(vals[0]>>11 or vals[1]) if flag else 1
   size=2*((token_count+15)//16+payload_words)
   # The file table fingerprints the first compressed word and flag group.
   if token_index>=16 and flag and count and size<min_size:
    def size_after(take):
     rest=count-take
     new_tokens=take+int(rest>0)
     new_payload=take+(2 if rest>31 else 1 if rest else 0)
     return 2*((token_count+new_tokens-1+15)//16+payload_words+new_payload-len(vals))
    low,high=1,count
    while low<high:
     middle=(low+high)//2
     if size_after(middle)>=min_size:high=middle
     else:low=middle+1
    take=low
    part=[(0,[v]) for v in words[source_pos:source_pos+take]]
    rest=count-take;distance=vals[0]&2047
    if rest==1:part.append((0,[words[source_pos+take]]))
    elif rest:part.append((1,[(rest<<11)|distance] if rest<=31 else [distance,rest]))
    token_count+=len(part)-1;payload_words+=sum(len(v) for _,v in part)-len(vals)
    expanded.extend(part)
   else:expanded.append((flag,vals))
   source_pos+=count
  tokens=expanded
  assert 2*((token_count+15)//16+payload_words)>=min_size
 out=bytearray()
 for start in range(0,len(tokens),16):
  group=tokens[start:start+16];flags=sum(flag<<(15-k) for k,(flag,_) in enumerate(group))
  out.extend(struct.pack('<H',flags))
  for _,vals in group:out.extend(struct.pack('<'+'H'*len(vals),*vals))
 assert unpack(out)==data,'Codec failed round-trip'
 return bytes(out)

def check_stream_budget(data,max_sector_output=16000):
 """Reject streams whose sector decode work can starve the CD input ring.

 Grouped output is charged to the sector containing its flag word, matching
 the streaming decoder's group-at-a-time stopping rule. The limit is a
 conservative build invariant, backed by emulator regression runs.
 """
 pos=0;totals=collections.Counter()
 while True:
  sector=pos//2048;flags=struct.unpack_from('<H',data,pos)[0];pos+=2
  for bit in range(15,-1,-1):
   token=struct.unpack_from('<H',data,pos)[0];pos+=2;count=1
   if flags&(1<<bit):
    count=token>>11;distance=token&2047
    if not count:count=struct.unpack_from('<H',data,pos)[0];pos+=2
    if not distance and not count:return max(totals.values(),default=0)
   totals[sector]+=count*2
   if totals[sector]>max_sector_output:
    raise ValueError(f'Unsafe CD decode work in sector {sector}: {totals[sector]} bytes')
