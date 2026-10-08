"""Owned Primal Hunt pair and mode checks; administration is native in-game chat."""
import argparse,configparser,json,os,secrets,signal,socket,subprocess,time
from pathlib import Path
from classic_windows_adapter import PrimalHuntAdapter,PH_MODES
root=Path('/srv/lan-party/servers')

def run(external_lan=False):
 assert os.geteuid()!=0,'Run as lanserver'
 adapter=PrimalHuntAdapter(root);parent=root/'classic-tests'/('pair-avp2ph-'+secrets.token_hex(5));parent.mkdir(mode=0o700)
 free=[]
 for port in range(27015,27019):
  with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
   try:s.bind(('0.0.0.0',port));free.append(port)
   except OSError:pass
 assert len(free)>=2,'Need two free approved ports';servers=[];results=[]
 def launch(mode,index,port):
  home=parent/str(index);home.mkdir(mode=0o700);levels=[x for x in adapter.maps() if adapter.map_valid(mode,x)];level=levels[min(index,len(levels)-1)]
  join='TestJoin'+secrets.token_hex(6);admin='TestAdmin'+secrets.token_hex(8);args,cwd=adapter.prepare(home,port,mode,level,8,join,admin,[],[])
  log=(home/'server.log').open('wb');p=subprocess.Popen(args,cwd=cwd,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);servers.append((p,log,port))
  deadline=time.monotonic()+45;info=None
  while p.poll() is None and time.monotonic()<deadline:
   info=adapter.query(port)
   if info and info['mapname']==Path(level).name:break
   time.sleep(1)
  assert info and info['mapname']==Path(level).name,'Inspect private log '+str(home)
  assert info['maxPlayers']==8 and info['passwordProtected'],info
  assert info['mode'].casefold()==PH_MODES[mode][3].casefold(),info
  cfg=configparser.ConfigParser(interpolation=None);cfg.read(home/'game/ServerData/lisp.txt');assert cfg['Settings']['Password']=='"'+join+'"' and cfg['Settings']['SCPassword']=='"'+admin+'"'
  result={'map':level,'mode':mode,'advertisedMode':info['mode'],'players':8,'port':port,'joinPasswordAdvertised':True,'joinAndControllerPasswordConfigured':True,'inGameAdminAuthentication':'not tested; requires a joined player'}
  if external_lan:
   ticket=parent/'external-ticket.json';ticket.write_text(json.dumps({'game':'avp2ph','port':port,'map':Path(level).name,'mode':info['mode'],'index':index}));ticket.chmod(0o600)
   print('EXTERNAL_GATE',parent,index,flush=True);ack=parent/('external-ack-'+str(index)+'.json');deadline=time.monotonic()+120
   while time.monotonic()<deadline and not ack.exists():time.sleep(1)
   assert ack.exists() and json.loads(ack.read_text())['query'],'Windows LAN query was not verified'
   result['windowsLanQuery']=True;ticket.unlink()
  print('PASS Primal Hunt',mode,level,port,flush=True);return result
 def stop(item):
  p,log,port=item
  if p.poll() is None:os.killpg(p.pid,signal.SIGTERM);p.wait(timeout=12)
  log.close()
 try:
  results.append(launch('dm',0,free[0]));results.append(launch('tdm',1,free[1]));stop(servers[0])
  assert servers[1][0].poll() is None and adapter.query(free[1]),'First stop affected second match'
  stop(servers[1]);modes=[]
  for index,mode in enumerate(['hunt','survivor','overrun','evac'],start=2):
   modes.append(launch(mode,index,free[0]));stop(servers[-1])
  result={'game':'avp2ph','instances':results,'additionalModes':modes,'independentStopVerified':True,'playerConnection':'not tested'}
  (root/'classic-tests/validated-avp2ph.json').write_text(json.dumps(result,indent=2));print('PASS independent stopping: avp2ph',flush=True)
 finally:
  for item in servers:
   if not item[1].closed:stop(item)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--external-lan',action='store_true');run(p.parse_args().external_lan)
