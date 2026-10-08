"""Real paired native server checks; run as lanserver, never stops other matches."""
import argparse,json,os,secrets,shutil,signal,socket,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from classic_adapter import ClassicQuakeAdapter
from classic_windows_adapter import Wolf2009Adapter
root=Path('/srv/lan-party/servers')
def rcon(port,password,command,wolf=False):
 with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
  packet=b'\xff\xffrcon\0'+password.encode()+b'\0'+command.encode()+b'\0' if wolf else b'\xff'*4+f'rcon "{password}" {command}'.encode()
  s.settimeout(4);s.sendto(packet,('192.168.8.138',port))
  return s.recv(65535).decode('latin1')
def run(game,external_lan=False):
 assert os.geteuid()!=0,'Run as lanserver, not root'
 parent=root/'classic-tests'/('pair-'+game+'-'+secrets.token_hex(5));parent.mkdir(parents=True,mode=0o700)
 servers=[];ports=[]
 for port in range(27015,27019):
  with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
   try:s.bind(('0.0.0.0',port));ports.append(port)
   except OSError:continue
 assert len(ports)>=2,'Two free approved ports are required'
 results=[]
 try:
  wolf=game=='wolf2009'
  for index,mode in enumerate(['objective','tdm'] if wolf else ['ffa','ctf']):
   adapter=Wolf2009Adapter(root) if wolf else ClassicQuakeAdapter(root,game);levels=[m for m in adapter.maps() if adapter.map_valid(mode,m)];level=levels[min(index,len(levels)-1)]
   home=parent/str(index);home.mkdir(mode=0o700)
   join='TestJoin'+secrets.token_hex(6);admin='TestAdmin'+secrets.token_hex(8)
   args,cwd=adapter.prepare(home,ports[index],mode,level,8,join,admin,[],[])
   log=(home/'server.log').open('wb');env=os.environ.copy();env['HOME']=str(home)
   proc=subprocess.Popen(args,cwd=cwd,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
   servers.append((proc,log,adapter,ports[index]))
   deadline=time.monotonic()+75;info=None
   while time.monotonic()<deadline and proc.poll() is None:
    info=adapter.query(ports[index])
    if info and info['mapname']==level:break
    time.sleep(2)
   assert info and info['mapname']==level,'Startup failed; inspect private log '+str(home/'server.log')
   assert info['maxPlayers']==8 and info['passwordProtected'],info
   time.sleep(1)
   status='serverInfo' if wolf else 'status'
   wrong=rcon(ports[index],'IncorrectPassword',status,wolf);assert 'bad rconpassword' in wrong.lower() or 'bad rcon password' in wrong.lower(), 'Wrong RCON password not rejected'
   time.sleep(1)
   assert level in rcon(ports[index],admin,status,wolf)
   time.sleep(1)
   assert join in rcon(ports[index],admin,'g_password',wolf)
   time.sleep(1)
   assert str(adapter.rules[mode][1]) in rcon(ports[index],admin,'si_rules' if wolf else 'g_gametype',wolf)
   results.append({'map':level,'mode':mode,'players':8,'port':ports[index],'joinPasswordAdvertised':True,'configuredJoinPasswordVerified':True,'lanQuery':True,'wrongAndCorrectLanRcon':True})
   if external_lan:
    ticket=parent/'external-ticket.json'
    ticket.write_text(json.dumps({'game':game,'port':ports[index],'map':level,'admin':admin,'join':join,'index':index}));ticket.chmod(0o600)
    print('EXTERNAL_GATE',parent,index,flush=True)
    deadline=time.monotonic()+120;ack=parent/('external-ack-'+str(index)+'.json')
    while time.monotonic()<deadline and not ack.exists():time.sleep(1)
    assert ack.exists(),'External LAN checks were not completed'
    proof=json.loads(ack.read_text());assert proof['map']==level and proof['query'] and proof['rconAuthentication']
    results[-1]['windowsLanQuery']=True;results[-1]['windowsLanRconAuthentication']=True
    ticket.unlink()
   print('PASS',game,mode,level,'port',ports[index],flush=True)
  proc=servers[0][0];os.killpg(proc.pid,signal.SIGTERM);proc.wait(timeout=8)
  assert servers[1][0].poll() is None and servers[1][2].query(servers[1][3]),'Stopping the first instance affected the second'
  result={'game':game,'instances':results,'independentStopVerified':True,'playerConnection':'not tested'}
  (root/'classic-tests'/('validated-'+game+'.json')).write_text(json.dumps(result,indent=2))
  print('PASS independent stopping:',game,flush=True)
  return result
 finally:
  for proc,log,adapter,port in servers:
   if proc.poll() is None:
    os.killpg(proc.pid,signal.SIGTERM)
    try:proc.wait(timeout=8)
    except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
   log.close()
  # Private failed-test logs stay available for diagnosis; game originals are untouched.
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('game',choices=['eliteforce','jka','wolf2009']);parser.add_argument('--external-lan',action='store_true');args=parser.parse_args();run(args.game,args.external_lan)
