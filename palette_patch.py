"""Apply checked four-bit indexed texture rectangles, without image libraries."""
import hashlib,zlib,base64
def patch(data,spec):
 out=bytearray(data);touched=set()
 for e in spec['patches']:
  x,y,w,h=e['rect'];stride=e['width'];offset=e['pixel_offset']
  assert x>=0 and y>=0 and x+w<=stride and y+h<=e['height']
  indices=[(y+yy)*stride+x+xx for yy in range(h) for xx in range(w)]
  old=bytes((data[offset+i//2]>>(4*(i%2)))&15 for i in indices)
  assert hashlib.sha256(old).hexdigest()==e['original_sha256'],e['label']
  new=zlib.decompress(base64.b85decode(e['pixels']))
  assert len(new)==w*h and all(v<16 for v in new)
  for i,v in zip(indices,new):
   key=(offset+i//2,i%2);assert key not in touched,'Overlapping texture rectangles';touched.add(key)
   p=offset+i//2;shift=4*(i%2);out[p]=(out[p]&~(15<<shift))|(v<<shift)
 return bytes(out),{'asset':spec['asset'],'rectangles':len(spec['patches']),'labels':[e['text'] for e in spec['patches'] if e['text']]}
