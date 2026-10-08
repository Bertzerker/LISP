"""Expiry removes history in every room, including during idle maintenance."""
import sys,tempfile,time,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from chat import Chat,ROOMS

class ExpiryTests(unittest.TestCase):
 def test_boundary_and_other_rooms(self):
  with tempfile.TemporaryDirectory() as folder:
   chat=Chat(folder);now=time.time()
   with chat.db() as c:
    for room in ROOMS:
     c.executemany('INSERT INTO messages(nick,text,at,room) VALUES(?,?,?,?)',[('Player','expired',now-7201,room),('Player','boundary',now-7200,room),('Player','recent',now-7199,room)])
   chat.expire(now)
   with chat.db() as c:self.assertEqual(c.execute('SELECT text,room FROM messages ORDER BY room').fetchall(),[('recent',r) for r in sorted(ROOMS)])
 def test_read_deletes_history_and_startup_prunes_idle_rooms(self):
  with tempfile.TemporaryDirectory() as folder:
   chat=Chat(folder);token,_=chat.join('Player')
   with chat.db() as c:
    c.execute('INSERT INTO messages(nick,text,at,room) VALUES(?,?,?,?)',('Player','old',time.time()-7201,'strategy'))
    c.execute('INSERT INTO messages(nick,text,at,room) VALUES(?,?,?,?)',('Player','new',time.time(),'general'))
   self.assertEqual([m['text'] for m in chat.read(token)['messages']],['new'])
   with chat.db() as c:self.assertEqual(c.execute('SELECT count(*) FROM messages').fetchone()[0],1)
   with chat.db() as c:c.execute('UPDATE messages SET at=?',(time.time()-7201,))
   reopened=Chat(folder)
   with reopened.db() as c:self.assertEqual(c.execute('SELECT count(*) FROM messages').fetchone()[0],0)

if __name__=='__main__':unittest.main()
