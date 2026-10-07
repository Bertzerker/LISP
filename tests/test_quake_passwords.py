import sys,pathlib,json,time,secrets
import zmq,uuid
from urllib.request import Request,urlopen
import os
BASE=os.environ.get('LISP_TEST_URL','http://192.168.8.138')
from urllib.parse import urlparse
HOST=urlparse(BASE).hostname
def api(path,data=None):
 return json.load(urlopen(Request(BASE+path,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json','X-LAN-Request':'1'}),timeout=180))
ids=[]
try:
 for n in range(2):
  join='Join'+secrets.token_hex(8);admin='Admin'+secrets.token_hex(8)
  x=api('/api/servers',dict(game='quakelive',mode='ffa',map='campgrounds',players=8,password=join,adminPassword=admin));ids.append(x['id'])
  for _ in range(20):
   state=next(i for i in api('/api/servers')['servers'] if i['id']==x['id'])
   if state['status']=='running':break
   assert state['status']!='failed';time.sleep(2)
  else:raise AssertionError('QL did not become ready')
  assert join not in json.dumps(state) and admin not in json.dumps(state)
  with zmq.Context() as ctx:
   with ctx.socket(zmq.DEALER) as sock:
    sock.linger=0;sock.zap_domain=b'rcon';sock.identity=uuid.uuid4().hex.encode();sock.plain_username=b'rcon';sock.plain_password=admin.encode();sock.connect(f"tcp://{HOST}:{x['port']+1000}")
    sock.send(b'register');sock.poll(500);sock.send(b'echo LISP_RCON_TEST_OK');data=b''
    deadline=time.monotonic()+8
    while time.monotonic()<deadline:
     if sock.poll(500):data+=sock.recv()
     if b'LISP_RCON_TEST_OK' in data:break
    assert b'LISP_RCON_TEST_OK' in data,'No authenticated command response: '+repr(data.replace(join.encode(),b'[hidden]').replace(admin.encode(),b'[hidden]'))
   with ctx.socket(zmq.DEALER) as bad:
    bad.linger=0;bad.plain_username=b'rcon';bad.plain_password=b'WrongTestPassword';bad.connect(f"tcp://{HOST}:{x['port']+1000}");bad.send(b'register');bad.send(b'status');assert not bad.poll(1200),'Wrong password accepted'
  print('PASS Quake Live',n+1,'LAN RCON authentication, wrong-password rejection, join-password flag and API secret exclusion',flush=True)
 api('/api/servers/'+ids[0]+'/stop',{});ids.pop(0)
 assert any(i['id']==ids[0] and i['status']=='running' for i in api('/api/servers')['servers'])
 print('PASS two Quake Live instances and stop isolation',flush=True)
finally:
 for ident in ids:api('/api/servers/'+ident+'/stop',{})
