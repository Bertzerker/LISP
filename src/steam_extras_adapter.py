"""Steam dedicated servers using isolated Wine prefixes and private configurations."""
import os,re,socket,subprocess,json
from pathlib import Path
from adapters import Adapter,archive_maps,private_file
from classic_windows_adapter import Wolf2009Adapter,wolf_info

BRINK_MODES={'objective':'Objective','stopwatch':'Stopwatch'}
CONTAGION_MODES={'escape':('Escape','ce_'),'extraction':('Extraction','cx_'),'hunted':('Hunted','ch_'),'hordemode':('Horde Mode','chm_'),'flatline':('Flatline','cf_'),'panic':('Panic','cp_')}

class SteamWineAdapter(Wolf2009Adapter):
 def __init__(self,root):
  super().__init__(root)
  # Proton's Steam bridge requires a running client. Dedicated engines use
  # stock Wine and the native Steam libraries shipped in their own depot.
  self.runtime=Path(os.environ.get('LISP_STEAM_WINE_RUNTIME','/usr'))
 def installed(self):
  return super().installed()
 def copy_instance(self,home):
  game=home/'game';game.mkdir();prefix=home/'wine';prefix.mkdir()
  for source,target in ((self.path,game),(self.root/'templates/classic-wine-prefix',prefix)):
   subprocess.run(['cp','-a','--reflink=auto',str(source)+'/.',str(target)],check=True,timeout=180)
  return game
 def command(self,home,game,args):
  private_file(home/'wine-command.json',json.dumps({'executable':self.launcher,'args':args,'dllOverrides':'steam,steam_api,steamclient,steamclient64=n;mscoree,mshtml=d'}))
  return ['/usr/bin/python3',str(Path(__file__).with_name('run_classic_wine.py')),str(home),str(self.runtime)],game

class BrinkAdapter(SteamWineAdapter):
 def __init__(self,root):
  super().__init__(root);self.id='brink';self.name='Brink';self.engine='brink';self.mod='base';self.launcher='brink.exe';self.path=root/'templates/brink';self.base_modes=BRINK_MODES
 def maps(self):
  # SDMD2 indexes contain NUL-terminated directory and filename tables.
  # Only installed multiplayer entity entries become selectable maps.
  maps=set()
  for index in (self.path/'base').glob('*.sdmd2'):
   folder=''
   for raw in re.findall(rb'[\x20-\x7e]{4,}',index.read_bytes()):
    value=raw.decode('ascii')
    if value.endswith('/'):folder=value
    elif folder=='maps/mp/' and re.fullmatch(r'[A-Za-z0-9_-]+\.entities',value):maps.add('mp/'+value[:-9])
  return sorted(maps,key=str.casefold)
 def players(self,mode):return [2,4,6,8,10,12,16]
 def map_valid(self,mode,level):return mode in BRINK_MODES and level in self.maps()
 def reserved_ports(self,port):return [(port,socket.SOCK_DGRAM),(port+1,socket.SOCK_DGRAM),(port+2000,socket.SOCK_DGRAM)]
 def catalog(self):
  value=Adapter.catalog(self);value.update(self.public_details());value['clientNote']='Use the Steam version of Brink with the installed DLC maps. Each match uses a game/query port pair; two matches can run together.';return value
 def public_details(self):return {'adminInstructions':'In the Brink console: net_clientRemoteConsoleAddress IP:PORT and net_clientRemoteConsolePassword YOUR_ADMIN_PASSWORD, then rcon COMMAND.','joinInstructions':'Open Brink, open its console, and paste the connect command.','joinPasswordInstructions':'Set password YOUR_JOIN_PASSWORD in the Brink console before connecting.'}
 def prepare(self,home,port,mode,level,players,password,admin_password,admin_ids,mutators=None):
  if not self.map_valid(mode,level):raise ValueError('Choose an installed Brink map and mode.')
  game=self.copy_instance(home)
  private_file(game/'base/lisp.cfg',f'''applyServerConfig Standard
set si_rules "{'sdGameRulesObjective' if mode=='objective' else 'sdGameRulesStopWatch'}"
set si_playMode "2"
set si_onlineMode "3"
set si_name "LISP Brink - {port}"
set si_maxPlayers "{players}"
set si_maxPlayersHuman "{players}"
set si_maxTeamSize "{players//2}"
set si_minPlayers "2"
set si_rankRestricted "0"
set si_needPass "{int(bool(password))}"
set g_password "{password}"
set net_serverRemoteConsolePassword "{admin_password}"
set net_serverAllowHijacking "0"
set bot_minClients "0"
spawnServer {level}.entities
''')
  return self.command(home,game,['+set','net_serverDedicated','1','+set','net_ip','0.0.0.0','+set','net_serverPort',str(port),'+set','net_serverPortMaster',str(port+1),'+set','net_serverPortAuth',str(port+2000),'+set','exec_maxThreads','2','+set','fs_savepath','Z:'+str(home).replace('/','\\'),'+set','logFile','2','+exec','lisp.cfg'])
 def query(self,port):
  info=Adapter.query(self,port+1)
  if not info:return None
  level=info['mapname'].removeprefix('maps/').removesuffix('.entities')
  if not level.startswith('mp/'):level='mp/'+level
  if level not in self.maps():return None
  info['mapname']=level
  return info

class ContagionAdapter(SteamWineAdapter):
 def __init__(self,root):
  super().__init__(root);self.id='contagion';self.name='Contagion';self.engine='source';self.mod='contagion';self.launcher='contagionds.exe';self.path=root/'templates/contagion';self.base_modes={k:v[0] for k,v in CONTAGION_MODES.items()}
 def maps(self):
  maps=set(Adapter.maps(self))
  for index in (self.path/'vpks').glob('*_dir.vpk'):maps.update(archive_maps(index))
  return sorted((m for m in maps if any(m.startswith(v[1]) for v in CONTAGION_MODES.values())),key=str.casefold)
 def modes(self):return {k:v[0] for k,v in CONTAGION_MODES.items() if any(m.startswith(v[1]) for m in self.maps())}
 def players(self,mode):return [2,4,6,8] if mode!='hunted' else [2,4,6,8,10,12,16]
 def reserved_ports(self,port):return [(port,socket.SOCK_DGRAM),(port,socket.SOCK_STREAM)]
 def map_valid(self,mode,level):return mode in self.modes() and level in self.maps() and level.startswith(CONTAGION_MODES[mode][1])
 def catalog(self):
  value=Adapter.catalog(self);value.update(self.public_details());value['clientNote']='Uses the current official Windows dedicated server in Wine; the Linux depot lacks engine libraries.'
  for mode in value['modes']:mode['mapPrefix']=CONTAGION_MODES[mode['id']][1]
  return value
 def public_details(self):return {'adminInstructions':'In the Contagion console: rcon_address IP:PORT and rcon_password YOUR_ADMIN_PASSWORD, then rcon COMMAND.','joinInstructions':'Open Contagion, open its console, and paste the connect command.','joinPasswordInstructions':'Set password YOUR_JOIN_PASSWORD in the Contagion console before connecting.'}
 def prepare(self,home,port,mode,level,players,password,admin_password,admin_ids,mutators=None):
  if not self.map_valid(mode,level):raise ValueError('Choose a Contagion map for the selected mode.')
  game=self.copy_instance(home)
  private_file(game/'steam_appid.txt','238430\n')
  private_file(game/'contagion/cfg/lisp.cfg',f'''hostname "LISP Contagion - {port}"
sv_lan 0
sv_password "{password}"
rcon_password "{admin_password}"
sv_cheats 0
exec gamemodes/{mode}.cfg
''')
  private_file(game/'contagion/cfg/server.cfg','exec lisp.cfg\n')
  private_file(game/'contagion/cfg/autoexec.cfg','exec lisp.cfg\n')
  return self.command(home,game,['-steam','-console','-dedicated','-condebug','-game','contagion','-port',str(port),'-ip','0.0.0.0','+maxplayers',str(players),'+exec','lisp.cfg','+map',level])
 def query(self,port):return Adapter.query(self,port)
