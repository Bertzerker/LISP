"""Vote isolation, deadline races, recovery and duplicate-proof trophies."""
import sys,tempfile,unittest,threading
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from community import Store,Worker
A={'id':1,'name':'Admin','role':'admin'};P={'id':2,'name':'Player','role':'player'}
class CommunityTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.now=1000;self.s=Store(self.tmp.name,lambda:self.now)
        self.id=self.s.create(A,{'name':'LAN Cup','games':['quake','sof2'],'deadline':1100,'start':1200},{'quake':'Quake','sof2':'SoF2'})
    def tearDown(self):self.tmp.cleanup()
    def test_player_cannot_manage(self):
        with self.assertRaises(PermissionError):self.s.close(P,self.id)
        with self.assertRaises(PermissionError):self.s.create(P,{}, {})
    def test_one_vote_changes_and_persists(self):
        self.s.vote(P,self.id,'quake');self.s.vote(P,self.id,'sof2');self.s.vote(P,self.id,'sof2')
        row=self.s.view(P)[0];self.assertEqual(row['myVote'],'sof2');self.assertEqual(sum(o['votes'] for o in row['options']),1)
        self.assertEqual(Store(self.tmp.name,lambda:self.now).view(P)[0]['myVote'],'sof2')
    def test_invalid_game_and_deadline(self):
        with self.assertRaises(ValueError):self.s.vote(P,self.id,'forged')
        self.now=1100
        with self.assertRaises(ValueError):self.s.vote(P,self.id,'quake')
        self.s.due();self.assertEqual(self.s.view()[0]['status'],'choice')
    def test_tie_requires_admin_and_no_vote_overwrite(self):
        self.s.vote(P,self.id,'quake');self.s.vote(A,self.id,'sof2');self.now=1100;self.s.due()
        self.assertEqual(self.s.view()[0]['status'],'choice');self.s.close(A,self.id,'quake');self.s.close(A,self.id,'sof2')
        self.assertEqual(self.s.view()[0]['winner'],'quake')
        with self.s.db() as c:self.assertEqual(c.execute("SELECT count(*) FROM outbox WHERE op='create'").fetchone()[0],1)
    def test_concurrent_votes_do_not_duplicate(self):
        threads=[threading.Thread(target=self.s.vote,args=(P,self.id,'quake')) for _ in range(10)]
        for t in threads:t.start()
        for t in threads:t.join()
        self.assertEqual(sum(o['votes'] for o in self.s.view()[0]['options']),1)
    def test_latest_publication_survives_old_completion(self):
        job=self.s.pending();self.s.vote(P,self.id,'quake');self.s.completed(job);self.assertIsNotNone(self.s.pending())
        job=self.s.pending();self.s.failed(job);self.assertIsNone(self.s.pending());self.now+=11;self.assertIsNotNone(self.s.pending())
    def test_finalization_validates_mapping_and_is_idempotent(self):
        with self.s.db() as c:
            c.execute("UPDATE polls SET status='ready',bracket=99 WHERE id=?",(self.id,));c.execute('INSERT INTO participants VALUES(?,?,?,?,?)',(self.id,2,'Player',7,8))
        teams=[{'id':8,'player_ids':[7]},{'id':9,'player_ids':[999]}]
        with self.assertRaises(ValueError):self.s.finalize(A,self.id,[9],teams)
        with self.assertRaises(PermissionError):self.s.finalize(P,self.id,[8],teams)
        self.s.finalize(A,self.id,[8],teams);self.s.finalize(A,self.id,[8],teams)
        self.assertEqual(len(self.s.trophies(2)),1);self.assertEqual(self.s.trophies(2)[0]['rank'],1)
    def test_delete_with_no_players_then_restore(self):
        with self.assertRaises(PermissionError):self.s.cancel(P,self.id)
        self.s.cancel(A,self.id);self.s.cancel(A,self.id)
        self.assertEqual(self.s.view(),[]);p=self.s.view(ident=self.id)[0]
        self.assertEqual(p['status'],'cancelled');self.assertEqual(self.s.trophies(P['id']),[])
        self.now=1200;self.s.due();self.assertEqual(self.s.view(ident=self.id)[0]['status'],'cancelled')
        with self.assertRaises(ValueError):self.s.vote(P,self.id,'quake')
        with self.assertRaises(PermissionError):self.s.restore(P,self.id)
        self.s.restore(A,self.id);self.s.due();self.assertEqual(self.s.view()[0]['status'],'choice')
    def test_delete_one_player_blocks_work_and_keeps_roster(self):
        with self.s.db() as c:
            c.execute("UPDATE polls SET status='ready',bracket=99 WHERE id=?",(self.id,));c.execute('INSERT INTO participants VALUES(?,?,?,?,?)',(self.id,2,'Player',7,8))
        self.s.cancel(A,self.id)
        with self.assertRaises(ValueError):self.s.signup(P,self.id)
        with self.assertRaises(ValueError):self.s.finalize(A,self.id,[8],[{'id':8,'players':[{'id':7}]}])
        class Offline:
            def tournament(self,p):raise AssertionError('Deleted event must not be created')
        Worker(self.s,Offline()).process({'poll':self.id,'op':'create'})
        self.assertEqual(len(self.s.view(ident=self.id)[0]['participants']),1)
        self.s.restore(A,self.id);self.assertEqual(self.s.view()[0]['status'],'ready')
    def test_restore_purged_native_bracket_rebuilds_player_mapping(self):
        with self.s.db() as c:
            c.execute("UPDATE polls SET status='ready',bracket=99 WHERE id=?",(self.id,));c.execute('INSERT INTO participants VALUES(?,?,?,?,?)',(self.id,2,'Player',7,8))
        self.s.cancel(A,self.id);self.s.restore(A,self.id,native_missing=True)
        p=self.s.view()[0];self.assertEqual(p['status'],'preparing');self.assertIsNone(p['bracket']);self.assertEqual(p['participants'][0]['name'],'Player');self.assertIsNone(p['participants'][0]['team'])
    def test_confirmed_trophies_cannot_be_deleted(self):
        with self.s.db() as c:
            c.execute("UPDATE polls SET status='ready',bracket=99 WHERE id=?",(self.id,));c.execute('INSERT INTO participants VALUES(?,?,?,?,?)',(self.id,2,'Player',7,8))
        self.s.finalize(A,self.id,[8],[{'id':8,'players':[{'id':7}]}])
        with self.assertRaises(ValueError):self.s.cancel(A,self.id)
        self.assertEqual(len(self.s.trophies(2)),1)
    def test_workers_recover_bracket_and_forum_failures(self):
        class Fake:
            config={'host':'lan'}
            def __init__(self):self.fail=True;self.created=[];self.posts=[]
            def tournament(self,p):self.created.append(p['id']);return 99
            def forum(self,data):
                if self.fail:raise OSError('offline')
                self.posts.append(data);return {'topic':12}
        f=Fake();w=Worker(self.s,f);self.s.vote(P,self.id,'quake');self.now=1100;w.tick();f.fail=False;self.now+=11;w.tick()
        p=self.s.view()[0];self.assertEqual((p['status'],p['bracket'],p['thread']),('ready',99,12));self.assertEqual(f.created,[self.id]);self.assertTrue(any(x['event']=='result' for x in f.posts));self.assertIsNone(self.s.pending())
if __name__=='__main__':unittest.main()
