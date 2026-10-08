"""Engine adapters: inventory, maps, isolated configuration and readiness probes."""
import os,re,socket,struct,subprocess,zipfile
from pathlib import Path
ROOT=Path(os.environ.get('LISP_SERVER_ROOT','/srv/lan-party/servers'))
SAFE=re.compile(r'^[A-Za-z0-9_-]+$')
QL_MODES={'ffa':'Free for All','duel':'Duel','tdm':'Team Deathmatch','ca':'Clan Arena','ctf':'Capture the Flag','ft':'Freeze Tag','dom':'Domination','race':'Race'}
DEFINITIONS=[
 ('quakelive','Quake Live','quake','quakelive','baseq3','run_server_x64.sh',QL_MODES),
 ('tf2','Team Fortress 2','source','templates/tf2','tf','srcds_run_64',{'default':'Map default'}),
 ('hl2dm','Half-Life 2: Deathmatch','source','templates/hl2dm','hl2mp','srcds_run',{'deathmatch':'Deathmatch','teamplay':'Team Deathmatch'}),
 ('sof2','Soldier of Fortune II Gold (1.03)','idtech3','templates/sof2','base','sof2ded',{'dm':'Deathmatch','tdm':'Team Deathmatch','ctf':'Capture the Flag','inf':'Infiltration','elim':'Elimination'}),
 ('halflife','Half-Life','goldsrc','templates/halflife','valve','hlds_run',{'deathmatch':'Deathmatch','teamplay':'Team Deathmatch'}),
 ('cstrike','Counter-Strike 1.6','goldsrc','templates/halflife','cstrike','hlds_run',{'standard':'Standard'}),
 ('crossproduct','Half-Life: Cross Product','goldsrc','templates/crossproduct','zamnhlmp','hlds_run',{}),
 ('l4d2','Left 4 Dead 2','source','templates/l4d2','left4dead2','srcds_run',{'coop':'Campaign','realism':'Realism','versus':'Versus','survival':'Survival','scavenge':'Scavenge'}),
 ('jabroni','Jabroni Brawl: Episode 3','source','templates/jabroni','jbep3','srcds_run.sh',{'default':'Map default / rotation'})]

def archive_maps(path):
    names=[]
    try:
        if path.suffix=='.pk3':
            with zipfile.ZipFile(path) as z:names=z.namelist()
        elif path.suffix=='.pak':
            with path.open('rb') as f:
                magic,off,size=struct.unpack('<4sII',f.read(12))
                if magic!=b'PACK':return []
                f.seek(off)
                for _ in range(size//64):names.append(f.read(64)[:56].split(b'\0')[0].decode('ascii','ignore'))
        elif path.name.endswith('_dir.vpk'):
            with path.open('rb') as f:
                magic,version,size=struct.unpack('<III',f.read(12))
                if magic!=0x55aa1234 or version not in (1,2):return []
                if version==2:f.read(16)
                tree=f.read(size)
            pos=0
            def string():
                nonlocal pos
                end=tree.index(0,pos);value=tree[pos:end].decode('utf8','replace');pos=end+1;return value
            while (ext:=string()):
                while (folder:=string()):
                    while (name:=string()):
                        _,preload,_,_,_,_=struct.unpack_from('<IHHIIH',tree,pos);pos+=18+preload
                        if ext=='bsp':names.append(folder+'/'+name+'.bsp')
    except (OSError,ValueError,struct.error,zipfile.BadZipFile):pass
    return [Path(n).stem for n in names if n.startswith('maps/') and n.endswith('.bsp') and SAFE.fullmatch(Path(n).stem)]

def private_file(path,text):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(text,encoding='utf8');path.chmod(0o600)

class Adapter:
    def __init__(self,definition):
        self.id,self.name,self.engine,folder,self.mod,self.launcher,self.base_modes=definition
        self.path=ROOT/folder
    def modes(self):
        if self.id=='crossproduct':return {p.stem:p.stem for p in sorted((self.path/self.mod/'gamemodes').glob('*.cfg')) if SAFE.fullmatch(p.stem)}
        return self.base_modes
    def maps(self):
        folders=[self.path/self.mod]
        if self.id=='l4d2':folders += [self.path/n for n in ('left4dead2_dlc1','left4dead2_dlc2','left4dead2_dlc3','update')]
        if self.id=='quakelive':folders += [self.path/'steamapps/workshop/content/282440']
        maps=set()
        for folder in folders:
            maps.update(p.stem for p in (folder/'maps').glob('*.bsp') if SAFE.fullmatch(p.stem))
            for pattern in ('*.pk3','*.pak','*_dir.vpk'):
                for archive in folder.rglob(pattern):maps.update(archive_maps(archive))
        if self.id=='sof2':maps={m for m in maps if m.startswith('mp_')}
        return sorted(maps,key=str.casefold)
    def players(self,mode):
        if self.id=='quakelive' and mode=='duel':return [2]
        if self.id=='l4d2':return [8] if mode in ('versus','scavenge') else [4]
        return [2,4,6,8,10,12,16,24,32]
    def catalog(self):
        return {'id':self.id,'name':self.name,'engine':self.engine,'modes':[{'id':k,'name':v,'players':self.players(k)} for k,v in self.modes().items()],'maps':self.maps(),'adminKind':'steamid-zmq' if self.engine=='quake' else 'rcon','joinPasswordSupported':self.id!='l4d2','clientNote':'Requires Soldier of Fortune II Gold v1.03 clients. Uses the community-patched SoF2.org Gold server.' if self.id=='sof2' else '', 'joinPasswordNote':'Left 4 Dead 2 has a native join-password bug. Join passwords are unavailable; admin passwords still work.' if self.id=='l4d2' else ''}
    def mutators(self):return {}
    def reserved_ports(self,port):return [(port,socket.SOCK_DGRAM),(port,socket.SOCK_STREAM),(port+1000,socket.SOCK_STREAM)]
    def prepare(self,home,port,mode,level,players,password,admin_password,admin_ids,mutators=None):
        if self.engine=='quake':
            base=home/'baseq3';base.mkdir()
            private_file(base/'mappool.txt',f'{level}|{mode}\n')
            private_file(base/'access.txt',''.join(f'{ident}|admin\n' for ident in admin_ids))
            private_file(base/'server.cfg',f'''set sv_hostname "LAN Party - Quake Live - {port}"
set sv_maxclients "{players}"
set teamsize "{players//2 if mode in ('tdm','ca','ctf','ft','dom') else 0}"
set sv_master "0"
set sv_serverType "2"
set sv_lan "0"
set g_password "{password}"
set g_accessFile "access.txt"
set zmq_rcon_enable "{int(bool(admin_password))}"
set zmq_rcon_ip "0.0.0.0"
set zmq_rcon_port "{port+1000}"
set zmq_rcon_password "{admin_password}"
set zmq_stats_enable "0"
set sv_mapPoolFile "mappool.txt"
set serverstartup "map {level} {mode}"
''')
            return [str(self.path/self.launcher),'+set','net_strict','1','+set','net_port',str(port),'+set','fs_homepath',str(home),'+exec','server.cfg'],self.path
        game=home/'game';game.mkdir()
        # reflinks are independent files; no symlink/hardlink config sharing.
        subprocess.run(['cp','-a','--reflink=auto',str(self.path)+'/.',str(game)],check=True,timeout=180)
        if self.id in ('l4d2','tf2','hl2dm'):
            app={'l4d2':'550','tf2':'440','hl2dm':'320'}[self.id]
            private_file(game/'steam_appid.txt',app+'\n')
            sdk=home/'.steam/sdk32';sdk.mkdir(parents=True)
            for name,candidate in [('sdk32',game/'bin/steamclient.so'),('sdk64',(game/'bin/linux64/steamclient.so') if (game/'bin/linux64/steamclient.so').is_file() else ROOT/'steamcmd/linux64/steamclient.so')]:
                if candidate.is_file():
                    folder=home/'.steam'/name;folder.mkdir(parents=True,exist_ok=True);(folder/'steamclient.so').symlink_to(candidate)
        if self.id=='sof2':
            private_file(game/'base/lisp.cfg',f'''set sv_hostname "LAN Party - Soldier of Fortune II - {port}"
set sv_maxclients "{players}"
set g_gametype "{mode}"
set g_password "{password}"
set rconpassword "{admin_password}"
set sv_pure "0"
set sv_allowDownload "0"
set sv_punkbuster "0"
set sv_master1 ""
set sv_master2 ""
set sv_master3 ""
set sv_master4 ""
set sv_master5 ""
''')
            private_file(game/'base/server.cfg','exec lisp.cfg\n')
            return ['/usr/bin/env','LD_LIBRARY_PATH='+str(game),'LD_PRELOAD='+str(game/'lisp-dns-compat.so'),str(game/'sof2ded'),'+set','dedicated','1','+set','net_ip',os.environ.get('LISP_BIND_IP','192.168.8.138'),'+set','net_port',str(port),'+set','fs_basepath',str(game),'+set','fs_homepath',str(home),'+set','vm_game','2','+exec','lisp.cfg','+map',level],game
        launcher=game/self.launcher
        launcher.write_bytes(launcher.read_bytes().replace(b'\r\n',b'\n'))
        cfg=game/self.mod/('cfg' if self.engine=='source' else '')
        settings=f'''hostname "LAN Party - {self.name} - {port}"
sv_lan 0
sv_password "{password}"
rcon_password "{admin_password}"
sv_cheats 0
'''
        if self.id=='hl2dm':settings+=f'mp_teamplay {int(mode=="teamplay")}\n'
        if self.id=='tf2':
            # This engine asks for bin/replay_srv.so even in its 64-bit build.
            # Redirect only the private instance to the installed matching module.
            replay=game/'bin/replay_srv.so'
            replay.unlink()
            replay.symlink_to('linux64/replay_srv.so')
            settings+='tf_bot_quota 0\nreplay_enable 0\n'
        if self.id=='halflife':settings+=f'mp_teamplay {int(mode=="teamplay")}\n'
        if self.id=='crossproduct':settings+=f'sv_aura_gamemode "{mode}"\n'
        if self.id=='l4d2':settings+='sv_allow_lobby_connect_only 0\nsv_steamgroup_exclusive 0\n'
        private_file(cfg/'lisp.cfg',settings)
        # Replace instance-only startup settings; never inherit a saved password.
        private_file(cfg/'server.cfg','exec lisp.cfg\n')
        private_file(cfg/'autoexec.cfg','exec lisp.cfg\n')
        args=[str(game/self.launcher),'-norestart','-console','-game',self.mod,'-port',str(port),'-ip',os.environ.get('LISP_BIND_IP','192.168.8.138'),'+maxplayers',str(players),'+exec','lisp.cfg','+map',level]
        if self.engine=='goldsrc':args += ['-nomaster','-sport',str(port-115)]
        if self.id=='l4d2':args += [mode]
        if self.id=='jabroni':
            args.remove('-console')
            args += ['-dedicated']
        return args,game
    def query(self,port):
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
            sock.settimeout(.6)
            request=b'\xff\xff\xff\xffgetstatus lisp' if self.engine=='idtech3' else b'\xff\xff\xff\xffgetchallenge 12345' if self.engine=='quake' else (b'\xff\xff\xff\xffchallenge rcon\n' if self.engine=='goldsrc' else b'\xff\xff\xff\xffTSource Engine Query\x00')
            try:
                sock.sendto(request,(os.environ.get('LISP_BIND_IP','192.168.8.138'),port));data=sock.recv(16384)
                if self.engine=='idtech3':
                    if not data.startswith(b'\xff\xff\xff\xffstatusResponse\n'):return None
                    lines=data[4:].decode('latin1').splitlines();values=lines[1].split('\\');info=dict(zip(values[1::2],values[2::2]))
                    return {'mapname':info.get('mapname',''),'clients':sum(bool(x.strip()) for x in lines[2:]),'maxPlayers':int(info.get('sv_maxclients','0')),'passwordProtected':info.get('g_needpass')=='1'}
                if self.engine=='goldsrc':return {} if b'challenge rcon ' in data else None
                if self.engine=='quake':return {} if b'challengeResponse ' in data or b'No Steam auth token.' in data else None
                if data[4:5]==b'A':sock.sendto(request+data[5:9],(os.environ.get('LISP_BIND_IP','192.168.8.138'),port));data=sock.recv(16384)
                if data[4:5]==b'I':
                    pos=6;values=[]
                    for _ in range(4):end=data.index(0,pos);values.append(data[pos:end].decode('utf8','replace'));pos=end+1
                    pos+=2
                    return {'mapname':values[1],'clients':data[pos],'maxPlayers':data[pos+1],'passwordProtected':bool(data[pos+5])}
                if data[4:5]==b'm':return {} # Legacy GoldSrc response.
            except (OSError,IndexError,ValueError):pass
            return None

def registry():
    from unreal_adapter import UnrealAdapter
    games={a.id:a for a in map(Adapter,DEFINITIONS) if (a.path/a.launcher).is_file() and (a.id not in ('tf2','hl2dm') or (a.path/'.lisp-installed').is_file())}
    for ident in ('ut99','ut2004'):
        a=UnrealAdapter(ROOT,ident)
        if a.launcher and (a.path/'.lisp-installed').is_file():games[a.id]=a
    from swbf2_adapter import Swbf2Adapter
    a=Swbf2Adapter(ROOT)
    if a.installed():games[a.id]=a
    from etlegacy_adapter import EtLegacyAdapter
    a=EtLegacyAdapter(ROOT)
    if a.installed():games[a.id]=a
    from zomboid_adapter import ZomboidAdapter
    a=ZomboidAdapter(ROOT)
    if a.installed():games[a.id]=a
    from cod_adapter import CodAdapter,DEFINITIONS as COD_GAMES
    for ident in COD_GAMES:
        a=CodAdapter(ROOT,ident)
        if a.installed():games[a.id]=a
    from classic_adapter import ClassicQuakeAdapter,DEFINITIONS as CLASSIC_GAMES
    for ident in CLASSIC_GAMES:
        a=ClassicQuakeAdapter(ROOT,ident)
        if a.installed():games[a.id]=a
    from classic_windows_adapter import Wolf2009Adapter,PrimalHuntAdapter
    for cls in (Wolf2009Adapter,PrimalHuntAdapter):
        a=cls(ROOT)
        if a.installed():games[a.id]=a
    return games
