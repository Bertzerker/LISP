"""Isolated Unreal Tournament servers using installed OldUnreal binaries."""
import os,re,socket,subprocess,struct
from pathlib import Path
SAFE=re.compile(r'^[A-Za-z0-9_\[\]-]+$')
MODES={
 'ut99':{'dm':('Deathmatch','Botpack.DeathMatchPlus','DM-'),'tdm':('Team Deathmatch','Botpack.TeamGamePlus','DM-'),'ctf':('Capture the Flag','Botpack.CTFGame','CTF-'),'dom':('Domination','Botpack.Domination','DOM-'),'assault':('Assault','Botpack.Assault','AS-')},
 'ut2004':{'dm':('Deathmatch','XGame.xDeathMatch','DM-'),'tdm':('Team Deathmatch','XGame.xTeamGame','DM-'),'ctf':('Capture the Flag','XGame.xCTFGame','CTF-'),'ons':('Onslaught','Onslaught.ONSOnslaughtGame','ONS-'),'assault':('Assault','UT2k4Assault.ASGameInfo','AS-'),'br':('Bombing Run','XGame.xBombingRun','BR-'),'dom':('Double Domination','XGame.xDoubleDom','DOM-'),'invasion':('Invasion','SkaarjPack.Invasion','DM-')}
}
MUTATORS={'ut99':{'Botpack.InstaGibDM':'Instagib','Botpack.LowGrav':'Low gravity','Botpack.NoPowerups':'No powerups'},'ut2004':{'XGame.MutInstaGib':'Instagib','UnrealGame.MutLowGrav':'Low gravity','XGame.MutNoAdrenaline':'No adrenaline'}}
def setting(text,section,values):
 pattern=re.compile(r'^\['+re.escape(section)+r'\]\s*\n(.*?)(?=^\[|\Z)',re.M|re.S)
 match=pattern.search(text)
 body=match.group(1) if match else ''
 for key,value in values.items():
  body=re.sub(r'^'+re.escape(key)+r'=.*\n?','',body,flags=re.M|re.I)
  body+=key+'='+str(value)+'\n'
 replacement='['+section+']\n'+body+'\n'
 return text[:match.start()]+replacement+text[match.end():] if match else text+'\n'+replacement
class UnrealAdapter:
 engine='unreal'
 def __init__(self,root,ident):
  self.id=ident;self.name='Unreal Tournament 2004' if ident=='ut2004' else 'Unreal Tournament';self.path=root/'templates'/ident
  candidates=['System/ucc-bin','System/ucc-bin-amd64','System/ucc-bin-linux-amd64','System/ucc']
  self.launcher=next((x for x in candidates if (self.path/x).is_file()),None)
 def modes(self):return {k:v[0] for k,v in MODES[self.id].items()}
 def maps(self):return sorted({p.stem for p in (self.path/'Maps').glob('*.ut2' if self.id=='ut2004' else '*.unr') if SAFE.fullmatch(p.stem)})
 def players(self,mode):return [2,4,6,8,10,12,16,24,32]
 def mutators(self):return MUTATORS[self.id]
 def map_valid(self,mode,level):return level.startswith(MODES[self.id][mode][2])
 def reserved_ports(self,port):return [(port,socket.SOCK_DGRAM),(port+1,socket.SOCK_DGRAM),(port+10,socket.SOCK_DGRAM)]
 def catalog(self):
  return {'id':self.id,'name':self.name,'engine':self.engine,'modes':[{'id':k,'name':v[0],'players':self.players(k),'mapPrefix':v[2]} for k,v in MODES[self.id].items()],'maps':self.maps(),'mutators':[{'id':k,'name':v} for k,v in self.mutators().items()],'adminKind':'unreal','joinPasswordSupported':True,'clientNote':'Unreal matches reserve a game port and the following query port; up to two Unreal servers can run together.'}
 def prepare(self,home,port,mode,level,players,password,admin_password,admin_ids,mutators=None):
  game=home/'game';game.mkdir();subprocess.run(['cp','-a','--reflink=auto',str(self.path)+'/.',str(game)],check=True,timeout=180)
  ini_name='UT2004.ini' if self.id=='ut2004' else 'UnrealTournament.ini'
  original=game/'System'/ini_name
  if not original.is_file():original=game/'System'/('Default.ini' if self.id=='ut2004' else 'DefaultUnrealTournament.ini')
  text=original.read_text(encoding='utf8',errors='replace') if original.is_file() else ''
  text=text.replace('\r\n','\n')
  # Preserve game-package paths and local query actors, excluding Internet uplinks and shared LAN beacons.
  text=re.sub(r'^ServerActors=.*(?:UdpServerUplink|UdpBeacon).*\n?','',text,flags=re.M|re.I)
  text=setting(text,'URL',{'Port':port,'QueryPort':port+1})
  text=setting(text,'Engine.GameReplicationInfo',{'ServerName':'LAN Party - '+self.name+' - '+str(port),'ShortName':'LISP'})
  text=setting(text,'Engine.GameInfo',{'MaxPlayers':players,'GamePassword':password,'AdminPassword':admin_password,'bChangeLevels':'False','bAdminCanPause':'True','bEnableStatLogging':'False'})
  text=setting(text,'Engine.AccessControl',{'GamePassword':password,'AdminPassword':admin_password})
  text=setting(text,'UWeb.WebServer',{'bEnabled':'False'})
  text=setting(text,'IpDrv.MasterServerUplink',{'DoUplink':'False','UplinkToGamespy':'False','UplinkToMasterServer':'False','bAllowPlayerUplink':'False','DoLANBroadcast':'False'})
  text=setting(text,'IpServer.UdpServerUplink',{'DoUplink':'False'})
  text=setting(text,'IpDrv.UdpGamespyQuery',{'OldQueryPortNumber':port+10,'bRestartServerOnPortSwap':'False'})
  config=game/'System/LISP.ini';config.write_text(text,encoding='utf8');config.chmod(0o600)
  url=level+'?game='+MODES[self.id][mode][1]+'?MaxPlayers='+str(players)+'?MinPlayers=0'
  if mutators:url+='?mutator='+','.join(mutators)
  return [str(game/self.launcher),'server',url,'ini='+str(config),'port='+str(port),'log='+str(home/'unreal.log'),'-nohomedir','-lanplay','MULTIHOME='+os.environ.get('LISP_BIND_IP','192.168.8.138')],game/'System'
 def query(self,port):
  host=os.environ.get('LISP_BIND_IP','192.168.8.138')
  with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
   s.settimeout(.6)
   try:
    if self.id=='ut2004':
     s.sendto(bytes([0x79,0,0,0,0]),(host,port+1));return unreal2_info(s.recv(16384))
    s.sendto(b'\\status\\',(host,port+1));data=s.recv(16384).decode('latin1');values=data.split('\\');info=dict(zip(values[1::2],values[2::2]))
    if not info.get('gamename') and not info.get('mapname'):return None
    return {'mapname':info.get('mapname',''),'clients':int(info.get('numplayers','0')),'maxPlayers':int(info.get('maxplayers','0')),'passwordProtected':info.get('password','').lower() in ('true','1')}
   except (OSError,ValueError):return None

def unreal2_info(packet):
 if len(packet)<9 or packet[4]!=0:return None
 pos=5
 def number():
  nonlocal pos
  value=struct.unpack_from('<I',packet,pos)[0];pos+=4;return value
 def string():
  nonlocal pos
  length=packet[pos];pos+=1
  wide=bool(length&128);length=(length&127)*(2 if wide else 1)
  if wide and pos<len(packet) and packet[pos]==1:pos+=1
  if pos+length>len(packet):raise ValueError('Truncated Unreal query')
  raw=packet[pos:pos+length];pos+=length
  return raw.decode('utf-16-le' if wide else 'latin1').rstrip('\0')
 try:
  number();string();number();number();string();level=string();string();clients=number();maximum=number()
  return {'mapname':level,'clients':clients,'maxPlayers':maximum}
 except (IndexError,ValueError,struct.error):return None
