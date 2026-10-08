"""Original Windows dedicated engines, isolated behind per-match Wine prefixes."""
import configparser,json,os,re,secrets,socket,struct,subprocess,zipfile
from pathlib import Path
from adapters import Adapter,private_file
from rez_index import entries

WOLF_MODES={'objective':('Objective','sdGameRulesObjective'),'stopwatch':('Stopwatch','sdGameRulesStopWatch'),'tdm':('Team Deathmatch','sdGameRulesTDM')}

def wolf_info(data):
 """WolfMP getInfo: challenge/serial/protocol header followed by a NUL dictionary."""
 if not data.startswith(b'\xff\xffinfoResponse\0') or len(data)<32:raise ValueError('Invalid WolfMP reply')
 pos=31;info={}
 while pos<len(data):
  end=data.index(0,pos);key=data[pos:end].decode('ascii');pos=end+1
  if not key:break
  if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*',key):raise ValueError('Invalid WolfMP info key')
  end=data.index(0,pos);info[key]=data[pos:end].decode('latin1');pos=end+1
 return info

class Wolf2009Adapter(Adapter):
 def __init__(self,root):
  super().__init__(('wolf2009','Wolfenstein (2009)','wolfmp','templates/wolf2009','base','Wolf2MPLite.exe',{k:v[0] for k,v in WOLF_MODES.items()}))
  self.root=root;self.path=root/'templates/wolf2009'
  self.rules=WOLF_MODES
  self.runtime=Path(os.environ.get('LISP_CLASSIC_WINE_RUNTIME','/usr/share/steam/compatibilitytools.d/proton-cachyos-slr/files'))
 def installed(self):return (self.path/'.lisp-installed').is_file() and (self.path/self.launcher).is_file() and (self.runtime/'bin/wine').is_file() and (self.root/'templates/classic-wine-prefix').is_dir() and bool(self.maps())
 def maps(self):
  result=set()
  for archive in (self.path/'base').glob('*.pk4'):
   try:
    with zipfile.ZipFile(archive) as z:
     for name in z.namelist():
      match=re.fullmatch(r'mapinfo/(mp_[A-Za-z0-9_-]+)\.md',name)
      if match:result.add(match[1])
   except (OSError,zipfile.BadZipFile):continue
  return sorted(result,key=str.casefold)
 def reserved_ports(self,port):return [(port,socket.SOCK_DGRAM)]
 def map_valid(self,mode,level):return mode in WOLF_MODES and level in self.maps()
 def catalog(self):
  value=super().catalog();value.update(self.public_details())
  value['clientNote']='Use the original Wolfenstein multiplayer client with matching patches; LAN mode does not use the retired online master.'
  return value
 def public_details(self):return {'adminInstructions':'In the game console: net_clientRemoteConsolePassword YOUR_ADMIN_PASSWORD, then rcon COMMAND.','joinInstructions':'Open Wolfenstein (2009) multiplayer, open its console, and paste the connect command.','joinPasswordInstructions':'Set password YOUR_JOIN_PASSWORD in the game console before connecting.'}
 def prepare(self,home,port,mode,level,players,password,admin_password,admin_ids,mutators=None):
  game=home/'game';game.mkdir()
  subprocess.run(['cp','-a','--reflink=auto',str(self.path)+'/.',str(game)],check=True,timeout=180)
  prefix=home/'wine';prefix.mkdir()
  subprocess.run(['cp','-a','--reflink=auto',str(self.root/'templates/classic-wine-prefix')+'/.',str(prefix)],check=True,timeout=180)
  private_file(game/'base/lisp.cfg',f'''set net_serverDedicated "1"
set net_LANServer "1"
set net_LANForceAuth "0"
set net_serverPunkbusterEnabled "0"
set net_useUPnP "0"
set net_updateAutoDownload "0"
set net_updateAutoExecute "0"
set net_port "{port}"
set net_serverRemoteConsolePassword "{admin_password}"
set si_name "LISP Wolfenstein 2009 - {port}"
set si_maxPlayers "{players}"
set si_maxPlayersPerTeam "{players//2}"
set si_minPlayers "2"
set si_minPlayersPerTeam "1"
set si_needPass "{int(bool(password))}"
set g_password "{password}"
set si_pure "0"
set si_rules "{WOLF_MODES[mode][1]}"
''')
  args=['+set','net_serverDedicated','1','+set','net_port',str(port),'+set','net_LANServer','1','+set','net_LANForceAuth','0','+set','net_serverPunkbusterEnabled','0','+set','fs_basepath','Z:'+str(game).replace('/','\\'),'+set','fs_savepath','Z:'+str(home).replace('/','\\'),'+set','logFile','2','+exec','lisp.cfg','+spawnServer',level]
  private_file(home/'wine-command.json',json.dumps({'executable':self.launcher,'args':args}))
  return ['/usr/bin/python3',str(Path(__file__).with_name('run_classic_wine.py')),str(home),str(self.runtime)],game
 def query(self,port):
  with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
   s.settimeout(.6)
   try:
    s.sendto(b'\xff\xffgetInfo\0'+b'\0'*4,(os.environ.get('LISP_BIND_IP','192.168.8.138'),port));data=s.recv(16384);info=wolf_info(data)
    level=info.get('si_map','');level=level.removeprefix('maps/').removesuffix('.entities')
    if level not in self.maps():return None
    return {'mapname':level,'clients':None,'maxPlayers':int(info.get('si_maxPlayers','0')),'passwordProtected':info.get('si_needPass')=='1','mode':info.get('si_rules','')}
   except (OSError,ValueError,IndexError,UnicodeError):return None

PH_MODES={'dm':('Deathmatch',1,'worlds/multi/dm/','DM'),'tdm':('Team Deathmatch',2,'worlds/multi/dm/','Team DM'),'hunt':('Hunt',3,'worlds/multi/dm/','HUNT'),'survivor':('Survivor',4,'worlds/multi/survivor/','SURVIVOR'),'overrun':('Overrun',5,'worlds/multi/overrun/','OVERRUN'),'evac':('Evacuation',6,'worlds/multi/evac/','EVAC')}
PH_SECTIONS={'dm':'Deathmatch','tdm':'TeamDeathmatch','hunt':'Hunt','survivor':'Survivor','overrun':'Overrun','evac':'Evac'}

class PrimalHuntAdapter(Wolf2009Adapter):
 def __init__(self,root):
  super().__init__(root);self.id='avp2ph';self.name='Aliens vs Predator 2: Primal Hunt';self.engine='lithtech';self.mod='';self.launcher='AVP2XServ.exe';self.path=root/'templates/avp2ph';self.rules=PH_MODES;self.base_modes={k:v[0] for k,v in PH_MODES.items()}
 def maps(self):
  result=set()
  for archive in self.path.glob('*.REZ'):
   try:
    for name,off,size in entries(archive):
     if re.fullmatch(r"worlds/multi/[a-z0-9_-]+/[a-z0-9_' -]+\.dat",name):result.add(name[:-4])
   except (OSError,ValueError,struct.error,UnicodeError):continue
  for path in (self.path/'worlds/multi').rglob('*.dat'):
   name=path.relative_to(self.path).as_posix().lower()
   if re.fullmatch(r"worlds/multi/[a-z0-9_-]+/[a-z0-9_' -]+\.dat",name):result.add(name[:-4])
  return sorted(result,key=str.casefold)
 def players(self,mode):return [2,4,6,8,10,12,16]
 def map_valid(self,mode,level):return mode in PH_MODES and level in self.maps() and level.startswith(PH_MODES[mode][2])
 def catalog(self):
  value=Adapter.catalog(self);value.update(self.public_details());value['adminKind']='avp2ph'
  value['clientNote']='Use Primal Hunt with the community Master Server Patch 1.1. The base AVP2 client cannot join the expansion.'
  for mode in value['modes']:mode['mapPrefix']=PH_MODES[mode['id']][2]
  return value
 def public_details(self):return {'adminKind':'avp2ph','joinCommandKind':'address','joinInstructions':'Open Primal Hunt → Multiplayer LAN. Select the LISP server, or enter the displayed address in its direct-IP connection dialog.','joinPasswordInstructions':'Enter the join password when Primal Hunt prompts for it.','adminInstructions':'In game chat: <serv> control "YOUR_ADMIN_PASSWORD", then <serv> nextlevel, <serv> restart or <serv> kick PLAYER_NAME.'}
 def prepare(self,home,port,mode,level,players,password,admin_password,admin_ids,mutators=None):
  if not self.map_valid(mode,level):raise ValueError('Choose a map for the selected Primal Hunt mode.')
  game=home/'game';game.mkdir();prefix=home/'wine';prefix.mkdir()
  subprocess.run(['cp','-a','--reflink=auto',str(self.path)+'/.',str(game)],check=True,timeout=180)
  subprocess.run(['cp','-a','--reflink=auto',str(self.root/'templates/classic-wine-prefix')+'/.',str(prefix)],check=True,timeout=180)
  config=configparser.ConfigParser(interpolation=None);config.optionxform=str;config.read(game/'ServerData/default.txt')
  # Avoid an empty native controller credential; when administration is disabled,
  # use a private random token that is never exposed to players.
  controller_password=admin_password or secrets.token_hex(24)
  config['Settings'].update(Dedicated='1',PortID=str(port),Password='"'+password+'"',LANConnection='1',Locked=str(int(bool(password))),ServerName=f'"LISP Primal Hunt - {port}"',SCPassword='"'+controller_password+'"',GameType=str(PH_MODES[mode][1]))
  for section in PH_SECTIONS.values():
   for key in list(config[section]):
    if re.fullmatch(r'Map\d+',key):del config[section][key]
   config[section]['MaxTotalPlayers']=str(players)
  selected=config[PH_SECTIONS[mode]];selected['Map00']='"'+level.replace('/','\\')+'"'
  for key in list(selected):
   if re.fullmatch(r'MaxPlayers\d+',key):selected[key]=str(players)
  # One config avoids the native configuration-selection dialog.
  for path in (game/'ServerData').glob('*.txt'):path.unlink()
  import io
  out=io.StringIO();config.write(out);private_file(game/'ServerData/lisp.txt',out.getvalue())
  basepath='Z:'+str(game/'base-resources').replace('/','\\')+'\\'
  private_file(home/'wine-command.json',json.dumps({'executable':self.launcher,'args':['-config','lisp','-port',str(port)],'registry':[[r'HKLM\Software\Monolith Productions\Aliens vs. Predator 2\1.0',basepath]]}))
  return ['/usr/bin/python3',str(Path(__file__).with_name('run_classic_wine.py')),str(home),str(self.runtime)],game
 def query(self,port):
  with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
   s.settimeout(.6)
   try:
    s.sendto(b'\\status\\',(os.environ.get('LISP_BIND_IP','192.168.8.138'),port));data=s.recv(16384).decode('latin1');parts=data.split('\\');info=dict(zip(parts[1::2],parts[2::2]))
    if info.get('gamename')!='avp2ph' or not info.get('mapname'):return None
    return {'mapname':info['mapname'],'clients':int(info.get('numplayers','0')),'maxPlayers':int(info.get('maxplayers','0')),'passwordProtected':info.get('lock')=='1','mode':info.get('gametype','')}
   except (OSError,ValueError,IndexError):return None
