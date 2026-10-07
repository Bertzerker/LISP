"""Run after a completed installation is marked; cleans up only its own matches."""
import argparse,json,time,secrets
from more_games_protocols import source_rcon,unreal1_rules,unreal2_rules
from urllib.request import Request,urlopen
parser=argparse.ArgumentParser();parser.add_argument('game',choices=['tf2','hl2dm','ut99','ut2004']);args=parser.parse_args()
base='http://192.168.8.138';ids=[]
def api(path,data=None):
 with urlopen(Request(base+path,data=json.dumps(data).encode() if data is not None else None,headers={'X-LAN-Request':'1','Content-Type':'application/json'}),timeout=180) as r:return json.load(r)
def ready(ident):
 for _ in range(60):
  item=next(x for x in api('/api/servers')['servers'] if x['id']==ident)
  if item['status']=='running':return item
  if item['status']=='failed':raise AssertionError(item)
  time.sleep(1)
 raise AssertionError('Readiness query timed out')
try:
 catalog=next(x for x in api('/api/catalog')['games'] if x['id']==args.game)
 mode=catalog['modes'][0];maps=[x for x in catalog['maps'] if not mode.get('mapPrefix') or x.startswith(mode['mapPrefix'])];assert maps
 for i in range(2):
  if i and len(catalog['modes'])>1:
   mode=catalog['modes'][2 if args.game.startswith('ut') else 1];maps=[x for x in catalog['maps'] if not mode.get('mapPrefix') or x.startswith(mode['mapPrefix'])];assert maps
  data={'game':args.game,'mode':mode['id'],'map':maps[i%len(maps)],'players':8,'password':'LiveTestJoin'+str(i),'adminPassword':'LiveTestAdmin'+secrets.token_hex(8)}
  if catalog.get('mutators') and i:data['mutators']=[catalog['mutators'][0]['id']]
  started=api('/api/servers',data);ids.append(started['id']);server=ready(started['id']);assert server['passwordProtected'] and server['adminEnabled'];print('PASS ready:',args.game,server['port'],server['currentMap'],flush=True)
  if data.get('mutators'):assert server['mutators']==data['mutators']
  if args.game in ('tf2','hl2dm'):
   response=source_rcon(server['port'],data['adminPassword'],'sv_password')
   assert data['password'] in response,'Native join-password setting differs'
   response=source_rcon(server['port'],data['adminPassword'],'rcon_password')
   assert data['adminPassword'] in response,'Native admin-password setting differs'
   try:source_rcon(server['port'],'WrongTestPassword','status')
   except PermissionError:pass
   else:raise AssertionError('Incorrect RCON password accepted')
   if args.game=='hl2dm':
    response=source_rcon(server['port'],data['adminPassword'],'mp_teamplay')
    assert ('\"1\"' if mode['id']=='teamplay' else '\"0\"') in response,'Native team mode differs'
   print('PASS native configured password and correct/wrong RCON:',args.game,flush=True)
  elif args.game=='ut99':
   rules=unreal1_rules(server['port'])
   assert rules.get('password','').lower() in ('true','1'),'Native UT password flag absent'
   print('PASS native password-protection flag:',args.game,flush=True)
  else:
   rules=unreal2_rules(server['port'])
   assert rules.get('GamePassword')==['True'],'Native UT2004 password flag absent'
   if data.get('mutators'):assert any('instagib' in x.lower() for x in rules.get('Mutator',[])),'Mutator absent from native rules'
   print('PASS native password-protection flag and active mutator rules:',args.game,flush=True)
 current=api('/api/servers')['servers'];ports=[x['port'] for x in current if x['id'] in ids];assert len(set(ports))==2
 if args.game.startswith('ut'):assert abs(ports[0]-ports[1])>=2
 api('/api/servers/'+ids[0]+'/stop',{});ids.pop(0);assert ready(ids[0])['status']=='running';print('PASS independent stop and configured passwords/mutators:',args.game,flush=True)
finally:
 for ident in ids:api('/api/servers/'+ident+'/stop',{})
 print('Removed only test matches',flush=True)
