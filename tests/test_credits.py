"""Transactional credits, shared debt limits, retries and administrator exemption."""
import sys,tempfile,unittest,uuid
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from accounts import Accounts
import credits
from unittest.mock import patch
class CreditTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.a=Accounts(self.tmp.name,lookup=lambda ip:{'ip':ip,'mac':'00:11:22:33:44:55'});d={'ip':'192.168.8.2','mac':'00:11:22:33:44:55'}
  self.admin={'id':self.a.create('CreditAdmin','FixturePassword123',d,'admin'),'role':'admin'};self.player={'id':self.a.create('CreditPlayer','FixturePassword123',d),'role':'player'}
 def tearDown(self):self.tmp.cleanup()
 def add(self,amount,key=None):return self.a.manage_credits(self.admin,{'op':'add','id':self.player['id'],'amount':amount,'requestId':key or uuid.uuid4().hex})
 def run_id(self,ident=None):
  run=uuid.uuid4().hex;self.a.credit_authorize(ident or self.player['id'],run,'a'*12);return run
 def charge(self,run,cpu=0,rx=0,tx=0):return self.a.credit_charge({'runId':run,'cpuUs':cpu,'rxBytes':rx,'txBytes':tx,'serverId':'a'*12})
 def test_cpu_plus_network_and_idempotent_retry(self):
  self.add('4');run=self.run_id();v=self.charge(run,3600*1000000,1073741824//2,1073741824//2);self.assertEqual(v['chargedTokens'],2);self.assertEqual(v['creditTokenBalance'],2)
  self.assertEqual(self.charge(run,3600*1000000,1073741824//2,1073741824//2)['creditTokenBalance'],2)
  with self.assertRaises(ValueError):self.charge(run,0)
 def test_shared_balance_and_negative_limit_never_overdraw(self):
  with self.assertRaises(PermissionError):self.run_id()
  self.a.manage_credits(self.admin,{'op':'settings',**{'cpuMinutesPerToken':60,'networkGiBPerToken':1,'negativeLimit':2}})
  one=self.run_id();two=self.run_id();self.assertEqual(self.charge(one,3600*1000000)['creditTokenBalance'],-1)
  value=self.charge(two,7200*1000000);self.assertEqual(value['creditTokenBalance'],-2);self.assertTrue(value['limitReached']);self.assertEqual(value['chargedTokens'],1)
  with self.assertRaises(PermissionError):self.run_id()
  self.add(1);self.assertTrue(self.a.credit_status(self.player['id'])['canStartPaidServer'])
 def test_admin_free_and_role_changes_use_actual_owner(self):
  run=self.run_id(self.admin['id']);self.assertEqual(self.charge(run,999999999999,999999999999)['chargedTokens'],0)
  self.add(1);player_run=self.run_id()
  with self.a.db() as c:c.execute("UPDATE users SET role='admin' WHERE id=?",(self.player['id'],))
  self.assertTrue(self.charge(player_run,3600*1000000)['creditExempt']);self.assertEqual(self.a.credit_status(self.player['id'])['creditTokenBalance'],1)
 def test_topups_admin_only_idempotent_and_sessions_retained(self):
  key=uuid.uuid4().hex;self.add('2.123456',key);self.add('2.123456',key);self.assertEqual(self.a.credit_status(self.player['id'])['creditTokenBalance'],2.123456)
  with self.assertRaises(ValueError):self.add(3,key)
  for actor in [self.player]:
   with self.assertRaises(PermissionError):self.a.manage_credits(actor,{'op':'settings',**{'cpuMinutesPerToken':60,'networkGiBPerToken':1,'negativeLimit':1}})
  token,user=self.a.login('CreditPlayer','FixturePassword123','192.168.8.2');self.add(1);self.a.session(token,'192.168.8.2')
 def test_fractional_usage_carries_and_persistence(self):
  self.add(2);run=self.run_id()
  for i in range(1,3601):self.charge(run,i)
  self.assertEqual(self.a.credit_status(self.player['id'])['creditTokenBalance'],1.999999)
  other=Accounts(self.tmp.name,lookup=self.a.lookup);self.assertEqual(other.credit_status(self.player['id'])['creditTokenBalance'],1.999999)
  self.assertEqual(len(other.credit_status(self.player['id'],history=True)['usage']),1)
 def test_internal_billing_accepts_controller_not_engine_peer(self):
  with patch.object(credits,'_controller_pid',(0,0)),patch.object(credits.subprocess,'check_output',return_value=b'12345\n'):
   self.assertTrue(credits.controller_peer(0,999));self.assertTrue(credits.controller_peer(999,12345));self.assertFalse(credits.controller_peer(999,54321))
 def test_invalid_values_and_settings_changes(self):
  for x in [True,'NaN','Infinity',0,-1,'0.0000001',1000001]:
   with self.assertRaises(ValueError):self.add(x)
  self.add(3);run=self.run_id();self.charge(run,3600*1000000)
  self.a.manage_credits(self.admin,{'op':'settings','cpuMinutesPerToken':30,'networkGiBPerToken':1,'negativeLimit':0})
  self.assertEqual(self.charge(run,7200*1000000)['creditTokenBalance'],0)
  with self.assertRaises(ValueError):self.charge(run,True)
if __name__=='__main__':unittest.main()
