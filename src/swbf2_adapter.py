"""Original 2005 Battlefront II dedicated server, with private Wine instances."""
import hashlib, os, re, secrets, socket, subprocess, sys
from pathlib import Path
from adapters import private_file

RUNTIME=Path(os.environ.get('LISP_SWBF2_RUNTIME','/usr/share/steam/compatibilitytools.d/proton-cachyos-slr/files'))
MODES={'con':'Conquest','ctf':'Capture the Flag','1flag':'One Flag CTF','ass':'Space Assault','hunt':'Hunt','eli':'Hero Assault'}
LOCATIONS={'cor1':'Coruscant','dag1':'Dagobah','dea1':'Death Star','end1':'Endor','fel1':'Felucia','geo1':'Geonosis','hot1':'Hoth','kam1':'Kamino','kas2':'Kashyyyk','mus1':'Mustafar','myg1':'Mygeeto','nab2':'Naboo','pol1':'Polis Massa','spa1':'Space Yavin','spa3':'Space Kashyyyk','spa6':'Space Mygeeto','spa7':'Space Felucia','spa8':'Space Hoth','spa9':'Space Tatooine','tan1':'Tantive IV','tat2':'Mos Eisley','tat3':'Jabba’s Palace','uta1':'Utapau','yav1':'Yavin 4'}

class Swbf2Adapter:
    id='swbf2';name='Star Wars Battlefront II (2005)';engine='swbf2'
    def __init__(self,root):
        self.path=root/'templates/swbf2';self.prefix=root/'templates/swbf2-wine-prefix'
        self._admin=None
    def installed(self):
        return all(p.is_file() for p in (self.path/'BattlefrontII.exe',self.path/'.lisp-installed',self.prefix/'system.reg',RUNTIME/'bin/wine',RUNTIME/'bin/wineserver')) and Path('/usr/bin/xvfb-run').is_file()
    def maps(self):
        try:data=(self.path/'data/_LVL_PC/mission.lvl').read_bytes()
        except OSError:return []
        return sorted({m.decode('ascii') for m in re.findall(rb'(?<![A-Za-z0-9_])([a-z]{3}[1-9][cg]_(?:con|ctf|1flag|ass|hunt|eli))\x00',data)})
    def modes(self):return {k:v for k,v in MODES.items() if any(m.endswith('_'+k) for m in self.maps())}
    def players(self,mode):return [2,4,6,8,10,12,16,24,32]
    def mutators(self):return {}
    def map_valid(self,mode,level):return level in self.maps() and level.endswith('_'+mode)
    def catalog(self):
        maps=self.maps()
        return {'id':self.id,'name':self.name,'engine':self.engine,'maps':maps,
                'mapLabels':{m:LOCATIONS.get(m[:4],m[:4])+' · '+('Clone Wars' if m[4]=='c' else 'Galactic Civil War')+' · '+m for m in maps},
                'modes':[{'id':k,'name':v,'players':self.players(k),'mapSuffix':'_'+k} for k,v in self.modes().items()],
                'adminKind':'swbf2','passwordMaxLength':15,'joinPasswordSupported':True,'clientNote':'Original 2005 game: join through Multiplayer → LAN. Modern Steam/GOG client compatibility still needs a player test.'}
    def reserved_ports(self,port):return [(port,socket.SOCK_DGRAM),(port,socket.SOCK_STREAM)]
    def prepare(self,home,port,mode,level,players,password,admin_password,admin_ids,mutators=None):
        if not self.map_valid(mode,level):raise ValueError('Choose a Battlefront map matching the mode.')
        game=home/'game';prefix=home/'wine'
        for source,target in ((self.path,game),(self.prefix,prefix)):
            target.mkdir()
            subprocess.run(['cp','-a','--reflink=auto',str(source)+'/.',str(target)],check=True,timeout=180)
        # A private random credential permits readiness checks when player admin is blank.
        self._admin=admin_password or secrets.token_hex(7)
        cfg=f'''/gamename "LISP Battlefront II - {port}"
/password "{password}"
/adminpw "{self._admin}"
/ip {os.environ.get('LISP_BIND_IP','192.168.8.138')}
/gameport {port}
/rconport {port}
/playerlimit {players}
/playercount 0
/lan 1
/tps 30
/bandwidth 6144
/pregametime 0
/conaiperteam 4
/ctfaiperteam 4
/assaiperteam 4
/difficulty 2
/heroes 1
'''
        private_file(game/'settings/ServerSettings.cfg',cfg)
        private_file(game/'settings/ServerRotation.cfg','/addmap '+level+'\n')
        return [sys.executable,str(Path(__file__).with_name('run_swbf2.py')),str(home),str(RUNTIME)],game
    def query(self,port):
        if not self._admin:return None
        try:
            with socket.create_connection((os.environ.get('LISP_BIND_IP','192.168.8.138'),port),timeout=.6) as s:
                def read(n):
                    result=b''
                    while len(result)<n:
                        chunk=s.recv(n-len(result))
                        if not chunk:raise OSError('Truncated status')
                        result+=chunk
                    return result
                s.sendall(hashlib.md5(self._admin.encode('ascii')).hexdigest().encode()+b'\x64')
                if read(1)!=b'\x01':return None
                s.sendall(b'\x01\x08/status\0');count=read(1)[0]
                if count not in (12,13):return None
                values={}
                for _ in range(count):
                    row=read(read(1)[0]).rstrip(b'\0').decode('ascii','replace');key,sep,value=row.partition(':')
                    if sep:values[key.strip()]=value.strip()
                level=values.get('Current map','')
                if level not in self.maps():return None
                return {'mapname':level,'clients':sum(int(n) for n in values['Players'].split('/')),'maxPlayers':int(values['Max players']),'passwordProtected':bool(values.get('Password'))}
        except (OSError,ValueError,KeyError):return None
