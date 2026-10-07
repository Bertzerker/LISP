"""Project Zomboid instances, persistent worlds and native RCON readiness."""
import json,os,re,secrets,socket,struct,subprocess,sys,time
from pathlib import Path
from adapters import private_file

REGION=re.compile(r'^[A-Za-z0-9 ,_-]+$')
WORLD=re.compile(r'^[a-f0-9]{12}$')

def rcon(host,port,password,command,timeout=2):
    with socket.create_connection((host,port),timeout=timeout) as sock:
        def read(count):
            data=b''
            while len(data)<count:
                part=sock.recv(count-len(data))
                if not part:raise OSError('RCON closed')
                data+=part
            return data
        def receive():
            size=struct.unpack('<i',read(4))[0]
            if not 10<=size<=1048576:raise ValueError('Invalid RCON packet')
            data=read(size);ident,kind=struct.unpack_from('<ii',data)
            return ident,kind,data[8:-2].decode('utf8','replace')
        def send(kind,text):
            body=struct.pack('<ii',12345,kind)+text.encode()+b'\0\0'
            sock.sendall(struct.pack('<i',len(body))+body)
        send(3,password)
        for _ in range(4):
            ident,kind,_=receive()
            if ident==-1:raise PermissionError('Wrong RCON password')
            if kind==2:break
        else:raise ValueError('Missing RCON authentication')
        send(2,command)
        for _ in range(4):
            ident,kind,text=receive()
            if ident==12345 and kind==0:return text
        raise ValueError('Missing RCON response')

class ZomboidAdapter:
    id='zomboid';name='Project Zomboid';engine='zomboid'
    def __init__(self,root):
        self.path=root/'templates/zomboid';self.world_root=root/'worlds/zomboid'
        self._admin=None;self._details={};self._home=None;self._world=None;self._ready=False;self._level=None
    def installed(self):
        return all((self.path/f).is_file() for f in ('jre64/bin/java','java/projectzomboid.jar','lispclasses/LispZomboid.class','.lisp-installed'))
    def modes(self):return {'coop':'Co-op (Apocalypse)','pvp':'PvP (Apocalypse)'}
    def players(self,mode):return [2,4,6,8]
    def mutators(self):return {}
    def maps(self):
        return sorted(p.name for p in (self.path/'media/maps').iterdir() if p.is_dir() and REGION.fullmatch(p.name) and (p/'map.info').is_file() and (p/'spawnpoints.lua').is_file())
    def worlds(self):
        result=[]
        for meta in self.world_root.glob('*/lisp-world.json'):
            if not WORLD.fullmatch(meta.parent.name):continue
            try:
                data=json.loads(meta.read_text())
                if data['map'] in self.maps() and data['mode'] in self.modes():result.append({k:data[k] for k in ('id','name','mode','map')})
            except (OSError,ValueError,KeyError):continue
        return sorted(result,key=lambda w:w['name'].casefold())
    def catalog(self):
        return {'id':self.id,'name':self.name,'engine':self.engine,'modes':[{'id':k,'name':v,'players':self.players(k)} for k,v in self.modes().items()],'maps':self.maps(),'adminKind':'zomboid','joinPasswordSupported':True,'persistentWorlds':True,'worlds':self.worlds(),'clientNote':'Use the matching stable Steam client. Map selection is a starting region in the shared Kentucky world. Worlds are saved; up to two Zomboid worlds use two ports each. Maximum 8 players per world on this PC.'}
    def reserved_ports(self,port):return [(port,socket.SOCK_DGRAM),(port+1,socket.SOCK_DGRAM),(port,socket.SOCK_STREAM)]
    def public_details(self):return self._details
    def prepare_request(self,home,port,mode,level,players,password,admin_password,admin_ids,mutators,data):
        requested=data.get('world','new')
        if not isinstance(requested,str):raise ValueError('Choose a saved world.')
        self.world_root.mkdir(mode=0o700,parents=True,exist_ok=True);self.world_root.chmod(0o700)
        ident=home.name if requested=='new' else requested
        if not WORLD.fullmatch(ident):raise ValueError('Choose a valid saved world.')
        world=self.world_root/ident
        if world.is_symlink():raise ValueError('Invalid world directory.')
        meta=world/'lisp-world.json'
        if requested!='new':
            if not meta.is_file():raise ValueError('Saved world not found.')
            metadata=json.loads(meta.read_text())
            if (mode,level)!=(metadata['mode'],metadata['map']):raise ValueError('Keep the saved world mode and starting region.')
        else:
            name=data.get('worldName','').strip() if isinstance(data.get('worldName',''),str) else None
            if name is None or not re.fullmatch(r'[A-Za-z0-9 _-]{0,40}',name):raise ValueError('World names may use up to 40 letters, numbers, spaces, underscores or hyphens.')
            world.mkdir(mode=0o700)
            metadata={'id':ident,'name':name or 'LAN world '+ident[:6],'mode':mode,'map':level,'created':int(time.time())}
            private_file(meta,json.dumps(metadata,indent=2)+'\n')
        world.chmod(0o700);self._world=world;self._home=home;self._level=level
        self._details={'worldId':ident,'worldName':metadata['name'],'directPort':port+1,'adminPort':port if admin_password else None}
        self._admin=admin_password or secrets.token_hex(24)
        game=home/'game';game.mkdir()
        subprocess.run(['cp','-a','--reflink=auto',str(self.path)+'/.',str(game)],check=True,timeout=180)
        server='lisp_'+ident
        cfg=world/'Server'/(server+'.ini')
        # Preserve the engine's expanded settings and world IDs when resuming.
        text=cfg.read_text() if cfg.is_file() else ''
        settings={'Public':'false','PublicName':'LISP - '+metadata['name'],'PublicDescription':'Private LAN world','DefaultPort':port,'UDPPort':port+1,'RCONPort':port,'RCONPassword':self._admin,'Password':password,'PVP':str(mode=='pvp').lower(),'MaxPlayers':players,'Open':'true','AutoCreateUserInWhiteList':'true','PauseEmpty':'true','UPnP':'false','SteamVAC':'false','VoiceEnable':'false','SaveWorldEveryMinutes':5,'Mods':'','WorkshopItems':'','Map':'Muldraugh, KY','BackupsOnStart':'false','BackupsOnVersionChange':'true','BackupsPeriod':0}
        for key,value in settings.items():
            text=re.sub(r'^'+re.escape(key)+r'=.*\n?','',text,flags=re.M)
            text+=key+'='+str(value)+'\n'
        private_file(cfg,text)
        sandbox=world/'Server'/(server+'_SandboxVars.lua')
        if not sandbox.exists():private_file(sandbox,(game/'media/lua/shared/Sandbox/Apocalypse.lua').read_text().replace('return {','SandboxVars = {',1))
        regions=world/'Server'/(server+'_spawnregions.lua')
        if not regions.exists():private_file(regions,'function SpawnRegions()\n return { { name = "'+level+'", file = "media/maps/'+level+'/spawnpoints.lua" } }\nend\n')
        private_file(home/'admin-bootstrap.txt',admin_password or self._admin)
        # Use the bundled runtime and official classes; only heap sizing and the bootstrap differ.
        return [str(game/'jre64/bin/java'),'-Djava.awt.headless=true','-Xms256m','-Xmx1536m','-Dzomboid.steam=1','-Dzomboid.znetlog=1','-Djava.library.path='+str(game/'linux64'),'-Djava.security.egd=file:/dev/urandom','-XX:+UseZGC','-XX:-OmitStackTraceInFastThrow','-cp',str(game/'lispclasses')+':'+str(game/'java')+':'+str(game/'java/projectzomboid.jar'),'LispZomboid',str(home/'admin-bootstrap.txt'),'-cachedir='+str(world),'-servername',server,'-ip',os.environ.get('LISP_BIND_IP','192.168.8.138'),'-port',str(port),'-udpport',str(port+1)],game
    def query(self,port):
        if not self._admin or not self._home:return None
        try:
            # RCON can open before map initialization has finished.
            if not self._ready:
                with (self._home/'server.log').open('rb') as log:
                    log.seek(0,2);size=log.tell();log.seek(max(0,size-262144));tail=log.read()
                if b'SERVER STARTED' not in tail:return None
                self._ready=True
            response=rcon('127.0.0.1',port,self._admin,'players',.6)
            match=re.search(r'Players connected\s*\((\d+)\)',response,re.I)
            return {'mapname':self._level,'clients':int(match.group(1)) if match else None}
        except (OSError,ValueError,PermissionError):return None
    def stop_process(self,proc):
        if proc.poll() is not None:return
        try:proc.stdin.write(b'save\nquit\n');proc.stdin.flush()
        except BrokenPipeError:pass
        try:proc.wait(timeout=90)
        except subprocess.TimeoutExpired:raise ValueError('Zomboid is still saving. The world was retained; retry stopping shortly.')
    def after_stop(self):
        if not self._world:return
        for cfg in (self._world/'Server').glob('*.ini'):
            text=cfg.read_text();text=re.sub(r'^(Password|RCONPassword)=.*$',r'\1=',text,flags=re.M)
            private_file(cfg,text)
