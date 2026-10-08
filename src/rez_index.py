"""Read LithTech v1 REZ directory entries without loading game payloads.

Format reference: https://github.com/no-lith/RezExtract (block/header layout).
"""
import struct

def entries(path):
 with path.open('rb') as f:
  f.seek(0,2);length=f.tell();f.seek(0)
  head=f.read(143)
  if len(head)!=143 or head[:2]!=b'\r\n' or head[126]!=26:raise ValueError('Not a standard LithTech REZ archive')
  version,pos,size=struct.unpack_from('<III',head,127)
  if version!=1:raise ValueError('Unsupported REZ version')
  visited=set()
  def walk(pos,size,parent='',depth=0):
   if depth>32 or (pos,size) in visited or size>16*1024*1024 or pos+size>length:raise ValueError('Invalid REZ directory')
   visited.add((pos,size));f.seek(pos);data=f.read(size);offset=0
   def string(check_name=True):
    nonlocal offset
    end=data.index(0,offset);value=data[offset:end].decode('ascii');offset=end+1
    if check_name and ('/' in value or '\\' in value or value in ('.','..')):raise ValueError('Invalid REZ entry name')
    return value
   while offset<len(data):
    kind,location,nbytes,modified=struct.unpack_from('<IIII',data,offset);offset+=16
    if kind==1:
     name=string();folder=parent+'/'+name if parent else name
     if nbytes:yield from walk(location,nbytes,folder,depth+1)
    elif kind==0:
     ident,extension,keys=struct.unpack_from('<I4sI',data,offset);offset+=12
     name=string();description=string(False);offset+=4*keys
     ext=extension.rstrip(b'\0')[::-1].decode('ascii')
     if offset>len(data) or location+nbytes>length:raise ValueError('Invalid REZ resource')
     name=name+'.'+ext if ext else name
     yield (parent+'/'+name if parent else name).lower(),location,nbytes
    else:raise ValueError('Unknown REZ entry type')
  yield from walk(pos,size)
