"""Auth, IRC/browser sharing, mutation guards and rollback tests; no host topology changes."""
import importlib,ipaddress,json,os,secrets,socket,sys,tempfile,threading,time,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from admin_auth import Auth
from chat import Chat,IRC,IRCServer
import network_control as net
class Tests(unittest.TestCase):
    def test_forced_rotation_and_revocation(self):
        with tempfile.TemporaryDirectory() as d:
            auth=Auth(d);initial=(Path(d)/'initial-password.txt').read_text().strip();token,s=auth.login(initial,'test')
            self.assertTrue(s['mustChange'])
            with self.assertRaises(PermissionError):auth.session(token)
            with self.assertRaises(ValueError):auth.change(token,initial,'short')
            replacement='TestOnly-'+secrets.token_urlsafe(16);new,s=auth.change(token,initial,replacement)
            self.assertFalse(s['mustChange']);self.assertFalse((Path(d)/'initial-password.txt').exists())
            with self.assertRaises(PermissionError):auth.session(token,True)
            with self.assertRaises(PermissionError):auth.login(initial,'test')
            self.assertTrue(auth.session(new)['authenticated']);auth.logout(new)
            with self.assertRaises(PermissionError):auth.session(new)
    def test_chat_history_nicks_and_validation(self):
        with tempfile.TemporaryDirectory() as d:
            chat=Chat(d);a,_=chat.join('PlayerOne');b,_=chat.join('PlayerTwo')
            with self.assertRaises(ValueError):chat.join('playerone')
            with self.assertRaises(ValueError):chat.send(a,'newline\ninjection')
            text='<script>alert(1)</script> ; SELECT * FROM sessions'
            chat.send(a,text);self.assertEqual(chat.read(b)['messages'][0]['text'],text)
            with self.assertRaises(ValueError):chat.send(a,'too fast')
            self.assertEqual(Chat(d).read(b)['messages'][0]['text'],text);chat.leave(a)
            with self.assertRaises(PermissionError):chat.send(a,'expired')
    def test_real_irc_shares_web_history(self):
        with tempfile.TemporaryDirectory() as d:
            chat=Chat(d);web,_=chat.join('WebPlayer');server=IRCServer(('127.0.0.1',0),IRC);server.chat=chat
            auth=patch('chat.call',return_value={'id':91,'name':'IRCPlayer','token':'owned-test'});auth.start()
            threading.Thread(target=server.serve_forever,daemon=True).start()
            try:
                with socket.create_connection(server.server_address,timeout=3) as sock:
                    sock.sendall(b'PASS owned-code\r\nNICK IRCPlayer\r\nUSER irc 0 * :LAN Player\r\nJOIN #lan\r\nPRIVMSG #lan :Hello from IRC\r\n');time.sleep(.15)
                    self.assertEqual(chat.read(web)['messages'][-1]['text'],'Hello from IRC')
                    chat.send(web,'Hello from browser');data=b''
                    while b'Hello from browser' not in data:data+=sock.recv(8192)
                    self.assertIn(b'PRIVMSG #lan :Hello from browser',data);sock.sendall(b'QUIT\r\n')
            finally:server.shutdown();server.server_close();auth.stop()
    def test_gateway_preview_protects_management(self):
        with tempfile.TemporaryDirectory() as d:
            c=net.Controller(d)
            c.inventory=lambda:([{'name':'lan0','canUseForLAN':True},{'name':'lan1','canUseForLAN':True},{'name':'mgmt0','canUseForLAN':False}],'mgmt0',[])
            for request in [{'mode':'bridge','ports':['mgmt0','lan0']},{'mode':'bridge','ports':['lan0']},{'mode':'separate','ports':['lan0','lan1']},{'mode':'bridge','ports':['lan0','lan0']},{'mode':'bridge','ports':['lan0',';touch /tmp/pwned']}]:
                with self.assertRaises(ValueError):c.plan(request)
            plan=c.plan({'mode':'bridge','ports':['lan0','lan1']});self.assertIn('Bridge lan0, lan1',plan['summary']);self.assertFalse(c.state)
            with self.assertRaises(ValueError):c.apply({'plan':plan['plan'],'confirm':'NO'})
            with self.assertRaises(ValueError):c.dispatch({'op':'shell','command':'id'})
    def test_pending_rollback_restores_policy(self):
        with tempfile.TemporaryDirectory() as d:
            c=net.Controller(d);old={'lan':'lan0','wan':'wan0','internet':False,'blocked':[]};c.state={'lan':'lan1','wan':'wan0','internet':True,'blocked':[]}
            c.pending={'id':'test','expires':time.time()-1,'checkpoint':'/test','old':old,'new':c.state,'newIds':['fake-uuid'],'oldForward':'0'}
            calls=[];previous=net.run;net.run=lambda args,input=None,check=True:calls.append(args) or ''
            try:
                c.bus=lambda *args:calls.append(list(args));c.apply_filter=lambda config:calls.append(['filter',config]);c.route_rule=lambda *args:calls.append(['route',*args])
                self.assertTrue(c.rollback()['rolledBack']);self.assertEqual(c.state,old);self.assertIsNone(c.pending)
                self.assertIn(['filter',old],calls)
            finally:net.run=previous
    def test_blocking_is_forward_only(self):
        rule=net.nft_rules({'lan':'lan0','wan':'wan0','internet':False,'blocked':['aa:bb:cc:dd:ee:ff']})
        self.assertIn('hook forward',rule);self.assertNotIn('hook input',rule);self.assertNotIn('flush ruleset',rule)
        self.assertIn('meta nfproto ipv6 counter drop',rule);self.assertIn('ether saddr @blocked',rule)
        with self.assertRaises(ValueError):net.nft_rules({'lan':'evil";flush ruleset','wan':'wan0'})
if __name__=='__main__':unittest.main(verbosity=2)
