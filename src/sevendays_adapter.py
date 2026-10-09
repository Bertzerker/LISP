"""Native Steam 7 Days to Die servers with owned persistent worlds."""
import json,os,re,secrets,socket,subprocess,time,xml.etree.ElementTree as ET
from pathlib import Path
from adapters import private_file

WORLD=re.compile(r'^[a-f0-9]{12}$')
ADMIN_HELP='7 Days to Die uses SteamID64 permissions for in-game admin, not an in-game admin password. Enter your SteamID64 below to use F1 console commands. The admin password protects the remote Telnet console on port GAME_PORT+1000.'

def console(host,port,password,command,timeout=2):
    with socket.create_connection((host,port),timeout=timeout) as sock:
        sock.settimeout(timeout)
        def until(predicate):
            data=b''
            while len(data)<1048576:
                part=sock.recv(65536)
                if not part:break
                data+=part
                if predicate(data):break
            return data.decode('utf8','replace')
        welcome=until(lambda b:b'password' in b.lower())
        if 'password' not in welcome.lower():raise ValueError('Missing console password prompt')
        sock.sendall(password.encode()+b'\n')
        reply=until(lambda b:b'password' in b.lower() or b'help' in b.lower())
        if 'password' in reply.lower():raise PermissionError('Wrong console password')
        sock.sendall(command.encode()+b'\n')
        data=b''
        while len(data)<1048576:
            try:part=sock.recv(65536)
            except socket.timeout:break
            if not part:break
            data+=part
        return data.decode('utf8','replace')

class SevenDaysAdapter:
    id='sevendays';name='7 Days to Die';engine='sevendays'
    def __init__(self,root):
        self.path=root/'templates/sevendays';self.world_root=root/'worlds/sevendays';self._home=None;self._world=None;self._details={};self._admin=None;self._level=None;self._ready=False;self._ids=[]
    def build(self):return json.loads((self.path/'.lisp-source.json').read_text())['buildid']
    def installed(self):return all((self.path/f).is_file() for f in ('7DaysToDieServer.x86_64','UnityPlayer.so','serverconfig.xml','.lisp-installed'))
    def modes(self):return {'coop':'Survival / Co-op','pvp':'Survival / PvP'}
    def players(self,mode):return [2,4,6,8]
    def mutators(self):return {}
    def maps(self):
        return sorted(p.name for p in (self.path/'Data/Worlds').iterdir() if p.is_dir() and re.fullmatch(r'[A-Za-z0-9_-]+',p.name) and all((p/f).is_file() for f in ('map_info.xml','main.ttw','spawnpoints.xml')))
    def worlds(self):
        result=[]
        for meta in self.world_root.glob('*/lisp-world.json'):
            if not WORLD.fullmatch(meta.parent.name):continue
            try:
                data=json.loads(meta.read_text())
                if data.get('buildid')==self.build() and data['map'] in self.maps() and data['mode'] in self.modes():result.append({k:data[k] for k in ('id','name','mode','map','ownerId')})
            except (OSError,ValueError,KeyError):continue
        return sorted(result,key=lambda w:w['name'].casefold())
    def catalog(self):
        return {'id':self.id,'name':self.name,'engine':self.engine,'maps':self.maps(),'modes':[{'id':k,'name':v,'players':self.players(k)} for k,v in self.modes().items()],'adminKind':'steamid-telnet','adminInstructions':ADMIN_HELP,'joinPasswordSupported':True,'persistentWorlds':True,'worlds':self.worlds(),'clientNote':'Use the matching Steam PC client. Choose an installed world. Progress survives Save & stop. Allow time for the world to load. Six total servers can run; large worlds share this PC memory.'}
    def reserved_ports(self,port):return [(port,socket.SOCK_DGRAM),(port+2,socket.SOCK_DGRAM),(port,socket.SOCK_STREAM),(port+1000,socket.SOCK_STREAM)]
    def public_details(self):return self._details
    def prepare_request(self,home,port,mode,level,players,password,admin_password,admin_ids,mutators,data):
        requested=data.get('world','new');actor=data['_actor']
        if not isinstance(requested,str):raise ValueError('Choose a saved world.')
        ident=home.name if requested=='new' else requested
        if not WORLD.fullmatch(ident):raise ValueError('Choose a valid saved world.')
        self.world_root.mkdir(parents=True,mode=0o700,exist_ok=True);world=self.world_root/ident
        if world.is_symlink():raise ValueError('Invalid world folder.')
        meta=world/'lisp-world.json'
        if requested!='new':
            if not meta.is_file():raise ValueError('Saved world not found.')
            metadata=json.loads(meta.read_text())
            if metadata.get('buildid')!=self.build():raise ValueError('This world needs its original game build.')
            if actor['role']!='admin' and metadata.get('ownerId')!=actor['id']:raise PermissionError('Only the world owner or an administrator can resume it.')
            if (mode,level)!=(metadata['mode'],metadata['map']):raise ValueError('Keep the saved world mode and map.')
        else:
            name=data.get('worldName','')
            if not isinstance(name,str) or not re.fullmatch(r'[A-Za-z0-9 _-]{0,40}',name):raise ValueError('World names may use up to 40 letters, numbers, spaces, underscores or hyphens.')
            world.mkdir(mode=0o700);metadata={'id':ident,'name':name.strip() or 'LAN world '+ident[:6],'map':level,'mode':mode,'created':int(time.time()),'buildid':self.build(),'ownerId':actor['id']};private_file(meta,json.dumps(metadata,indent=2)+'\n')
        self._home=home;self._world=world;self._level=level;self._admin=admin_password or secrets.token_hex(24);self._ids=admin_ids
        game=home/'game';game.mkdir();subprocess.run(['cp','-a','--reflink=auto',str(self.path)+'/.',str(game)],check=True,timeout=180)
        tree=ET.parse(game/'serverconfig.xml');settings={
            'ServerName':'LISP - '+metadata['name'],'ServerDescription':'Private LAN survival world','ServerPassword':password,'ServerPort':port,'ServerVisibility':0,'ServerDisabledNetworkProtocols':'SteamNetworking','ServerMaxPlayerCount':players,'ServerReservedSlots':0,'ServerAdminSlots':0,'WebDashboardEnabled':'false','EnableMapRendering':'false','TelnetEnabled':'true','TelnetPort':port+1000,'TelnetPassword':self._admin,'TerminalWindowEnabled':'false','ServerAllowCrossplay':'false','EACEnabled':'true','UserDataFolder':str(world),'AdminFileName':'serveradmin.xml','GameWorld':level,'GameName':'lisp_'+ident,'GameMode':'GameModeSurvival','PlayerKillingMode':0 if mode=='coop' else 3,'DynamicMeshEnabled':'false','MaxSpawnedZombies':32,'MaxSpawnedAnimals':24,'ServerMaxAllowedViewDistance':8,
        }
        for key,value in settings.items():
            prop=tree.getroot().find("property[@name='"+key+"']")
            if prop is None:prop=ET.SubElement(tree.getroot(),'property',{'name':key})
            prop.set('value',str(value))
        config=home/'serverconfig.xml';private_file(config,ET.tostring(tree.getroot(),encoding='unicode')+'\n')
        self._details={'persistentWorld':True,'worldId':ident,'worldName':metadata['name'],'adminKind':'steamid-telnet','adminPort':port+1000 if admin_password else None,'adminInstructions':ADMIN_HELP.replace('GAME_PORT+1000',str(port+1000)),'inGameAdminEnabled':bool(admin_ids),'joinCommandKind':'address','joinInstructions':'Open 7 Days to Die → Join a Game → Connect to IP. Enter the address and game port above. Use a Steam PC client matching the server version.','joinPasswordInstructions':'Enter the server join password when the game asks for it.'}
        return ['/usr/bin/env','LD_LIBRARY_PATH='+str(game),str(game/'7DaysToDieServer.x86_64'),'-quit','-batchmode','-nographics','-dedicated','-logfile',str(home/'engine.log'),'-configfile='+str(config)],game
    def query(self,port):
        if not self._home:return None
        try:
            if not self._ready:
                path=self._home/'engine.log'
                with path.open('rb') as f:f.seek(0,2);size=f.tell();f.seek(max(0,size-131072));tail=f.read()
                if b'GameServer.Init successful' not in tail and b'GameServer initialization successful' not in tail:return None
                for ident in self._ids:
                    response=console('127.0.0.1',port+1000,self._admin,'admin add Steam_'+ident+' 0',1)
                    if 'added' not in response.lower() and 'updated' not in response.lower():raise ValueError('In-game administrator setup failed')
                self._ready=True
            response=console('127.0.0.1',port+1000,self._admin,'lp',.3)
            match=re.search(r'Total of (\d+) in the game',response,re.I)
            return {'mapname':self._level,'clients':int(match.group(1)) if match else None}
        except (OSError,ValueError,PermissionError):return None
    def stop_process(self,proc):
        if proc.poll() is not None:return
        # Native shutdown saves the world. Never force-kill an active save.
        try:console('127.0.0.1',self._details['adminPort'] or int(ET.parse(self._home/'serverconfig.xml').getroot().find("property[@name='TelnetPort']").get('value')),self._admin,'shutdown',1)
        except (OSError,ValueError,PermissionError):
            if not self._ready:
                proc.terminate()
            else:raise ValueError('Cannot reach the save/shutdown console; the world is retained. Retry stopping.')
        try:proc.wait(timeout=120)
        except subprocess.TimeoutExpired:raise ValueError('The world is still saving. Retry stopping shortly.')
    def after_stop(self):pass
