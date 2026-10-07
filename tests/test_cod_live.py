#!/usr/bin/python3
"""Two isolated owned CoD engine tests on free LAN ports; run as lanserver.

Uses source adapter directly and never stops a portal/player match. These are
engine tests; portal account ownership remains covered by test_accounts_live.py.
"""
import argparse,json,os,secrets,signal,socket,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from cod_adapter import CodAdapter
p=argparse.ArgumentParser();p.add_argument('game',choices=['iw4x','iw5','t4','t5','t6']);p.add_argument('--root',default='/srv/lan-party/servers');p.add_argument('--lan-probe-window',type=int,default=0);p.add_argument('--query-client');a=p.parse_args()
root=Path(a.root);adapter=CodAdapter(root,a.game);ports=[]
reserved=set()
for port in range(27015,27019):
 candidates=adapter.reserved_ports(port)
 if any(number>27018 or number in reserved for number,kind in candidates):continue
 sockets=[]
 try:
  for number,kind in candidates:
   s=socket.socket(socket.AF_INET,kind);sockets.append(s);s.bind(('0.0.0.0',number))
  ports.append(port);reserved.update(number for number,kind in candidates)
 except OSError:pass
 finally:
  for s in sockets:s.close()
if len(ports)<2:raise SystemExit('Two free slots are required. Player matches were left alone.')
owned=[];result={'game':a.game,'instances':[]}
def stop(item):
 process=item['process']
 if process.poll() is None:
  os.killpg(process.pid,signal.SIGTERM)
  try:process.wait(timeout=12)
  except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=5)
def rcon(port,password,command):
 with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
  s.settimeout(2);s.sendto(b'\xff\xff\xff\xffrcon '+password.encode()+b' '+command.encode(),('127.0.0.1',port))
  try:return s.recv(32768).decode('latin1','replace')
  except socket.timeout:return ''
try:
 maps=adapter.maps();assert maps,'No installed multiplayer maps'
 for index,port in enumerate(ports[:2]):
  mode='tdm' if index==0 else 'dm';level=maps[index%len(maps)]
  home=root/'cod-tests'/('pair-'+a.game+'-'+secrets.token_hex(4));home.mkdir(parents=True,mode=0o700)
  join=secrets.token_hex(8);admin=secrets.token_hex(8)
  args,cwd=adapter.prepare(home,port,mode,level,8,join,admin,[],query_clients=[a.query_client] if a.query_client else [])
  log=(home/'server.log').open('wb');process=subprocess.Popen(args,cwd=cwd,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  owned.append(dict(home=home,port=port,mode=mode,map=level,process=process,log=log,admin=admin))
 deadline=time.monotonic()+120
 while time.monotonic()<deadline:
  ready=[adapter.query(x['port']) for x in owned]
  if all(q and q.get('mapname')==x['map'] for x,q in zip(owned,ready)):break
  if any(x['process'].poll() is not None for x in owned):break
  time.sleep(4)
 for item in owned:
  q=adapter.query(item['port']);assert q and q['mapname']==item['map'],f"Instance not ready: {item['home']}"
  assert q.get('maxPlayers')==8,(q,'Player limit not honored')
  assert q.get('gametype')==item['mode'],(q,'Mode not honored')
  assert q.get('passwordProtected'),(q,'Join password not advertised')
  wrong=rcon(item['port'],'wrong-owned-test-password','status');time.sleep(.7);good=rcon(item['port'],item['admin'],'status')
  assert good and item['map'] in good and item['map'] not in wrong,'RCON authentication needs investigation'
  result['instances'].append({'port':item['port'],'mode':item['mode'],'map':item['map'],'query':q,'rconVerified':True,'home':str(item['home'])})
 if a.lan_probe_window:
  # This private SSH handoff is consumed by run_cod_pair.py without printing
  # its generated test passwords. It enables real LAN RCON verification.
  print('READY '+json.dumps({'instances':[{'port':item['port'],'map':item['map'],'admin':item['admin']} for item in owned]}),flush=True)
  time.sleep(min(30,max(0,a.lan_probe_window)))
 stop(owned[0]);time.sleep(2)
 assert adapter.query(owned[1]['port']),'Stopping the first match affected the second'
 stop(owned[1]);result['independentStopVerified']=True
 (root/'cod-tests'/('validated-'+a.game+'.json')).write_text(json.dumps(result,indent=2)+'\n')
 print('PASS '+json.dumps(result),flush=True)
finally:
 for item in owned:stop(item);item['log'].close()
 # Test logs are retained privately for diagnosis. No installed marker is set.
