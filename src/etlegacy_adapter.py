"""Native ET: Legacy servers with independent files and UDP administration."""
import os,socket,subprocess
from adapters import Adapter,archive_maps,private_file,SAFE

MODES={'objective':('Objective',2),'stopwatch':('Stopwatch',3),'lms':('Last Man Standing',5),'mapvote':('Map Voting',6)}

class EtLegacyAdapter(Adapter):
    def __init__(self,root):
        self.id='etlegacy';self.name='Wolfenstein: Enemy Territory — ET: Legacy'
        self.engine='idtech3';self.path=root/'templates/etlegacy'
        self.mod='legacy';self.launcher='etlded.x86_64'
        self.base_modes={k:v[0] for k,v in MODES.items()}

    def installed(self):
        return (self.path/self.launcher).is_file() and (self.path/'.lisp-installed').is_file()

    def maps(self):
        maps=set()
        for folder in ('etmain','legacy'):
            maps.update(p.stem for p in (self.path/folder/'maps').glob('*.bsp') if SAFE.fullmatch(p.stem))
            for archive in (self.path/folder).glob('*.pk3'):maps.update(archive_maps(archive))
        return sorted(maps,key=str.casefold)

    def reserved_ports(self,port):return [(port,socket.SOCK_DGRAM)]

    def catalog(self):
        result=super().catalog()
        result.update(adminKind='etlegacy',clientNote='Use ET: Legacy 2.86.0 with its Legacy mod and original ET game packs. Connect directly to the displayed address.')
        return result

    def prepare(self,home,port,mode,level,players,password,admin_password,admin_ids,mutators=None):
        game=home/'game';game.mkdir()
        subprocess.run(['cp','-a','--reflink=auto',str(self.path)+'/.',str(game)],check=True,timeout=180)
        gametype=MODES[mode][1]
        # Credentials remain in private files, never process arguments or public status.
        private_file(game/'legacy/lisp.cfg',f'''set sv_hostname "LISP ET Legacy - {port}"
set sv_maxclients "{players}"
set sv_privateclients "0"
set sv_privatepassword ""
set g_password "{password}"
set rconpassword "{admin_password}"
set refereePassword "{admin_password}"
set shoutcastPassword ""
set dedicated "1"
set sv_advert "0"
set sv_master1 ""
set sv_master2 ""
set sv_master3 ""
set sv_master4 ""
set sv_master5 ""
set sv_pure "1"
set sv_allowDownload "1"
set sv_wwwDownload "0"
set sv_maxRate "0"
set sv_dlRate "1000"
set sv_punkbuster "0"
set omnibot_enable "0"
set lua_modules ""
set g_gametype "{gametype}"
set g_warmup "10"
set g_doWarmup "1"
set g_minGameClients "2"
set g_inactivity "0"
set g_spectatorInactivity "0"
set g_log "lisp-game.log"
set logfile "1"
set nextmap "map {level}"
''')
        private_file(game/'legacy/server.cfg','exec lisp.cfg\n')
        private_file(game/'legacy/autoexec.cfg','exec lisp.cfg\n')
        return [str(game/self.launcher),'+set','fs_basepath',str(game),'+set','fs_homepath',str(home),'+set','fs_game','legacy','+set','net_ip',os.environ.get('LISP_BIND_IP','192.168.8.138'),'+set','net_port',str(port),'+set','dedicated','1','+exec','lisp.cfg','+map',level],game
