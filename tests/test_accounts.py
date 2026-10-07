"""Account binding, credential resets, revocation and forum authorization."""
import sys,tempfile,unittest,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from accounts import Accounts
from accounts import interface
from unittest.mock import patch
import json
class InterfaceTests(unittest.TestCase):
    def test_same_player_on_two_server_interfaces_uses_routed_device(self):
        rows=[{'dst':'192.168.8.2','lladdr':'00:11:22:33:44:02','dev':dev,'state':['STALE']} for dev in ['wlan0','enp3s0','enp3s0']]
        def output(command,**kwargs):
            return json.dumps([{'dev':'enp3s0'}] if command[2]=='route' else rows).encode()
        with patch('accounts.subprocess.check_output',side_effect=output):
            self.assertEqual(interface('192.168.8.2')['interface'],'enp3s0')
    def test_routed_client_still_rejected(self):
        with patch('accounts.subprocess.check_output',return_value=b'[{"dev":"enp3s0","gateway":"192.168.8.1"}]'):
            with self.assertRaises(PermissionError):interface('192.168.8.2')
class AccountTests(unittest.TestCase):
    def test_community_profiles_and_forum_password_recheck(self):
        users=self.a.community_users();self.assertEqual(set(users[0]),{'id','name','created'})
        self.assertTrue(self.a.verify_forum_password(self.player,'PlayerPassword123')['verified'])
        self.assertFalse(self.a.verify_forum_password(self.player,'WrongPassword123')['verified'])
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.devices={'192.168.8.2':{'ip':'192.168.8.2','mac':'00:11:22:33:44:02'},'192.168.8.3':{'ip':'192.168.8.3','mac':'00:11:22:33:44:03'}}
        self.a=Accounts(self.tmp.name,lookup=lambda ip:self.devices[ip]);self.a.create('HostAdmin','AdminPassword123',self.devices['192.168.8.2'],'admin');self.a.create('PlayerTwo','PlayerPassword123',self.devices['192.168.8.3'])
        self.at,self.admin=self.a.login('HostAdmin','AdminPassword123','192.168.8.2');self.pt,self.player=self.a.login('PlayerTwo','PlayerPassword123','192.168.8.3')
    def tearDown(self):self.tmp.cleanup()
    def test_interface_and_cookie_binding(self):
        with self.assertRaises(PermissionError):self.a.session(self.pt,'192.168.8.2')
        with self.assertRaises(PermissionError):self.a.login('PlayerTwo','PlayerPassword123','192.168.8.2')
        self.devices['192.168.8.3']['mac']='00:11:22:33:44:99'
        with self.assertRaises(PermissionError):self.a.session(self.pt,'192.168.8.3')
        self.a.manage(self.admin,{'op':'bind','id':self.player['id'],'ip':'192.168.8.3'})
        with self.assertRaises(PermissionError):self.a.session(self.pt,'192.168.8.3')
        _,user=self.a.login('PlayerTwo','PlayerPassword123','192.168.8.3');self.assertEqual(user['mac'],'00:11:22:33:44:99')
    def test_permissions_csrf_and_reset(self):
        with self.assertRaises(PermissionError):self.a.session(self.pt,'192.168.8.3',csrf='forged')
        with self.assertRaises(PermissionError):self.a.session(self.pt,'192.168.8.3',admin=True)
        with self.assertRaises(PermissionError):self.a.manage(self.player,{'op':'reset','id':self.admin['id'],'password':'ForgedPassword123'})
        self.a.manage(self.admin,{'op':'reset','id':self.player['id'],'password':'TemporaryPassword123'})
        with self.assertRaises(PermissionError):self.a.session(self.pt,'192.168.8.3')
        token,user=self.a.login('PlayerTwo','TemporaryPassword123','192.168.8.3');self.assertTrue(user['mustChange'])
        with self.assertRaises(PermissionError):self.a.session(token,'192.168.8.3')
        token,user=self.a.change(user,'TemporaryPassword123','NewPlayerPassword123','192.168.8.3');self.assertFalse(user['mustChange']);self.a.session(token,'192.168.8.3')
    def test_disable_roles_and_last_admin(self):
        with self.assertRaises(ValueError):self.a.manage(self.admin,{'op':'enabled','id':self.admin['id'],'enabled':False})
        self.a.manage(self.admin,{'op':'enabled','id':self.player['id'],'enabled':False})
        with self.assertRaises(PermissionError):self.a.session(self.pt,'192.168.8.3')
        self.a.manage(self.admin,{'op':'enabled','id':self.player['id'],'enabled':True});self.a.manage(self.admin,{'op':'role','id':self.player['id'],'role':'admin'})
        with self.assertRaises(PermissionError):self.a.session(self.pt,'192.168.8.3')
    def test_forum_persistence_and_moderation(self):
        self.assertEqual([b['name'] for b in self.a.boards()],['General','Games','Servers','Tools','Emulators'])
        topic=self.a.post(self.player,{'op':'topic','board':2,'title':'LAN match','body':'<script>plain text only</script>'})['topic']
        other=Accounts(self.tmp.name,lookup=lambda ip:self.devices[ip]);self.assertEqual(other.topic(topic)['posts'][0]['body'],'<script>plain text only</script>')
        with self.assertRaises(PermissionError):self.a.post(self.player,{'op':'lock','topic':topic,'locked':True})
        self.a.post(self.admin,{'op':'reply','topic':topic,'body':'Ready to play'});self.assertEqual(len(self.a.topic(topic)['posts']),2)
        self.a.post(self.admin,{'op':'lock','topic':topic,'locked':True});self.a.post_times.clear()
        with self.assertRaises(ValueError):self.a.post(self.player,{'op':'reply','topic':topic,'body':'Must fail'})
        self.a.post(self.admin,{'op':'delete','topic':topic})
        with self.assertRaises(ValueError):self.a.topic(topic)
    def test_irc_code_is_single_use_and_bound(self):
        ticket=self.a.irc_ticket(self.player)
        with self.assertRaises(PermissionError):self.a.irc_login('PlayerTwo',ticket['code'],'192.168.8.2')
        token,user=self.a.irc_login('PlayerTwo',ticket['code'],'192.168.8.3');self.assertEqual(user['id'],self.player['id'])
        with self.assertRaises(PermissionError):self.a.irc_login('PlayerTwo',ticket['code'],'192.168.8.3')
        self.a.manage(self.admin,{'op':'reset','id':self.player['id'],'password':'TemporaryPassword123'})
        with self.assertRaises(PermissionError):self.a.session(token,'192.168.8.3')
    def test_logout_expiry_and_non_leaking_storage(self):
        with self.a.db() as c:
            self.assertNotEqual(c.execute('SELECT token FROM sessions WHERE user_id=?',(self.player['id'],)).fetchone()[0],self.pt)
            self.assertNotIn('PlayerPassword123',(Path(self.tmp.name)/'accounts.sqlite3').read_bytes().decode('latin1'))
            c.execute('UPDATE sessions SET expires=0 WHERE user_id=?',(self.player['id'],))
        with self.assertRaises(PermissionError):self.a.session(self.pt,'192.168.8.3')
        self.a.logout(self.at)
        with self.assertRaises(PermissionError):self.a.session(self.at,'192.168.8.2')
if __name__=='__main__':unittest.main()
