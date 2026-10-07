"""Room migration/isolation, authenticated API and IRC/browser integration."""
import importlib,json,sqlite3,socket,sys,tempfile,threading,time,unittest
from pathlib import Path
from unittest.mock import patch
from urllib.request import Request,urlopen
from urllib.error import HTTPError
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from chat import Chat,IRC,IRCServer
class Tests(unittest.TestCase):
    def test_legacy_history_migrates_once(self):
        with tempfile.TemporaryDirectory() as d:
            with sqlite3.connect(Path(d)/'chat.sqlite3') as c:
                c.execute('CREATE TABLE messages(id INTEGER PRIMARY KEY AUTOINCREMENT,nick TEXT,text TEXT,at REAL)')
                c.execute('INSERT INTO messages VALUES(17,?,?,?)',('OldPlayer','Original chat',time.time()))
            c.close()
            chat=Chat(d);token,_=chat.join('Reader')
            self.assertEqual(chat.read(token)['messages'][0]['id'],17)
            self.assertEqual(chat.read(token)['messages'][0]['room'],'general')
            self.assertEqual(chat.read(token,room='shooter')['messages'],[])
            self.assertEqual(Chat(d).read(token)['messages'][0]['text'],'Original chat')
    def test_room_history_cursor_and_presence(self):
        with tempfile.TemporaryDirectory() as d:
            chat=Chat(d);a,_=chat.join('Alpha');b,_=chat.join('Bravo')
            general=chat.send(a,'General only')['sent'];chat.send(b,'Shooter only','shooter')
            self.assertEqual([m['text'] for m in chat.read(a)['messages']],['General only'])
            self.assertEqual(chat.read(a)['online'],['Alpha'])
            self.assertEqual(chat.read(b,room='shooter')['online'],['Bravo'])
            self.assertEqual(chat.read(a,since=general)['messages'],[])
            self.assertEqual(chat.read(a,room='strategy')['messages'],[])
            self.assertEqual(chat.read(b,room='general')['online'],['Bravo'])
            self.assertEqual(Chat(d).read(a,room='shooter')['messages'][0]['text'],'Shooter only')
    def test_invalid_rooms_and_rate_limit_across_rooms(self):
        with tempfile.TemporaryDirectory() as d:
            chat=Chat(d);a,_=chat.join('Alpha')
            for room in ['random',None,[],"general' OR 1=1"]:
                with self.assertRaises(ValueError):chat.read(a,room=room)
                with self.assertRaises(ValueError):chat.send(a,'Hello',room)
            chat.send(a,'First','general')
            with self.assertRaises(ValueError):chat.send(a,'Flood','strategy')
            self.assertEqual(chat.read(a,room='strategy')['messages'],[])
    def test_room_retention_does_not_delete_other_rooms(self):
        with tempfile.TemporaryDirectory() as d:
            chat=Chat(d);a,_=chat.join('Alpha');chat.send(a,'Quiet room','general');chat.rate.clear()
            with chat.db() as c:c.executemany('INSERT INTO messages(nick,text,at,room) VALUES(?,?,?,?)',[('Alpha',str(i),time.time(),'shooter') for i in range(1100)])
            chat.send(a,'Newest','shooter')
            self.assertEqual(chat.read(a,room='general')['messages'][0]['text'],'Quiet room')
            with chat.db() as c:self.assertEqual(c.execute("SELECT count(*) FROM messages WHERE room='shooter'").fetchone()[0],1000)
    def test_irc_leaving_preserves_same_account_browser(self):
        with tempfile.TemporaryDirectory() as d:
            chat=Chat(d);token=chat.account({'id':1,'name':'Alpha'})
            chat.read(token,room='general');chat.read(token,room='shooter',source='irc-owned')
            chat.leave(token,'irc-owned')
            self.assertEqual(chat.read(token)['online'],['Alpha'])
            self.assertEqual(chat.identity(token),'Alpha')
    def test_authenticated_irc_rooms_share_only_matching_history(self):
        with tempfile.TemporaryDirectory() as d:
            chat=Chat(d);web=chat.account({'id':3,'name':'WebPlayer'});server=IRCServer(('127.0.0.1',0),IRC);server.chat=chat
            def account(data):
                if data['op']=='irc-login' and data.get('name')=='IRCPlayer' and data.get('code')=='test-code':return {'id':1,'name':'IRCPlayer','token':'test-session'}
                if data['op']=='session' and data.get('token')=='test-session':return {'id':1,'name':'IRCPlayer'}
                raise PermissionError('Invalid code')
            def receive(sock,needle):
                data=b''
                while needle not in data:
                    part=sock.recv(8192)
                    if not part:raise AssertionError('IRC closed early')
                    data+=part
                return data
            with patch('chat.call',side_effect=account):
                threading.Thread(target=server.serve_forever,daemon=True).start()
                try:
                    with socket.create_connection(server.server_address,timeout=3) as sock:
                        sock.sendall(b'PASS test-code\r\nNICK IRCPlayer\r\nUSER irc 0 * :LAN Player\r\nJOIN #shooter\r\n')
                        receive(sock,b'366 IRCPlayer #shooter')
                        chat.send(web,'Browser shooter','shooter');self.assertIn(b'PRIVMSG #shooter :Browser shooter',receive(sock,b'Browser shooter'))
                        sock.sendall(b'PRIVMSG #shooter :IRC shooter\r\nPING :barrier\r\n');receive(sock,b'PONG lisp :barrier')
                        self.assertEqual(chat.read(web,room='shooter')['messages'][-1]['text'],'IRC shooter')
                        self.assertEqual(chat.read(web,room='strategy')['messages'],[])
                        sock.sendall(b'PRIVMSG #strategy :Do not save\r\n');self.assertIn(b'442 IRCPlayer #strategy',receive(sock,b'Join this room first'))
                        sock.sendall(b'JOIN #strategy\r\nPART #shooter\r\nPING :parted\r\n');receive(sock,b'PONG lisp :parted')
                        self.assertNotIn('IRCPlayer',chat.read(web,room='shooter')['online'])
                        self.assertIn('IRCPlayer',chat.read(web,room='strategy')['online'])
                        sock.sendall(b'JOIN #lan\r\n');self.assertIn(b'JOIN #lan',receive(sock,b'366 IRCPlayer #lan'))
                        sock.sendall(b'QUIT\r\n')
                    with socket.create_connection(server.server_address,timeout=3) as sock:
                        sock.sendall(b'NICK Stranger\r\nUSER irc 0 * :LAN Player\r\n');self.assertIn(b'464',receive(sock,b'464'))
                finally:server.shutdown();server.server_close()
    def test_api_auth_room_validation_and_isolation(self):
        with tempfile.TemporaryDirectory() as d:
            chat=Chat(d)
            with patch('chat.Chat',return_value=chat):module=importlib.import_module('chat_server')
            def check(headers,write=False):
                if headers.get('Cookie')!='lisp_session=test' or (write and headers.get('X-CSRF-Token')!='test-csrf'):raise PermissionError('Log in first')
                return {'id':7,'name':'APIPlayer'}
            server=module.ThreadingHTTPServer(('127.0.0.1',0),module.Handler)
            base='http://127.0.0.1:'+str(server.server_address[1])
            def req(path,data=None,authenticated=True):
                headers={'X-Forwarded-Proto':'https','X-LAN-Request':'1','Content-Type':'application/json'}
                if authenticated:headers.update(Cookie='lisp_session=test',**{'X-CSRF-Token':'test-csrf'})
                return json.load(urlopen(Request(base+path,json.dumps(data).encode() if data is not None else None,headers=headers),timeout=3))
            with patch.object(module,'CHAT',chat),patch.object(module,'check',side_effect=check):
                threading.Thread(target=server.serve_forever,daemon=True).start()
                try:
                    for room in ['general','shooter','strategy']:
                        with self.assertRaises(HTTPError) as error:req('/api/chat?room='+room,authenticated=False)
                        self.assertEqual(error.exception.code,401)
                    with self.assertRaises(HTTPError) as error:req('/api/chat/message',{'room':'strategy','text':'Denied'},False)
                    self.assertEqual(error.exception.code,401)
                    req('/api/chat/message',{'room':'strategy','text':'Strategy API'})
                    self.assertEqual(req('/api/chat?room=strategy')['messages'][0]['text'],'Strategy API')
                    self.assertEqual(req('/api/chat?room=shooter')['messages'],[])
                    self.assertEqual(req('/api/chat')['room'],'general')
                    for path,data in [('/api/chat?room=bad',None),('/api/chat/message',{'room':'bad','text':'No'}),('/api/chat/message',{'room':None,'text':'No'})]:
                        with self.assertRaises(HTTPError) as error:req(path,data)
                        self.assertEqual(error.exception.code,400)
                finally:server.shutdown();server.server_close()
if __name__=='__main__':unittest.main(verbosity=2)
