import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from personal_status import next_matches,PersonalStatus

def match(ident,start='2030-01-01T12:00:00Z',team=8,score=0):
 return {'id':ident,'start_time':start,'stage_item_input1_score':score,'stage_item_input2_score':0,'stage_item_input1':{'team_id':team,'team':{'name':'Player'}},'stage_item_input2':{'team_id':9,'team':{'name':'Opponent'}}}
def stages(matches,draft=False):return {'data':[{'stage_items':[{'rounds':[{'is_draft':draft,'matches':matches}]}]}]}
POLL={'id':1,'name':'LAN Cup','status':'ready','bracket':7,'participants':[{'user':2,'team':8}]}
class PersonalTests(unittest.TestCase):
 def test_own_next_match_sorted_and_linked(self):
  rows=next_matches([POLL],2,lambda path:stages([match(2,'2030-01-02T12:00:00Z'),match(1)]),0)
  self.assertEqual([x['matchId'] for x in rows],[1,2]);self.assertEqual(rows[0]['opponent'],'Opponent');self.assertEqual(rows[0]['url'],'/bracket/tournaments/7/dashboard')
 def test_admin_does_not_get_other_players_matches(self):
  self.assertEqual(next_matches([POLL],1,lambda _:self.fail('Not your tournament'),0),[])
 def test_completed_past_draft_unscheduled_and_other_teams_excluded(self):
  self.assertEqual(next_matches([POLL],2,lambda _:stages([match(1,score=2),match(2,'2000-01-01T12:00:00Z'),match(3,None),match(4,team=99)]),1800000000),[])
  self.assertEqual(next_matches([POLL],2,lambda _:stages([match(1)],True),0),[])
 def test_cancelled_and_final_excluded(self):
  for status in ('cancelled','final','open'):
   self.assertEqual(next_matches([{**POLL,'status':status}],2,lambda _:self.fail('Not active'),0),[])
 def test_cache_is_personal_and_recovers_unavailable_services(self):
  now=[0];calls=[]
  class Store:
   def view(self,user):return []
  class Services:
   fail=False
   def forum(self,data):
    calls.append(data['user']['id'])
    if self.fail:raise OSError('Unavailable')
    return {'avatar':None,'unreadMessages':data['user']['id'],'unreadTopics':0}
   def api(self,path):raise AssertionError('No tournaments')
  svc=Services();status=PersonalStatus(Store(),svc,lambda:now[0]);a={'id':1,'name':'Admin','role':'admin'};b={'id':2,'name':'Player','role':'player'}
  self.assertEqual(status.get(a)['unreadMessages'],1);self.assertEqual(status.get(b)['unreadMessages'],2);status.get(a);self.assertEqual(calls,[1,2])
  now[0]=26;svc.fail=True;self.assertFalse(status.get(a)['forumAvailable']);self.assertIsNone(status.get(a)['unreadMessages'])
  now[0]=52;svc.fail=False;self.assertEqual(status.get(a)['unreadMessages'],1)
if __name__=='__main__':unittest.main()
