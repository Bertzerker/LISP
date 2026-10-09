"""Two owned native instances, saved-world restart and independent shutdown."""
import json,os,pathlib,secrets,signal,subprocess,sys,time,resource
sys.path.insert(0,os.environ.get('LISP_TEST_SRC',str(pathlib.Path(__file__).resolve().parents[1]/'src')));sys.path.insert(1,'/opt/lan-portal')
from zomboid_adapter import ZomboidAdapter,rcon
from sevendays_adapter import SevenDaysAdapter,console
resource.setrlimit(resource.RLIMIT_NOFILE,(16384,resource.getrlimit(resource.RLIMIT_NOFILE)[1]))
assert os.geteuid()!=0,'Run owned engine tests as lanserver, never root'
root=pathlib.Path('/srv/lan-party/servers');game=sys.argv[1];cls=ZomboidAdapter if game=='zomboid' else SevenDaysAdapter
test=root/'survival-tests'/('pair-'+game+'-'+secrets.token_hex(4));test.mkdir(mode=0o700);owned=[]
def launch(index,world='new',previous=None):
 a=cls(root);ident=secrets.token_hex(6);home=test/ident;home.mkdir(mode=0o700);port=(27015 if index==0 else 27017) if game=='zomboid' else 27015+index
 probes=[]
 try:
  for number,kind in a.reserved_ports(port):
   probe=__import__('socket').socket(__import__('socket').AF_INET,kind);probes.append(probe);probe.bind(('0.0.0.0',number))
 finally:
  for probe in probes:probe.close()
 level=(['Rosewood, KY','Echo Creek, KY'] if game=='zomboid' else ['Navezgane','Pregen06k01'])[index];mode=['coop','pvp'][index];players=[2,4][index];admin=previous['admin'] if previous else secrets.token_hex(12);join=previous['join'] if previous else secrets.token_hex(12)
 args,cwd=a.prepare_request(home,port,mode,level,players,join,admin,['76561198000000001'] if game=='sevendays' else [],[],{'world':world,'worldName':'Owned pair validation','_actor':{'id':1,'role':'admin'}})
 env=os.environ.copy();env['HOME']=str(home)
 if game=='zomboid':env['LD_LIBRARY_PATH']=':'.join(str(home/'game'/p) for p in ['linux64','','jre64/lib'])
 log=(home/'server.log').open('ab');proc=subprocess.Popen(args,cwd=cwd,env=env,stdin=subprocess.PIPE if game=='zomboid' else subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 item={'id':ident,'adapter':a,'home':str(home),'port':port,'mode':mode,'map':level,'players':players,'admin':admin,'join':join,'process':proc,'log':log,'worldId':a.public_details()['worldId']};owned.append(item)
 public=[{k:v for k,v in i.items() if k not in ('adapter','process','log')} for i in owned]
 (test/'state.json').write_text(json.dumps({'game':game,'instances':public}));(test/'state.json').chmod(0o600)
 return item
def ready(items):
 for _ in range(24):
  time.sleep(15)
  if all(i['adapter'].query(i['port']) is not None for i in items):return
  for i in items:
   if i['process'].poll() is not None:raise AssertionError('Owned engine exited with '+str(i['process'].returncode))
 raise AssertionError('Owned engines did not become ready')
def stop(item):
 item['adapter'].stop_process(item['process']);item['adapter'].after_stop();item['log'].close()
try:
 first=launch(0);second=launch(1);print('Owned pair',game,test.name,flush=True);ready([first,second])
 for item in [first,second]:
  function=rcon if game=='zomboid' else console;host='192.168.8.138' if game=='zomboid' else '127.0.0.1';port=item['port'] if game=='zomboid' else item['port']+1000;command='players' if game=='zomboid' else 'lp'
  assert function(host,port,item['admin'],command,1)
  try:function(host,port,'WrongOwnedTestPassword',command,1);raise AssertionError('Wrong admin password accepted')
  except PermissionError:pass
  cfg=root/'worlds'/game/item['worldId']
  if game=='sevendays':assert '76561198000000001' in (cfg/'Saves/serveradmin.xml').read_text(),'Native game-admin permission missing'
 print('PASS two engines, maps/modes/player limits, native admin IDs and wrong/correct console passwords',flush=True)
 # Allow the Windows LAN query/password checks before changing the first port.
 (test/'ready.json').write_text(json.dumps({'game':game,'instances':[{k:i[k] for k in ('id','port','map','mode','players')} for i in [first,second]]}))
 if '--lan-gate' in sys.argv:
  deadline=time.monotonic()+180
  while not (test/'lan-checked').exists() and time.monotonic()<deadline:time.sleep(5)
  assert (test/'lan-checked').exists(),'Windows LAN validation has not completed'
 stop(first);assert second['process'].poll() is None and second['adapter'].query(second['port']) is not None
 world=root/'worlds'/game/first['worldId'];assert any(world.rglob('*.bin')) or any(world.rglob('*.db')) or (world/'Saves').is_dir(),'World progress was not saved'
 resumed=launch(0,first['worldId'],first);ready([resumed]);assert resumed['worldId']==first['worldId'];assert second['adapter'].query(second['port']) is not None
 print('PASS independent stop and saved-world resume',flush=True);stop(resumed);stop(second)
 proof={'game':game,'twoInstancesReady':True,'maps':[first['map'],second['map']],'modes':[first['mode'],second['mode']],'playerLimits':[2,4],'adminPasswordRejectionVerified':True,'selectedNativeAdminVerified':game=='sevendays','independentStopVerified':True,'savedWorldResumeVerified':True,'ownedTestsStopped':True}
 (test/'result.json').write_text(json.dumps(proof,indent=2));print('RESULT',str(test/'result.json'),flush=True)
finally:
 for item in owned:
  if item['process'].poll() is None:
   try:stop(item)
   except Exception:print('Owned test needs cleanup:',item['id'],flush=True)
