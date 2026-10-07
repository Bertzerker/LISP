import json,time,urllib.request,urllib.error,urllib.parse,socket,hashlib,os
URL=os.environ.get('LISP_TEST_URL','http://192.168.8.138');HOST=urllib.parse.urlparse(URL).hostname
def api(path,data=None):
 r=urllib.request.Request(URL+path,data=json.dumps(data).encode() if data is not None else None,headers={'X-LAN-Request':'1','Content-Type':'application/json'})
 with urllib.request.urlopen(r,timeout=180) as response:return json.load(response)
def login(port,password):
 with socket.create_connection((HOST,port),timeout=2) as s:
  s.sendall(hashlib.md5(password.encode()).hexdigest().encode()+b'\x64');return s.recv(1)==b'\x01'
def run():
 ids=[]
 try:
  catalog=next(g for g in api('/api/catalog')['games'] if g['id']=='swbf2')
  assert len(catalog['maps'])>=70
  for mode,level,players,join,admin in [('con','tat2g_con',8,'LispTestJoinA','LispTestAdminA'),('ctf','cor1c_ctf',12,'LispTestJoinB','LispTestAdminB')]:
   ids.append(api('/api/servers',dict(game='swbf2',mode=mode,map=level,players=players,password=join,adminPassword=admin)))
  time.sleep(25)
  servers={s['id']:s for s in api('/api/servers')['servers']}
  if any(servers[i['id']]['status']=='starting' for i in ids):
   time.sleep(20);servers={s['id']:s for s in api('/api/servers')['servers']}
  for i,mode,mapname,players,admin in [(ids[0],'con','tat2g_con',8,'LispTestAdminA'),(ids[1],'ctf','cor1c_ctf',12,'LispTestAdminB')]:
   s=servers[i['id']];assert s['status']=='running',s
   assert s['currentMap']==mapname and s['players']==players and s['passwordProtected'] and s['adminKind']=='swbf2',s
   assert login(i['port'],admin) and not login(i['port'],'WrongPassword')
  assert ids[0]['port']!=ids[1]['port']
  print('PASS two Battlefront matches: distinct ports, maps, limits, passwords and RCON authentication')
  try:api('/api/servers',dict(game='swbf2',mode='con',map='cor1c_ctf',players=8))
  except urllib.error.HTTPError as e:assert e.code==400
  else:raise AssertionError('Mismatched mode accepted')
  try:api('/api/servers',dict(game='swbf2',mode='con',map='tat2g_con',players=8,adminPassword='X'*16))
  except urllib.error.HTTPError as e:assert e.code==400
  else:raise AssertionError('Too-long password accepted')
  first=ids.pop(0);api('/api/servers/'+first['id']+'/stop',{})
  assert next(s for s in api('/api/servers')['servers'] if s['id']==ids[0]['id'])['status']=='running'
  assert login(ids[0]['port'],'LispTestAdminB')
  print('PASS independent stop and map/mode rejection')
 finally:
  for i in ids:api('/api/servers/'+i['id']+'/stop',{})
 print('PASS test cleanup')
if __name__=='__main__':run()
