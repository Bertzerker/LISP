from account_test_remote import *
import urllib.request,urllib.error,http.cookiejar,ssl,secrets,time,json,re
root=pathlib.Path(__file__).resolve().parents[1]
c=connect();s=c.open_sftp();s.get('/srv/lan-party/site/style/lisp-lan-ca.crt',str(CA_FILE));s.close()
context=ssl.create_default_context(cafile=str(CA_FILE))
class Client:
 def __init__(self):self.cookies=http.cookiejar.CookieJar();self.open=urllib.request.build_opener(urllib.request.HTTPSHandler(context=context),urllib.request.HTTPCookieProcessor(self.cookies));self.user=None
 def req(self,path,data=None,expect=200,csrf=True,extra=None):
  headers={'X-LAN-Request':'1','Content-Type':'application/json'}
  if self.user and csrf:headers['X-CSRF-Token']=self.user['csrf']
  if extra:headers.update(extra)
  req=urllib.request.Request(f'https://{HOST}'+path,json.dumps(data).encode() if data is not None else None,headers=headers)
  try:
   r=self.open.open(req,timeout=220);code=r.status;body=r.read();h=r.headers
  except urllib.error.HTTPError as e:code=e.code;body=e.read();h=e.headers
  assert code==expect,(path,code,expect,body[:200])
  return json.loads(body) if 'application/json' in h.get('Content-Type','') else body
names=[];ids=[];owned=[];topic=None
def report(text):print('PASS '+text,flush=True)
try:
 anonymous=Client()
 for path in ['/api/catalog','/api/servers','/api/chat','/auth-api/forum','/files/Age%20of%20Empires%20Collection.iso']:anonymous.req(path,expect=401)
 for path in ['/downloads/','/servers/','/forum/','/accounts/','/admin/']:
  result=anonymous.open.open(f'https://{HOST}'+path);assert result.geturl()==f'https://{HOST}/'
 report('Guests cannot access protected pages, downloads or APIs')
 players=[Client(),Client(),Client()];passwords=[]
 for p in players:
  name='LISPTest'+secrets.token_hex(4);names.append(name);secret=secrets.token_urlsafe(18);passwords.append(secret)
  p.user=p.req('/auth-api/register',dict(name=name,password=secret));ids.append(p.user['id'])
  assert p.user['role']=='player' and p.user['ip'] and re.fullmatch('[0-9a-f:]{17}',p.user['mac'])
 report('Registration binds the actual Windows LAN client IP/MAC')
 one,two,admin=players
 run(c,"python3 -c 'import sqlite3; c=sqlite3.connect(\"/var/lib/lisp-accounts/accounts.sqlite3\");c.execute(\"update users set role=? where id=?\",(\"admin\","+str(admin.user['id'])+"));c.commit()'",True)
 admin.user=admin.req('/auth-api/session')
 one.req('/auth-api/accounts',expect=403);one.req('/admin-api/network',expect=403)
 admin.req('/admin-api/network');admin.req('/auth-api/accounts')
 report('Player/admin permissions protect accounts and network controls')
 one.req('/api/servers',{'game':'sof2','mode':'dm','map':'mp_shop','players':8},expect=403,csrf=False)
 one.req('/auth-api/forum',{'op':'topic','board':1,'title':'Forbidden','body':'Missing CSRF'},expect=401,csrf=False)
 report('State changes reject missing CSRF tokens')
 boards=one.req('/auth-api/forum')['boards'];assert [b['name'] for b in boards]==['General','Games','Servers','Tools','Emulators']
 topic=one.req('/auth-api/forum',{'op':'topic','board':2,'title':'LISP owned validation topic','body':'<script>must stay plain text</script>'})['topic']
 two.req('/auth-api/forum',{'op':'reply','topic':topic,'body':'Test reply'})
 assert len(one.req('/auth-api/forum?topic='+str(topic))['posts'])==2
 one.req('/auth-api/forum',{'op':'lock','topic':topic,'locked':True},expect=403)
 admin.req('/auth-api/forum',{'op':'lock','topic':topic,'locked':True});time.sleep(2.1)
 two.req('/auth-api/forum',{'op':'reply','topic':topic,'body':'Blocked on locked topic'},expect=400)
 report('Forum sections, persistent posts, replies and admin moderation')
 chat=one.req('/api/chat/message',{'text':'LISP account chat validation'});assert chat['sent']
 assert one.req('/api/chat')['nick']==one.user['name']
 ticket=one.req('/auth-api/irc-code',{})
 import socket
 with socket.create_connection((HOST,6667),timeout=5) as irc:
  irc.settimeout(5);irc.sendall(('PASS '+ticket['code']+'\r\nNICK '+one.user['name']+'\r\nUSER lisp 0 * :LAN Player\r\n').encode());buf=b''
  while b' 001 ' not in buf:buf+=irc.recv(4096)
  irc.sendall(b'JOIN #lan\r\n');buf=b''
  while b' 366 ' not in buf:buf+=irc.recv(4096)
  irc.sendall(b'QUIT\r\n')
 report('Chat uses account identity; IRC accepts an IP/MAC-bound one-time code')
 # Use only free slots and only own test instances.
 assert not one.req('/api/servers')['servers'],'Player matches present: defer owned live tests'
 catalog=one.req('/api/catalog')['games'];sof=next(g for g in catalog if g['id']=='sof2');mode=sof['modes'][0]['id'];level=sof['maps'][0]
 for client in (one,two):owned.append((client,client.req('/api/servers',dict(game='sof2',mode=mode,map=level,players=8,ownerId=admin.user['id']))['id']))
 deadline=time.monotonic()+80
 while time.monotonic()<deadline:
  servers=one.req('/api/servers')['servers']
  if all(next(s for s in servers if s['id']==ident)['status']=='running' for client,ident in owned):break
  time.sleep(5)
 else:raise AssertionError('Owned SoF2 tests did not become ready')
 first,second=[i for _,i in owned];servers=one.req('/api/servers')['servers'];a=next(s for s in servers if s['id']==first);b=next(s for s in servers if s['id']==second)
 assert a['ownerId']==one.user['id'] and a['canStop'] and not b['canStop'] and a['port']!=b['port']
 two.req('/api/servers/'+first+'/stop',{},expect=403);one.req('/api/servers/'+second+'/stop',{},expect=403)
 one.req('/api/servers/'+first+'/stop',{});owned=[owned[1]]
 assert next(s for s in two.req('/api/servers')['servers'] if s['id']==second)['status']=='running'
 admin.req('/api/servers/'+second+'/stop',{});owned=[]
 report('Two same-game servers retain distinct owners; only owner/admin can stop; independent stopping works')
 target=two.user['id'];admin.req('/auth-api/accounts',{'op':'reset','id':target,'password':'TemporaryTestPassword123'})
 two.req('/auth-api/session',expect=401);two.user=two.req('/auth-api/login',{'name':two.user['name'],'password':'TemporaryTestPassword123'})
 two.req('/api/catalog',expect=401)
 two.user=two.req('/auth-api/password',{'current':'TemporaryTestPassword123','new':passwords[1]});two.req('/api/catalog')
 admin.req('/auth-api/accounts',{'op':'bind','id':target,'ip':two.user['ip']});two.req('/auth-api/session',expect=401)
 two.user=two.req('/auth-api/login',{'name':two.user['name'],'password':passwords[1]})
 admin.req('/auth-api/accounts',{'op':'enabled','id':target,'enabled':False});two.req('/auth-api/session',expect=401)
 report('Reset requires password change; rebind and disable revoke sessions')
 links=re.findall(r'href="(/files/[^"<>]+)"',one.req('/downloads/').decode())
 assert links
 path=links[0];req=urllib.request.Request(f'https://{HOST}'+path,method='HEAD');response=one.open.open(req);assert int(response.headers['Content-Length'])>0
 response=one.open.open(urllib.request.Request(f'https://{HOST}'+path,headers={'Range':'bytes=0-31'}));assert response.status==206 and len(response.read())==32
 report('Authenticated downloads retain HEAD sizes and resumable ranges')
 one.req('/auth-api/logout',{});one.req('/api/catalog',expect=401)
 report('Logout immediately removes access')
finally:
 for client,ident in owned:
  try:admin.req('/api/servers/'+ident+'/stop',{})
  except Exception:print('Owned instance needs cleanup:',ident)
 if ids:
  sql="""import sqlite3
c=sqlite3.connect('/var/lib/lisp-accounts/accounts.sqlite3');ids="""+repr(ids)+"""
q=','.join('?' for _ in ids)
c.execute('DELETE FROM posts WHERE topic IN (SELECT id FROM topics WHERE user_id IN ('+q+')) OR user_id IN ('+q+')',ids+ids)
c.execute('DELETE FROM topics WHERE user_id IN ('+q+')',ids)
for table,column in [('sessions','user_id'),('irc_tickets','user_id'),('audit','actor')]:c.execute('DELETE FROM '+table+' WHERE '+column+' IN ('+q+')',ids)
c.execute('DELETE FROM users WHERE id IN ('+q+')',ids);c.commit()
d=sqlite3.connect('/srv/lan-party/chat/chat.sqlite3')
d.execute('DELETE FROM messages WHERE nick IN ('+q+')',"""+repr(names)+""")
d.execute('DELETE FROM sessions WHERE nick IN ('+q+')',"""+repr(names)+""");d.commit()
print('Owned test accounts, forum posts and chat cleaned up')
"""
  run(c,"python3 - <<'PY'\n"+sql+"\nPY",True)
 c.close()
