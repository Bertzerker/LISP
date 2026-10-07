"""Isolated LAN servers for IW4x and Plutonium, using owned game data."""
import ipaddress,os,re,socket,subprocess,sys
from pathlib import Path
from adapters import private_file
SAFE=re.compile(r'^[A-Za-z0-9_-]+$')
MP={'dm':'Free for All','tdm':'Team Deathmatch','dom':'Domination','sd':'Search and Destroy','sab':'Sabotage','koth':'Headquarters','ctf':'Capture the Flag'}
DEFINITIONS={
 'iw4x':('Call of Duty: Modern Warfare 2 — IW4x','iw4x',MP),
 'iw5':('Call of Duty: Modern Warfare 3 — Plutonium','iw5mp',MP),
 't4':('Call of Duty: World at War — Plutonium','t4mp',MP),
 't5':('Call of Duty: Black Ops — Plutonium','t5mp',{**MP,'dem':'Demolition'}),
 't6':('Call of Duty: Black Ops II — Plutonium','t6mp',{'dm':'Free for All','tdm':'Team Deathmatch','dom':'Domination','sd':'Search and Destroy','hq':'Headquarters','ctf':'Capture the Flag','koth':'Hardpoint','conf':'Kill Confirmed','dem':'Demolition','gun':'Gun Game'}),
}
WINE=Path(os.environ.get('LISP_COD_WINE','/usr/bin/wine'))
class CodAdapter:
 engine='cod'
 def __init__(self,root,ident):
  self.root=root;self.id=ident;self.name,self.target,self.base_modes=DEFINITIONS[ident]
  self.path=root/'templates'/ident;self.prefix=root/'templates/cod-wine-prefix';self.runtime=root/'runtimes/plutonium'
  specific=root/'templates'/(ident+'-wine-prefix')
  if (specific/'system.reg').is_file():self.prefix=specific
 def installed(self):
  executable=self.path/'iw4x.exe' if self.id=='iw4x' else self.runtime/'bin/plutonium-bootstrapper-win32.exe'
  return all(p.is_file() for p in [self.path/'.lisp-installed',executable,self.prefix/'system.reg',WINE]) and bool(self.maps())
 def maps(self):
  result=set()
  for f in (self.path/'zone').rglob('mp_*.ff'):
   if SAFE.fullmatch(f.stem) and not f.stem.endswith(('_load','_patch','_s','_s_load','_shaders')):result.add(f.stem)
  return sorted(result,key=str.casefold)
 def modes(self):return self.base_modes
 def players(self,mode):return [2,4,6,8,10,12,16,18] if self.id in ('iw4x','iw5','t5','t6') else [2,4,6,8,10,12,16,24,32]
 def mutators(self):return {}
 def reserved_ports(self,port):return [(port,socket.SOCK_DGRAM),(port+1,socket.SOCK_DGRAM)] if self.id=='t5' else [(port,socket.SOCK_DGRAM)]
 def catalog(self):
  return {'id':self.id,'name':self.name,'engine':self.engine,'maps':self.maps(),
   'modes':[{'id':k,'name':v,'players':self.players(k)} for k,v in self.modes().items()],
   'adminKind':'cod','joinPasswordSupported':True,'adminInstructions':self.admin_instructions(),
   'clientNote':'Use the matching IW4x client and connect through its console.' if self.id=='iw4x' else 'Use the matching Plutonium game in LAN mode, then connect through its console. Online-mode clients cannot join a LAN-mode server.'}
 def admin_instructions(self):
  return 'In the game console: rcon_password YOUR_ADMIN_PASSWORD, then rcon COMMAND.' if self.id=='iw4x' else 'In the game console: rcon login YOUR_ADMIN_PASSWORD, then rcon COMMAND. Use rcon logout when finished.'
 def public_details(self):return {'adminKind':'cod','clientNote':self.catalog()['clientNote'],'adminInstructions':self.admin_instructions()}
 def prepare_request(self,home,port,mode,level,players,password,admin_password,admin_ids,mutators,data):
  return self.prepare(home,port,mode,level,players,password,admin_password,admin_ids,mutators,query_clients=data.get('_queryClients',[]))
 def prepare(self,home,port,mode,level,players,password,admin_password,admin_ids,mutators=None,query_clients=None):
  game=home/'game';prefix=home/'wine'
  for source,target in [(self.path,game),(self.prefix,prefix)]:
   target.mkdir()
   subprocess.run(['cp','-a','--reflink=auto',str(source)+'/.',str(target)],check=True,timeout=180)
  localized=[p.name for p in (game/'zone').iterdir() if p.is_dir() and p.name.lower() in ('english','german')]
  language=0 if any(x.lower()=='english' for x in localized) else 2
  engine_mode='war' if mode=='tdm' and self.id in ('iw4x','iw5') else mode
  config=f'''set sv_hostname "LISP {self.name} - {port}"
set sv_maxclients "{players}"
set party_maxplayers "{players}"
set g_password "{password}"
set rcon_password "{admin_password}"
set rconPassword "{admin_password}"
set sv_pure "0"
set sv_allowDownload "0"
set sv_voice "0"
set sv_lanOnly "1"
set loc_language "{language}"
set g_gametype "{engine_mode}"
set sv_maprotation "gametype {engine_mode} map {level}"
set g_log "lisp-game.log"
set g_logSync "2"
'''
  if self.id=='t5':config+='set sv_connectTimeout "180"\nset g_inactivity "190"\n'
  if self.id=='t4':
   # T4 uses tdm and matching UI/game limits. Its official hosting guide
   # warns that nondefault party_maxplayers can cause map-change timeouts.
   config=config.replace(f'set party_maxplayers "{players}"\n',f'set ui_maxclients "{players}"\n')
  if self.id in ('t4','t5','t6'):
   # The user approved LAN-wide queries on 192.168.8.0/24. These engines
   # share their query/RCON allowlist; RCON still requires its private password.
   config+='rconWhitelistAdd "127.0.0.1"\n'
   clients={str(ip) for ip in ipaddress.ip_network('192.168.8.0/24').hosts()}
   clients.update(query_clients or [])
   for address in sorted(clients):
    address=ipaddress.IPv4Address(address)
    config+=f'rconWhitelistAdd "{address}"\n'
  if self.id=='iw4x':
   config+=f'set sv_lanOnly "1"\nset party_enable "0"\nset sv_gametype "{engine_mode}"\n'
   private_file(game/'userraw/lisp.cfg',config)
   executable=game/'iw4x.exe'
   # Wine binds a specific-IP socket to its physical interface, which drops
   # queries from the controller on this same host. Bind all local interfaces;
   # the existing LAN-only firewall still restricts who can reach the port.
   args=['-dedicated','-stdout','+set','net_port',str(port),'+set','net_ip','0.0.0.0','+set','loc_language',str(language),'+exec','lisp.cfg','+map',level]
   cwd=game
  else:
   pluto=home/'plutonium';pluto.mkdir()
   subprocess.run(['cp','-a','--reflink=auto',str(self.runtime)+'/.',str(pluto)],check=True,timeout=180)
   # Bootstrapper locates game/storage beside its own bin directory. Each
   # instance gets its own storage, logs, profiles and registry.
   private_file(game/'main/lisp.cfg',config)
   private_file(pluto/('storage/'+self.id+'/lisp.cfg'),config)
   executable=pluto/'bin/plutonium-bootstrapper-win32.exe'
   if self.id=='iw5':
    dsr={'dm':'FFA_default','tdm':'TDM_default','dom':'DOM_default','sd':'SD_default','sab':'SAB_default','koth':'HQ_default','ctf':'CTF_default'}[mode]
    config=config.replace(f'gametype {engine_mode} map {level}',f'dsr {dsr} map {level}')
    private_file(game/'admin/lisp.cfg',config)
   args=[self.target,'Z:'+str(game).replace('/','\\'),'-dedicated','-lan','+set','net_ip','0.0.0.0','+set','net_port',str(port),'+set','loc_language',str(language)]
   args += ['+set','sv_config','lisp.cfg','+start_map_rotate'] if self.id=='iw5' else ['+exec','lisp.cfg','+map_rotate']
   cwd=pluto
  private_file(home/'cod-launch.json',__import__('json').dumps({'wine':str(WINE),'executable':str(executable),'args':args,'cwd':str(cwd)}))
  return [sys.executable,str(Path(__file__).with_name('run_cod.py')),str(home)],cwd
 def query(self,port):
  try:
   if self.id=='t5':
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
     sock.settimeout(.6);sock.sendto(b'\xff\xff\xff\xffgetinfo lisp',('127.0.0.1',port));data=sock.recv(32768)
    if not data.startswith(b'\xff\xff\xff\xffinfoResponse'):return None
    parts=data[4:].decode('latin1').splitlines()[1].lstrip('\\').split('\\');info=dict(zip(parts[0::2],parts[1::2]))
    return {'mapname':info.get('mapname',''),'clients':int(info.get('clients','0')),'maxPlayers':int(info.get('com_maxclients',info.get('sv_maxclients','0'))),'passwordProtected':info.get('pswrd')=='1','gametype':info.get('gametype','')}
   with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
    sock.settimeout(.6);sock.sendto(b'\xff\xff\xff\xffgetstatus lisp',('127.0.0.1',port));data=sock.recv(32768)
   if not data.startswith(b'\xff\xff\xff\xffstatusResponse'):return None
   lines=data[4:].decode('latin1').splitlines();parts=lines[1].split('\\');info=dict(zip(parts[1::2],parts[2::2]))
   protected=info.get('g_password','0') not in ('','0') or info.get('g_needpass')=='1'
   # Plutonium advertises join protection as pswrd in getinfo, without
   # publishing the password itself in getstatus.
   with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
    sock.settimeout(.6);sock.sendto(b'\xff\xff\xff\xffgetinfo lisp',('127.0.0.1',port))
    try:
     extra=sock.recv(32768)
     if extra.startswith(b'\xff\xff\xff\xffinfoResponse'):
      values=extra[4:].decode('latin1').splitlines()[1].split('\\');details=dict(zip(values[1::2],values[2::2]));protected=protected or details.get('pswrd')=='1' or details.get('isPrivate')=='1'
    except socket.timeout:pass
   gametype=info.get('g_gametype','');gametype='tdm' if gametype=='war' and self.id in ('iw4x','iw5') else gametype
   return {'mapname':info.get('mapname',''),'clients':len([p for p in lines[2:] if p.strip()]),'maxPlayers':int(info.get('sv_maxclients',info.get('com_maxclients','0'))),'passwordProtected':protected,'gametype':gametype}
  except (OSError,ValueError,IndexError):return None
