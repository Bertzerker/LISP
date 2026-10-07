#!/usr/bin/python3
import hmac,json,os,pwd,socket,socketserver,struct,threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlparse,parse_qs
from accounts import Accounts,interfaces
from account_client import cookie

AUTH=Accounts(os.environ.get('LISP_ACCOUNTS_DIR','/var/lib/lisp-accounts'))
HOSTS=set(os.environ.get('LISP_ALLOWED_HOSTS','192.168.8.138,10.42.0.1,127.0.0.1,localhost').split(','))
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def reply(self,status,value=None,token=None):
        body=json.dumps(value).encode() if value is not None else b''
        self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(body)))
        if token is not None:self.send_header('Set-Cookie','lisp_session='+token+'; Path=/; HttpOnly; Secure; SameSite=Strict'+('; Max-Age=28800' if token else '; Max-Age=0'))
        self.end_headers();self.wfile.write(body)
    def secure(self):return self.headers.get('X-Forwarded-Proto')=='https' and urlparse('//'+self.headers.get('Host','')).hostname in HOSTS
    def user(self,write=False,admin=False,allow_change=False):return AUTH.session(cookie(self.headers),self.headers.get('X-Real-IP',''),self.headers.get('X-CSRF-Token','') if write else None,allow_change,admin)
    def do_GET(self):
        if not self.secure():self.reply(403,{'error':'Use the secure LAN portal.'});return
        try:
            url=urlparse(self.path);q=parse_qs(url.query)
            if url.path in ('/auth-api/check','/auth-api/check-admin'):
                self.user(admin=url.path.endswith('admin'));self.reply(204);return
            if url.path=='/auth-api/session':self.reply(200,self.user(allow_change=True));return
            user=self.user()
            if url.path=='/auth-api/accounts':self.user(admin=True);self.reply(200,{'users':AUTH.users(),'interfaces':interfaces()})
            elif url.path=='/auth-api/forum':
                if 'topic' in q:self.reply(200,AUTH.topic(int(q['topic'][0])))
                elif 'board' in q:self.reply(200,{'topics':AUTH.topics(int(q['board'][0]))})
                else:self.reply(200,{'boards':AUTH.boards()})
            else:self.reply(404,{'error':'Not found'})
        except PermissionError as e:self.reply(403 if 'Administrator' in str(e) else 401,{'error':str(e)})
        except (ValueError,TypeError) as e:self.reply(400,{'error':str(e)})
        except Exception:self.reply(503,{'error':'Account service is temporarily unavailable.'})
    def do_POST(self):
        origin=urlparse(self.headers.get('Origin',''))
        if not self.secure() or self.headers.get('X-LAN-Request')!='1' or (origin.netloc and (origin.scheme!='https' or origin.netloc!=self.headers.get('Host'))):self.reply(403,{'error':'Use the secure LAN portal.'});return
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=32768:raise ValueError('Invalid request size.')
            data=json.loads(self.rfile.read(size))
            if not isinstance(data,dict):raise ValueError('Invalid request.')
            ip=self.headers.get('X-Real-IP','')
            if self.path in ('/auth-api/login','/auth-api/register'):
                method=AUTH.login if self.path.endswith('login') else AUTH.register
                token,result=method(data.get('name'),data.get('password'),ip);self.reply(200,result,token);return
            user=self.user(True,allow_change=self.path in ('/auth-api/password','/auth-api/logout'))
            if self.path=='/auth-api/password':token,result=AUTH.change(user,data.get('current'),data.get('new'),ip);self.reply(200,result,token)
            elif self.path=='/auth-api/logout':AUTH.logout(cookie(self.headers));self.reply(200,{'loggedOut':True},'')
            elif self.path=='/auth-api/irc-code':self.reply(200,AUTH.irc_ticket(user))
            elif self.path=='/auth-api/accounts':self.reply(200,AUTH.manage(user,data))
            elif self.path=='/auth-api/forum':
                if os.path.exists('/var/lib/lisp-accounts/forum-migrated.json'):raise ValueError('The forum has moved to /forum/. Please refresh the portal.')
                self.reply(200,AUTH.post(user,data))
            else:self.reply(404,{'error':'Not found'})
        except PermissionError as e:self.reply(403 if 'Administrator' in str(e) else 401,{'error':str(e)})
        except (ValueError,TypeError) as e:self.reply(400,{'error':str(e)})
        except Exception:self.reply(503,{'error':'Account operation failed; check the private service journal.'})
class Local(socketserver.StreamRequestHandler):
    def handle(self):
        uid=struct.unpack('3i',self.request.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))[1]
        def app_uid(name):
            try:return pwd.getpwnam(name).pw_uid
            except KeyError:return -1
        if uid not in (0,app_uid('lanserver'),app_uid('lanadmin'),app_uid('lancommunity'),app_uid('lanforum')):return
        self.request.settimeout(8)
        try:
            raw=self.rfile.readline(4097)
            if len(raw)>4096:raise ValueError('Invalid session request.')
            data=json.loads(raw)
            if data['op']=='session':result=AUTH.session(data.get('token',''),data.get('ip'),data.get('csrf'),data.get('allowChange',False),data.get('admin',False))
            elif data['op']=='irc-login':
                if uid not in (0,app_uid('lanserver')):raise PermissionError('Unsupported client.')
                token,result=AUTH.irc_login(data.get('name'),data.get('code'),data.get('ip'));result['token']=token
            elif data['op']=='community-users' and uid in (0,app_uid('lancommunity')):result={'users':AUTH.community_users()}
            elif data['op']=='verify-password' and uid in (0,app_uid('lanforum')):
                user=AUTH.session(data.get('token',''),data.get('ip'))
                result=AUTH.verify_forum_password(user,data.get('password'))
            else:raise ValueError('Unsupported session request.')
        except (PermissionError,ValueError,KeyError) as e:result={'error':str(e)}
        except Exception:result={'error':'Account service is unavailable.'}
        self.wfile.write(json.dumps(result).encode()+b'\n')
class LocalServer(socketserver.ThreadingUnixStreamServer):daemon_threads=True
if __name__=='__main__':
    os.umask(0o077);path='/run/lisp-accounts/auth.sock'
    try:os.unlink(path)
    except FileNotFoundError:pass
    local=LocalServer(path,Local);os.chmod(path,0o660)
    threading.Thread(target=local.serve_forever,daemon=True).start()
    ThreadingHTTPServer(('127.0.0.1',8790),Handler).serve_forever()
