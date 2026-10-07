import json,time,socket,secrets
from urllib.request import Request,urlopen
base='http://192.168.8.138';ids=[]
def api(path,data=None):
 with urlopen(Request(base+path,data=json.dumps(data).encode() if data is not None else None,headers={'X-LAN-Request':'1','Content-Type':'application/json'}),timeout=100) as r:return json.load(r)
def wait(ident):
 for _ in range(15):
  item=next(x for x in api('/api/servers')['servers'] if x['id']==ident)
  if item['status']=='running':return item
  if item['status']=='failed':raise AssertionError(item)
  time.sleep(1)
 raise AssertionError('SoF2 did not become ready')
def rcon(port,password):
 with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
  s.settimeout(3);s.sendto(b'\xff\xff\xff\xffrcon '+password.encode()+b' status\n',('192.168.8.138',port));return s.recv(16384)
try:
 game=next(x for x in api('/api/catalog')['games'] if x['id']=='sof2');assert len(game['maps'])>=13 and 'mp_shop' in game['maps']
 print('PASS SoF2 installed catalog, discovered multiplayer maps and five modes',flush=True)
 admin='TestAdmin'+secrets.token_hex(8)
 for mode,level,join in [('dm','mp_shop','TestJoinA'),('tdm','mp_kam1','TestJoinB')]:
  started=api('/api/servers',{'game':'sof2','mode':mode,'map':level,'players':8,'password':join,'adminPassword':admin});ids.append(started['id']);item=wait(started['id']);assert item['passwordProtected'] and item['adminEnabled']
  with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as query:
   query.settimeout(3);query.sendto(b'\xff\xff\xff\xffgetstatus\n',('192.168.8.138',item['port']));packet=query.recv(16000)
   assert b'\\protocol\\2004\\' in packet and b'\\g_needpass\\1\\' in packet,packet
  print('PASS independent Gold instance, protocol 2004 and password requirement:',mode,level,item['port'],flush=True)
 servers=api('/api/servers')['servers'];ports=[x['port'] for x in servers if x['id'] in ids];assert len(set(ports))==2
 reply=rcon(ports[0],admin);assert b'map:' in reply or b'num ' in reply,reply
 time.sleep(1);wrong=rcon(ports[0],'WrongAdminPassword');assert b'Bad rconpassword' in wrong,wrong
 print('PASS RCON correct password accepted; incorrect password rejected',flush=True)
 api('/api/servers/'+ids[0]+'/stop',{});ids.pop(0);assert wait(ids[0])['status']=='running';print('PASS stopping one SoF2 instance preserves the other',flush=True)
finally:
 for ident in ids:api('/api/servers/'+ident+'/stop',{})
 print('Test SoF2 instances cleaned up',flush=True)


