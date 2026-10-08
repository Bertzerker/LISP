"""Isolated native Elite Force and Jedi Academy dedicated servers."""
import re,socket,subprocess,zipfile
from adapters import Adapter,private_file

DEFINITIONS={
 'eliteforce':('Star Trek: Voyager - Elite Force','baseEF','cMod-dedicated',{'ffa':('Free for All',0,'hm_'),'tdm':('Team Deathmatch',3,'hm_'),'ctf':('Capture the Flag',4,'ctf_')}),
 'jka':('Star Wars Jedi Knight: Jedi Academy','base','openjkded.x86_64',{'ffa':('Free for All',0,'mp/ffa'),'duel':('Duel',3,'mp/duel'),'powerduel':('Power Duel',4,'mp/duel'),'tdm':('Team Deathmatch',6,'mp/ffa'),'siege':('Siege',7,'mp/siege'),'ctf':('Capture the Flag',8,'mp/ctf')})}

class ClassicQuakeAdapter(Adapter):
 def __init__(self,root,ident):
  name,mod,launcher,self.rules=DEFINITIONS[ident]
  super().__init__((ident,name,'idtech3','templates/'+ident,mod,launcher,{k:v[0] for k,v in self.rules.items()}))
  self.path=root/'templates'/ident
 def installed(self):return (self.path/'.lisp-installed').is_file() and (self.path/self.launcher).is_file() and bool(self.maps())
 def maps(self):
  result=set()
  for archive in (self.path/self.mod).glob('*.pk3'):
   try:
    with zipfile.ZipFile(archive) as z:
     for name in z.namelist():
      if name.startswith('maps/') and name.endswith('.bsp'):
       level=name[5:-4]
       if re.fullmatch(r'(?:mp/)?[A-Za-z0-9_-]+',level) and any(level.startswith(v[2]) for v in self.rules.values()):result.add(level)
   except (OSError,zipfile.BadZipFile):continue
  for f in (self.path/self.mod/'maps').rglob('*.bsp'):
   level=f.relative_to(self.path/self.mod/'maps').as_posix()[:-4]
   if re.fullmatch(r'(?:mp/)?[A-Za-z0-9_-]+',level) and any(level.startswith(v[2]) for v in self.rules.values()):result.add(level)
  return sorted(result,key=str.casefold)
 def players(self,mode):return [2] if mode=='duel' else [3] if mode=='powerduel' else [2,4,6,8,10,12,16,24,32]
 def map_valid(self,mode,level):return mode in self.rules and level in self.maps() and level.startswith(self.rules[mode][2])
 def reserved_ports(self,port):return [(port,socket.SOCK_DGRAM)]
 def catalog(self):
  value=super().catalog()
  for mode in value['modes']:mode['mapPrefix']=self.rules[mode['id']][2]
  value['clientNote']='Use an Elite Force 1.2 Holomatch client (or cMod).' if self.id=='eliteforce' else 'Use Jedi Academy multiplayer 1.01 (or OpenJK).'
  value['adminInstructions']='In the game console: rconpassword YOUR_ADMIN_PASSWORD, then rcon COMMAND.'
  return value
 def public_details(self):return {'adminInstructions':self.catalog()['adminInstructions']}
 def prepare(self,home,port,mode,level,players,password,admin_password,admin_ids,mutators=None):
  if not self.map_valid(mode,level):raise ValueError('Choose a multiplayer map for the selected mode.')
  game=home/'game';game.mkdir()
  subprocess.run(['cp','-a','--reflink=auto',str(self.path)+'/.',str(game)],check=True,timeout=180)
  settings=f'''set sv_hostname "LISP {self.name} - {port}"
set sv_maxclients "{players}"
set g_gametype "{self.rules[mode][1]}"
set g_password "{password}"
set rconpassword "{admin_password}"
set sv_pure "0"
set sv_allowDownload "0"
set bot_minplayers "0"
set sv_master1 ""
set sv_master2 ""
set sv_master3 ""
set sv_master4 ""
set sv_master5 ""
'''
  private_file(game/self.mod/'lisp.cfg',settings)
  private_file(game/self.mod/'server.cfg','exec lisp.cfg\n')
  args=[str(game/self.launcher),'+set','dedicated','1','+set','net_ip','0.0.0.0','+set','net_port',str(port),'+set','fs_basepath',str(game),'+set','fs_homepath',str(home)]
  if self.id=='eliteforce':args+=['+set','fs_dirs','*fs_basepath']
  args+=['+exec','lisp.cfg','+map',level]
  return args,game
