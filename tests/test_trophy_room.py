"""Confirmed medals, historical game labels, empty players and avatar recovery."""
import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from community import Store
from trophy_room import TrophyRoom
A={'id':1,'name':'Admin','role':'admin'}
class TrophyTests(unittest.TestCase):
 def setUp(self):
  self.folder=tempfile.TemporaryDirectory();self.store=Store(self.folder.name,lambda:1000)
 def tearDown(self):self.folder.cleanup()
 def award(self,game,label,user,rank,status='final'):
  poll=self.store.create(A,{'name':label+' Cup','games':[game,'alternative'],'deadline':1100,'start':1200},{game:label,'alternative':'Alternative Game'})
  with self.store.db() as c:
   c.execute('UPDATE polls SET status=?,winner=? WHERE id=?',(status,game,poll));c.execute('INSERT INTO awards VALUES(?,?,?,?,?)',(poll,user,rank,99,1000))
  return poll
 def test_multiple_medals_and_game_labels_survive_restart(self):
  self.award('quakelive','Quake Live',2,1);self.award('sof2','Soldier of Fortune II Gold',2,2);self.award('old-game','Historical Game',2,3);self.award('quakelive','Quake Live',3,1)
  self.award('not-final','Pending Game',2,1,'ready')
  reopened=Store(self.folder.name)
  self.assertEqual(reopened.medal_totals(),{2:{'gold':1,'silver':1,'bronze':1},3:{'gold':1,'silver':0,'bronze':0}})
  self.assertEqual({p['gameName'] for p in reopened.trophies(2)},{'Quake Live','Soldier of Fortune II Gold','Historical Game'})
  self.assertEqual(len(reopened.trophies(2)),3)
 def test_zero_medal_players_sorting_avatar_cache_and_no_private_fields(self):
  self.award('quake','Quake Live',2,1);calls=[]
  class Service:
   def forum(self,data):calls.append(data);return {'avatars':{'2':'/forum/custom_avatar/player.png'}}
  room=TrophyRoom(self.store,Service(),lambda:1000)
  users=[{'id':1,'name':'Admin','created':900,'ip':'private'},{'id':2,'name':'Winner','created':800},{'id':3,'name':'Empty','created':800}]
  rows=room.listing(users)['users'];self.assertEqual([p['id'] for p in rows],[2,1,3]);self.assertEqual(rows[0]['avatar'],'/forum/custom_avatar/player.png');self.assertEqual(rows[1]['gold'],0)
  self.assertEqual(set(rows[0]),{'id','name','avatar','gold','silver','bronze'});room.listing(users);self.assertEqual(len(calls),1)
 def test_forum_failure_keeps_medals_and_recovers(self):
  self.award('quake','Quake Live',1,1)
  class Service:
   fail=True
   def forum(self,data):
    if self.fail:raise OSError('Offline')
    return {'avatars':{}}
  svc=Service();room=TrophyRoom(self.store,svc)
  data=room.listing([{'id':1,'name':'Admin'}]);self.assertFalse(data['avatarsAvailable']);self.assertEqual(data['users'][0]['gold'],1)
  svc.fail=False;self.assertTrue(room.listing([{'id':1,'name':'Admin'}])['avatarsAvailable'])
if __name__=='__main__':unittest.main()
