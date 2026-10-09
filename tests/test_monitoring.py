"""Usage averages, durable settlement, owner limits and scoped network rules."""
import sys,tempfile,unittest,json,socket
from pathlib import Path
from collections import deque
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import portal,server_metrics,network_meter
class MonitorTests(unittest.TestCase):
 def test_cgroup_cpu_and_network_average(self):
  with tempfile.TemporaryDirectory() as d:
   group=Path(d);(group/'cpu.stat').write_text('usage_usec 5000000\n');m=server_metrics.EngineMeter.__new__(server_metrics.EngineMeter);m.group=group;m.run_id='a'*32;m.started=0;m.samples=deque([(0,0,0,0)])
   with patch.object(server_metrics.time,'monotonic',return_value=10),patch.object(server_metrics,'network',return_value={'rxBytes':10240,'txBytes':20480}):
    cpu,rx,tx,v=m.sample();self.assertEqual(v['cpuPercent'],50);self.assertEqual(v['cpuAveragePercent'],50);self.assertEqual(v['rxBytesPerSecond'],1024);self.assertEqual(v['txBytesPerSecond'],2048)
 def test_pending_usage_retries_same_counters_without_duplicate_debit(self):
  with tempfile.TemporaryDirectory() as d,patch.object(portal,'ROOT',Path(d)):
   data={'op':'credit-charge','runId':'a'*32,'cpuUs':100,'rxBytes':2,'txBytes':3};path=portal.pending_usage(data);self.assertEqual(path.stat().st_mode&0o777,0o600)
   with patch.object(portal,'call',side_effect=OSError('offline')):portal.settle_pending()
   self.assertTrue(path.exists())
   with patch.object(portal,'call',return_value={}) as call:portal.settle_pending();call.assert_called_once_with(data)
   self.assertFalse(path.exists())
 def test_exhausted_owner_stops_all_own_instances_only(self):
  saved=portal.instances
  try:
   portal.instances={key:{'meter':object(),'public':{'ownerId':owner}} for key,owner in [('a',2),('b',2),('c',3)]}
   def usage(ident,item):return {'limitReached':ident=='a'}
   with patch.object(portal,'settle_pending'),patch.object(portal,'sample_usage',side_effect=usage),patch.object(portal,'records',{k:{'public':v['public']} for k,v in portal.instances.items()}),patch.object(portal,'save_record'),patch.object(portal,'stop') as stop:
    portal.monitor_tick();self.assertEqual([x.args[0] for x in stop.call_args_list],['a','b'])
  finally:portal.instances=saved
 def test_scoped_counter_rules_validate_ports_and_have_no_verdict(self):
  saved=network_meter.entries;network_meter.entries={};ident='a'*32
  try:
   with patch.object(network_meter,'nft') as nft:
    network_meter.add(ident,[{'port':27015,'protocol':'udp'},{'port':28015,'protocol':'tcp'}]);commands=nft.call_args.args[0];self.assertIn('ip saddr',commands);self.assertIn('ip daddr',commands);self.assertIn('dport',commands);self.assertIn('sport',commands);self.assertNotIn(' accept',commands);self.assertNotIn(' drop',commands)
   for p in [{'port':22,'protocol':'tcp'},{'port':True,'protocol':'udp'},{'port':27015,'protocol':'udp; drop'}]:
    with self.assertRaises(ValueError):network_meter.add('b'*32,[p])
  finally:network_meter.entries=saved
if __name__=='__main__':unittest.main()
