"""Durable ownership, six slots, safe stopping, restart and cold-load recovery."""
import importlib.util,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import adapters,portal
OWNER={'id':2,'name':'Owner','role':'player','ip':'192.168.8.2'}
OTHER={'id':3,'name':'Other','role':'player','ip':'192.168.8.3'}
ADMIN={'id':1,'name':'Admin','role':'admin','ip':'192.168.8.1'}
class Process:
 pid=123456789
 returncode=None
 def poll(self):return self.returncode
 def wait(self,timeout=None):self.returncode=0;return 0
class FakeAdapter:
 id='test';name='Fixture';engine='fixture'
 def modes(self):return {'coop':'Co-op'}
 def maps(self):return ['Map']
 def players(self,mode):return [2]
 def mutators(self):return {}
 def reserved_ports(self,port):return [(port,portal.socket.SOCK_DGRAM)]
 def prepare_request(self,home,port,mode,level,players,password,admin,ids,mutators,data):
  ident=home.name if data.get('world','new')=='new' else data['world'];world=portal.ROOT/'worlds'/ident;world.mkdir(parents=True,exist_ok=True)
  (world/'save.bin').touch();self.world=ident;return ['/bin/true'],home
 def public_details(self):return {'worldId':self.world,'worldName':'Fixture world','persistentWorld':True}
 def query(self,port):return {'clients':0,'mapname':'Map'}
 def stop_process(self,proc):proc.wait()
 def after_stop(self):pass
class LifecycleTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);portal.ROOT=self.root;portal.RECORDS=self.root/'records';portal.records={};portal.instances={};portal.deleted_records={};portal.DELETED=self.root/'deleted-records';portal.PORTS=range(45000,45036)
  self.registry=patch.object(portal,'registry',side_effect=lambda:{'test':FakeAdapter()});self.registry.start();self.proc=patch.object(portal.subprocess,'Popen',side_effect=lambda *a,**k:Process());self.proc.start()
 def tearDown(self):
  for ident in list(portal.instances):portal.stop(ident,ADMIN)
  self.registry.stop();self.proc.stop();self.tmp.cleanup()
 def start(self,actor=OWNER):return portal.start({'game':'test','mode':'coop','map':'Map','players':2,'password':'JoinFixture123','adminPassword':'AdminFixture123'},actor)
 def test_six_active_slots_and_stopped_records_do_not_consume_slots(self):
  self.assertEqual(portal.MAX_SERVERS,6);ids=[self.start()['id'] for _ in range(6)]
  with self.assertRaises(ValueError):self.start()
  portal.stop(ids[0],OWNER);self.assertEqual(next(s for s in portal.listing(OWNER) if s['id']==ids[0])['status'],'stopped');self.assertEqual(len(portal.records),6)
  self.assertEqual(portal.restart(ids[0],OWNER)['id'],ids[0]);self.assertEqual(len(portal.instances),6)
  self.assertTrue((self.root/'worlds'/ids[0]/'save.bin').exists());self.assertEqual(len({s['port'] for s in portal.listing(OWNER)}),6)
 def test_stop_restart_owner_guards_and_admin_preserves_creator(self):
  ident=self.start()['id']
  for action in [portal.stop,portal.restart]:
   with self.assertRaises(PermissionError):action(ident,OTHER)
  portal.stop(ident,OWNER);row=portal.listing(OTHER)[0];self.assertFalse(row['canStop']);self.assertFalse(row['canRestart'])
  with self.assertRaises(PermissionError):portal.restart(ident,OTHER)
  portal.restart(ident,ADMIN);self.assertEqual(portal.listing(OWNER)[0]['ownerId'],OWNER['id']);self.assertEqual(portal.records[ident]['launch']['world'],ident)
 def test_private_presets_survive_cold_controller_load_without_auto_start(self):
  ident=self.start()['id'];portal.stop(ident,OWNER);p=portal.RECORDS/(ident+'.json');self.assertEqual(p.stat().st_mode&0o777,0o600)
  with patch.object(adapters,'ROOT',self.root):
   spec=importlib.util.spec_from_file_location('cold_portal',portal.__file__);cold=importlib.util.module_from_spec(spec);spec.loader.exec_module(cold)
  self.assertEqual(cold.instances,{});row=cold.listing(OWNER)[0];self.assertEqual(row['id'],ident);self.assertEqual(row['status'],'stopped');self.assertTrue(row['canRestart']);self.assertNotIn('launch',row)
  self.assertNotIn('AdminFixture123',json.dumps(row));self.assertNotIn('JoinFixture123',json.dumps(row))
 def test_explicit_restart_preserves_only_stale_instance_logs(self):
  ident=self.start()['id'];portal.stop(ident,OWNER);home=self.root/'instances'/ident;home.mkdir();(home/'server.log').write_text('Retained fixture log')
  portal.restart(ident,OWNER)
  self.assertTrue(any((self.root/'retired-instances').glob(ident+'-*/server.log')))
  self.assertTrue((self.root/'worlds'/ident/'save.bin').exists())
  portal.stop(ident,OWNER);home.mkdir()
  class LiveCommand:
   def read_bytes(self):return b'/usr/bin/engine'+str(home).encode()
  with patch('pathlib.Path.glob',return_value=[LiveCommand()]):
   with self.assertRaises(ValueError):portal.restart(ident,OWNER)
  self.assertTrue(home.exists())
 def test_delete_restore_owner_guards_and_world_preservation(self):
  ident=self.start()['id']
  with self.assertRaises(PermissionError):portal.delete_entry(ident,OTHER)
  with self.assertRaises(ValueError):portal.delete_entry(ident,OWNER)
  portal.stop(ident,OWNER);portal.delete_entry(ident,OWNER)
  self.assertEqual(portal.listing(OWNER),[]);self.assertEqual(portal.deleted_listing(OTHER),[])
  self.assertTrue((self.root/'worlds'/ident/'save.bin').exists())
  self.assertNotIn('AdminFixture123',json.dumps(portal.deleted_listing(OWNER)))
  with self.assertRaises(PermissionError):portal.restore_entry(ident,OTHER)
  portal.restore_entry(ident,ADMIN);self.assertEqual(portal.listing(OWNER)[0]['status'],'stopped')
  self.assertEqual(portal.listing(OWNER)[0]['ownerId'],OWNER['id']);portal.restart(ident,OWNER)
 def test_record_write_failure_does_not_leave_an_untracked_engine(self):
  with patch.object(portal,'save_record',side_effect=OSError('Fixture disk unavailable')):
   with self.assertRaises(OSError):self.start()
  self.assertEqual(portal.instances,{})
if __name__=='__main__':unittest.main()
