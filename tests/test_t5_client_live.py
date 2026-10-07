#!/usr/bin/python3
"""Owned T5 client join attempt against an isolated server; no player stops."""
import argparse,json,os,re,secrets,signal,socket,subprocess,time,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from cod_adapter import CodAdapter
p=argparse.ArgumentParser();p.add_argument('--root',default='/srv/lan-party/servers');p.add_argument('--address',default='192.168.8.138');a=p.parse_args()
root=Path(a.root);adapter=CodAdapter(root,'t5')
# Client and server each use a game/QoS pair inside the approved slots.
for port in range(27015,27019):
 with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
  try:sock.bind(('0.0.0.0',port))
  except OSError:raise SystemExit('Approved slots occupied; no player matches touched.')
owned=[];parent=root/'cod-tests'/('t5-client-'+secrets.token_hex(4));parent.mkdir(mode=0o700)
result={'game':'t5','home':str(parent),'address':a.address+':27015','clientLocation':'same Linux host, LAN address','joined':False}
def stop(process):
 if process.poll() is None:
  os.killpg(process.pid,signal.SIGTERM)
  try:process.wait(timeout=12)
  except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=5)
def launch(home):
 runner=str(Path(__file__).resolve().parents[1]/'src/run_cod.py')
 if not Path(runner).is_file():runner='/opt/lan-portal/run_cod.py'
 if home.name=='client':
  code=Path(runner).read_text().replace("'/usr/bin/xvfb-run','-a',job['wine']","'/usr/bin/xvfb-run','-a','-s','-screen 0 1280x720x24',job['wine']")
  runner=str(home/'client-runner.py');Path(runner).write_text(code)
 console=home/'plutonium/storage/t5/main/console_mp.log'
 if console.exists():console.unlink()
 log=(home/'process.log').open('wb');process=subprocess.Popen(['/usr/bin/python3',runner,str(home)],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 owned.append((process,log));return process
def client_display():
 target=b'WINEPREFIX='+str(client/'wine').encode()
 for p in Path('/proc').glob('[0-9]*'):
  try:
   env=(p/'environ').read_bytes().split(b'\0')
   fields={x.split(b'=',1)[0].decode():x.split(b'=',1)[1].decode() for x in env if b'=' in x}
  except (OSError,UnicodeError):continue
  if target in env and fields.get('DISPLAY'):return fields
 return None

def capture(label):
 fields=client_display()
 if not fields:return False
 env={**os.environ,'DISPLAY':fields['DISPLAY'],'XAUTHORITY':fields.get('XAUTHORITY','')}
 return subprocess.run(['/usr/bin/import','-window','root',str(client/(label+'.png'))],env=env,timeout=12,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0

def select_class():
 # Send Return only to this test's private Xvfb display; no desktop is accessed.
 import ctypes,ctypes.util
 fields=client_display()
 if not fields:return False
 os.environ['XAUTHORITY']=fields.get('XAUTHORITY','')
 x=ctypes.CDLL(ctypes.util.find_library('X11'));t=ctypes.CDLL(ctypes.util.find_library('Xtst'))
 x.XOpenDisplay.argtypes=[ctypes.c_char_p];x.XOpenDisplay.restype=ctypes.c_void_p
 x.XKeysymToKeycode.argtypes=[ctypes.c_void_p,ctypes.c_ulong];x.XKeysymToKeycode.restype=ctypes.c_uint
 x.XFlush.argtypes=[ctypes.c_void_p];x.XCloseDisplay.argtypes=[ctypes.c_void_p]
 t.XTestFakeKeyEvent.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_int,ctypes.c_ulong]
 display=x.XOpenDisplay(fields['DISPLAY'].encode())
 if not display:return False
 try:
  key=x.XKeysymToKeycode(display,0xff0d);t.XTestFakeKeyEvent(display,key,1,0);t.XTestFakeKeyEvent(display,key,0,0);x.XFlush(display)
 finally:x.XCloseDisplay(display)
 return True


try:
 join=secrets.token_hex(8);admin=secrets.token_hex(8);level=adapter.maps()[0]
 server=parent/'server';server.mkdir(mode=0o700);adapter.prepare(server,27015,'tdm',level,8,join,admin,[])
 # Prepared production timeout plus test-only 600-second inactivity limit for this slow client.
 cfg=server/'plutonium/storage/t5/lisp.cfg';cfg.write_text(cfg.read_text()+'set sv_connectTimeout "180"\nset g_inactivity "600"\n')
 sp=launch(server)
 deadline=time.monotonic()+120
 while time.monotonic()<deadline:
  q=adapter.query(27015)
  if q and q['mapname']==level:break
  if sp.poll() is not None:break
  time.sleep(4)
 assert q and q['mapname']==level,'Owned server did not become ready'
 print('SERVER_READY '+json.dumps(q),flush=True)
 client=parent/'client';client.mkdir(mode=0o700);adapter.prepare(client,27017,'tdm',level,8,'','',[])
 job=json.loads((client/'cod-launch.json').read_text());job['args']=['t5mp','Z:'+str(client/'game').replace('/','\\'),'-lan','-name','LISPJoinTest','+set','net_ip','0.0.0.0','+set','net_port','27017','+set','r_fullscreen','0','+set','r_mode','1280x720','+set','r_vsync','0','+set','com_maxfps','30','+set','snd_enable','0','+set','logfile','2','+set','password',join,'+connect',a.address+':27015']
 os.environ['LIBGL_ALWAYS_SOFTWARE']='1';password_index=job['args'].index('password')+1
 job['args'][password_index]=secrets.token_hex(20);(client/'cod-launch.json').write_text(json.dumps(job));bad=launch(client);deadline=time.monotonic()+60;result['wrongJoinPasswordRejected']=False
 while time.monotonic()<deadline:
  text=(client/'process.log').read_text(errors='replace').lower()
  if any(k in text for k in ['exe_invalidpassword','invalid password','incorrect password','wrong password','ungültiges passwort']):result['wrongJoinPasswordRejected']=True;break
  if bad.poll() is not None:break
  time.sleep(3)
 capture('wrong-password-display');result['wrongPasswordServerQuery']=adapter.query(27015);stop(bad);owned[-1][1].close()
 job['args'][password_index]=join;(client/'cod-launch.json').write_text(json.dumps(job));cp=launch(client)
 deadline=time.monotonic()+260;stable=0;class_selected=False;loaded_at=None
 while time.monotonic()<deadline:
  q=adapter.query(27015)
  server_text=(server/'process.log').read_text(errors='replace')
  if q and q.get('clients',0)>0:result['handshakeAccepted']=True
  console=client/'plutonium/storage/t5/main/console_mp.log'
  client_text=console.read_text(errors='replace') if console.exists() else ''
  loaded=re.search(r'CL_InitCGame: ([0-9.]+) seconds',client_text)
  if q and q.get('clients',0)>0 and loaded:
   if loaded_at is None:loaded_at=time.monotonic()
   if not class_selected and time.monotonic()-loaded_at>=10:
    capture('class-before');class_selected=select_class();result['classSelectionAttempted']=class_selected
   with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as probe:
    probe.settimeout(2);probe.sendto(b'\xff\xff\xff\xffrcon '+admin.encode()+b' status',('127.0.0.1',27015))
    try:status=probe.recv(32768).decode('latin1','replace')
    except socket.timeout:status=''
   rows=[line for line in status.splitlines() if 'LISPJoinTest' in line]
   ping=re.match(r'\s*\d+\s+-?\d+\s+(\d+)\s+',rows[0]) if rows else None
   if ping and int(ping[1])<999:
    stable+=1
    if stable>=3:
     result.update(joined=True,serverQuery=q,activeClientVerified=True,clientMapLoaded=True,livePacketExchangeVerified=True,mapLoadSeconds=float(loaded[1]),rconPlayerRow=rows[0]);break
   else:stable=0
  if cp.poll() is not None:break
  console=client/'plutonium/storage/t5/main/console_mp.log'
  if console.exists() and 'No valid resolutions' in console.read_text(errors='replace'):break
  time.sleep(4)
 capture('final-display');result['clientExitCode']=cp.poll();result['serverQuery']=adapter.query(27015)
 # Logs retained privately; print only relevant diagnostics with test secrets removed.
 for home in [server,client]:
  files=[home/'process.log',*(home/'plutonium/storage/t5').rglob('console*.log')]
  for path in files:
   if path.is_file():
    text=path.read_text(errors='replace').replace(join,'[private]').replace(admin,'[private]')
    lines=[x for x in text.splitlines() if any(k in x.lower() for k in ['error','fail','connect','directx','renderer','password','session','fatal','adapter','d3d','graphics','client'])]
    print(home.name+' '+str(path.relative_to(home))+'\n'+'\n'.join(lines[-18:]),flush=True)
 (parent/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 print('RESULT '+json.dumps(result),flush=True)
 if not result.get('activeClientVerified'):raise SystemExit('Client did not become active; keep T5 hidden.')
finally:
 for process,log in reversed(owned):stop(process);log.close()
