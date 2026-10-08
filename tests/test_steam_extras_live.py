"""Two real isolated servers, LAN/password probes and independent stopping."""
import json,os,secrets,signal,socket,struct,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from steam_extras_adapter import BrinkAdapter,ContagionAdapter
ROOT=Path('/srv/lan-party/servers');HOST='192.168.8.138'

def source_rcon(port,password,command,host=HOST):
 with socket.create_connection((host,port),timeout=4) as s:
  def read(n):
   data=b''
   while len(data)<n:
    part=s.recv(n-len(data))
    if not part:raise OSError('RCON disconnected')
    data+=part
   return data
  def receive():
   size=struct.unpack('<i',read(4))[0]
   if not 10<=size<=1024*1024:raise ValueError('Invalid RCON response')
   data=read(size);ident,kind=struct.unpack_from('<ii',data);return ident,kind,data[8:-2].decode(errors='replace')
  def send(kind,text):
   data=struct.pack('<ii',77341,kind)+text.encode()+b'\0\0';s.sendall(struct.pack('<i',len(data))+data)
  send(3,password)
  for _ in range(4):
   ident,kind,_=receive()
   if ident==-1:raise PermissionError('RCON authentication rejected')
   if kind==2:break
  else:raise ValueError('No RCON authentication response')
  send(2,command)
  for _ in range(4):
   ident,kind,text=receive()
   if ident==77341 and kind==0:return text
  raise ValueError('No RCON command response')

def brink_rcon(port,password,command,host=HOST):
 with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
  s.settimeout(3);s.sendto(b'\xff\xffrcon\0'+password.encode()+b'\0'+command.encode()+b'\0',(host,port))
  data=s.recv(16384)
  if not data.startswith(b'\xff\xffprint\0'):raise ValueError('Invalid Brink RCON response')
  return data[8:].decode('latin1').rstrip('\0')

def run(game,external=False):
 assert os.geteuid()!=0,'Run as lanserver'
 cls=BrinkAdapter if game=='brink' else ContagionAdapter
 adapter=cls(ROOT);parent=ROOT/'extra-tests'/('pair-'+game+'-'+secrets.token_hex(5));parent.mkdir(mode=0o700,parents=True)
 owned=[];result=[]
 try:
  modes=['objective','stopwatch'] if game=='brink' else ['escape','extraction']
  for index,mode in enumerate(modes):
   port=None
   used={n for _,_,a,p in owned for n,t in a.reserved_ports(p) if t==socket.SOCK_DGRAM}
   for candidate in range(27015,27019):
    if game=='brink' and candidate+1>27018:continue
    probes=[]
    try:
     for number,kind in adapter.reserved_ports(candidate):
      if kind==socket.SOCK_DGRAM and number in used:raise OSError('Owned port busy')
      probe=socket.socket(socket.AF_INET,kind);probes.append(probe);probe.bind(('0.0.0.0',number))
     port=candidate;break
    except OSError:pass
    finally:
     for probe in probes:probe.close()
   assert port is not None,'Free approved slots unavailable'
   home=parent/str(index);home.mkdir(mode=0o700)
   join=secrets.token_hex(8);admin=secrets.token_hex(12);levels=[m for m in adapter.maps() if adapter.map_valid(mode,m)];level=levels[min(index,len(levels)-1)]
   args,cwd=adapter.prepare(home,port,mode,level,8,join,admin,[])
   log=(home/'server.log').open('wb');os.chmod(home/'server.log',0o600)
   proc=subprocess.Popen(args,cwd=cwd,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);owned.append((proc,log,adapter,port))
   deadline=time.monotonic()+100;info=None
   while time.monotonic()<deadline and proc.poll() is None:
    info=adapter.query(port)
    if info and info.get('mapname')==level:break
    time.sleep(3)
   assert info and info['mapname']==level,'Readiness failed; private log: '+str(home/'server.log')
   assert info['maxPlayers']==8 and info['passwordProtected'],info
   if game=='contagion':
    try:source_rcon(port,'WrongPassword','status');raise AssertionError('Wrong RCON accepted')
    except PermissionError:pass
    assert level in source_rcon(port,admin,'status')
    assert join in source_rcon(port,admin,'sv_password')
   else:
    assert 'bad rcon password' in brink_rcon(port,'WrongPassword','serverInfo').lower()
    assert level in brink_rcon(port,admin,'serverInfo')
    assert join in brink_rcon(port,admin,'g_password')
    rule='sdGameRulesObjective' if mode=='objective' else 'sdGameRulesStopWatch'
    assert rule in brink_rcon(port,admin,'si_rules')
   proof={'port':port,'mode':mode,'map':level,'players':8,'joinPasswordAdvertised':True,'configuredJoinPasswordVerified':True,'localRconAuthentication':True}
   if external:
    ticket=parent/'ticket.json';ticket.write_text(json.dumps({'game':game,'port':port,'map':level,'admin':admin,'join':join,'index':index}));ticket.chmod(0o600)
    print('EXTERNAL_GATE',str(parent),index,flush=True);ack=parent/('ack-'+str(index)+'.json');deadline=time.monotonic()+90
    while not ack.exists() and time.monotonic()<deadline:time.sleep(1)
    assert ack.exists(),'Windows LAN check did not arrive'
    data=json.loads(ack.read_text());assert data.get('query') and data.get('rconAuthentication') and data['map']==level
    proof.update(windowsLanQuery=True,windowsLanRconAuthentication=True);ticket.unlink()
   result.append(proof);print('PASS',game,mode,level,port,flush=True)
  first=owned[0][0];os.killpg(first.pid,signal.SIGTERM);first.wait(15)
  assert owned[1][0].poll() is None and owned[1][2].query(owned[1][3]),'Independent stop failed'
  proof={'game':game,'instances':result,'independentStopVerified':True,'playerConnection':'not tested'}
  (ROOT/'extra-tests'/('validated-'+game+'.json')).write_text(json.dumps(proof,indent=2));print('PASS independent stop',game,flush=True)
 finally:
  for proc,log,a,p in owned:
   if proc.poll() is None:
    os.killpg(proc.pid,signal.SIGTERM)
    try:proc.wait(15)
    except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
   log.close()
if __name__=='__main__':run(sys.argv[1],'--external-lan' in sys.argv)
