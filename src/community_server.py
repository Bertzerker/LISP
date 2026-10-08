#!/usr/bin/python3
"""Authenticated portal API and restricted Bracket gateway, bound to loopback."""
import hmac,json,os,re,threading,time
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlparse,parse_qs
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
from pathlib import Path
import account_client
from community import Store,Services,Worker,admin
from personal_status import PersonalStatus

CONFIG=json.loads(Path(os.getenv('LISP_COMMUNITY_CONFIG','/etc/lisp/community/settings.json')).read_text())
STORE=Store(os.getenv('LISP_COMMUNITY_DIR','/var/lib/lisp-community'));SERVICES=Services(CONFIG);WORKER=Worker(STORE,SERVICES)
PERSONAL=PersonalStatus(STORE,SERVICES)
HOSTS={CONFIG['host'],'10.42.0.1','127.0.0.1','localhost'}
def profiles():return account_client.call({'op':'community-users'})['users']
def profile(ident):
    person=next((p for p in profiles() if p['id']==ident),None)
    if not person:raise ValueError('Profile not found.')
    return {**person,'trophies':STORE.trophies(ident)}
def games(headers):
    req=Request('http://127.0.0.1:8787/api/catalog',headers={'Cookie':headers.get('Cookie',''),'Host':headers.get('Host',''),'X-Real-IP':headers.get('X-Real-IP',''),'X-Forwarded-Proto':'https'})
    with urlopen(req,timeout=10) as r:data=json.load(r)
    return {g['id']:g['name'] for g in data['games']}
def bracket_allowed(method,path,user,store=STORE):
    route=urlparse(path).path.strip('/')
    # No alternate accounts, token endpoints, password resets or backend admin API.
    if route=='users/me':return method=='GET'
    if not (route=='clubs' or re.fullmatch(r'clubs/\d+',route) or route=='tournaments' or re.fullmatch(r'tournaments/\d+(?:/[A-Za-z0-9_./-]+)?',route)) or '..' in route:return False
    if user['role']=='admin':
        # Finalized event records are immutable; corrections must be made explicitly.
        m=re.match(r'tournaments/(\d+)',route)
        if method not in ('GET','HEAD') and m:
            linked=store.for_bracket(int(m[1]))
            if linked and linked['status'] in ('final','cancelled'):return False
        return True
    if method not in ('GET','HEAD'):return False
    if route in ('clubs','tournaments'):return True
    m=re.fullmatch(r'tournaments/(\d+)(?:/[A-Za-z0-9_./-]+)?',route)
    linked=store.for_bracket(int(m[1])) if m else None
    return bool(linked and linked['status']!='cancelled')

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def reply(self,status,value):
        body=json.dumps(value).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    def user(self,write=False):
        origin=urlparse(self.headers.get('Origin',''));host=self.headers.get('Host','')
        if self.headers.get('X-Forwarded-Proto')!='https' or urlparse('//'+host).hostname not in HOSTS:raise PermissionError('Use the secure LAN portal.')
        if write and (self.headers.get('X-LAN-Request')!='1' or (origin.netloc and (origin.netloc!=host or origin.scheme!='https'))):raise PermissionError('Refresh the portal before making changes.')
        return account_client.check(self.headers,write=write)
    def run_request(self):
        try:
            url=urlparse(self.path);q=parse_qs(url.query);method=self.command;write=method not in ('GET','HEAD')
            if url.path.startswith('/community-private/profile/'):
                if method!='GET' or not hmac.compare_digest(self.headers.get('X-LISP-Private',''),CONFIG['forumSecret']):raise PermissionError('Private endpoint.')
                self.reply(200,profile(int(url.path.rsplit('/',1)[1])));return
            user=self.user(write)
            if url.path.startswith('/bracket-api/'):
                path=self.path[len('/bracket-api/'):]
                native_delete=re.fullmatch(r'tournaments/(\d+)/?',path)
                if method=='DELETE' and native_delete:
                    admin(user);linked=STORE.for_bracket(int(native_delete[1]))
                    if linked:
                        with WORKER.serial:STORE.cancel(user,linked['id'],'Cancelled by organizer')
                        self.reply(200,{'success':True});return
                if not bracket_allowed(method,path,user):raise PermissionError('This Bracket operation is not available to your account.')
                size=int(self.headers.get('Content-Length','0'))
                if not 0<=size<=8*1024*1024:raise ValueError('File is too large.')
                req=Request(CONFIG.get('bracketUrl','http://127.0.0.1:8793/')+path,self.rfile.read(size) if size else None,{'Authorization':'Bearer '+SERVICES.token(),'Content-Type':self.headers.get('Content-Type','application/json')},method=method)
                try:response=urlopen(req,timeout=30)
                except HTTPError as e:response=e
                with response as r:
                    body=r.read(16*1024*1024+1)
                    if len(body)>16*1024*1024:raise ValueError('Bracket response is too large.')
                    if method=='GET' and urlparse(path).path.strip('/')=='tournaments' and r.status==200:
                        listing=json.loads(body)
                        listing['data']=[x for x in listing['data'] if not (p:=STORE.for_bracket(x['id'])) or p['status']!='cancelled']
                        body=json.dumps(listing).encode()
                    self.send_response(r.status);self.send_header('Content-Type',r.headers.get('Content-Type','application/json'));self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(body)));self.end_headers()
                    if method!='HEAD':self.wfile.write(body)
                return
            if not write:
                if url.path=='/community-api/tournaments':self.reply(200,{'tournaments':STORE.view(user,include_cancelled=q.get('archived',['0'])[0]=='1'),'games':games(self.headers)})
                elif url.path=='/community-api/status':self.reply(200,PERSONAL.get(user))
                elif url.path=='/community-api/profile':self.reply(200,profile(int(q.get('user',[user['id']])[0])))
                elif url.path=='/community-api/profiles':self.reply(200,{'users':profiles()})
                elif url.path=='/community-api/bracket-session':
                    me=SERVICES.api('users/me')['data'];self.reply(200,{'user_id':me['id'],'access_token':'portal-session','csrf':user['csrf'],'role':user['role']})
                elif url.path=='/community-api/podium':
                    admin(user);p=STORE.view(ident=int(q['id'][0]))[0]
                    self.reply(200,{'teams':SERVICES.api(f'tournaments/{p["bracket"]}/teams?limit=100')['data']['teams'],'stages':SERVICES.api(f'tournaments/{p["bracket"]}/stages')['data']})
                else:self.reply(404,{'error':'Not found.'})
                return
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=32768:raise ValueError('Invalid request size.')
            data=json.loads(self.rfile.read(size));ident=data.get('id')
            if url.path!='/community-api/create' and type(ident) is not int:raise ValueError('Choose a tournament.')
            if url.path=='/community-api/create':ident=STORE.create(user,data,games(self.headers))
            elif url.path=='/community-api/vote':STORE.vote(user,ident,data.get('game'))
            elif url.path=='/community-api/close':STORE.close(user,ident,data.get('winner'))
            elif url.path=='/community-api/signup':STORE.signup(user,ident)
            elif url.path in ('/community-api/delete','/community-api/restore'):
                with WORKER.serial:
                    if url.path.endswith('/delete'):STORE.cancel(user,ident,data.get('reason','Not enough players'))
                    else:
                        admin(user);p=STORE.view(ident=ident)[0]
                        missing=bool(p['bracket'] and not any(x['id']==p['bracket'] for x in SERVICES.api('tournaments?filter_=ALL')['data']))
                        STORE.restore(user,ident,native_missing=missing)
            elif url.path=='/community-api/finalize':
                admin(user);p=STORE.view(ident=ident)[0]
                teams=SERVICES.api(f'tournaments/{p["bracket"]}/teams?limit=100')['data']['teams'];STORE.finalize(user,ident,data.get('podium'),teams)
            else:self.reply(404,{'error':'Not found.'});return
            self.reply(200,{'updated':True,'id':ident})
        except PermissionError as e:self.reply(403,{'error':str(e)})
        except (ValueError,KeyError,TypeError) as e:self.reply(400,{'error':str(e)})
        except Exception:self.reply(503,{'error':'Community service is temporarily unavailable. Saved updates will retry automatically.'})
    do_GET=do_POST=do_PUT=do_PATCH=do_DELETE=do_HEAD=run_request

def background():
    while True:
        try:WORKER.tick()
        except Exception:print('Community worker will retry.',flush=True)
        time.sleep(10)
if __name__=='__main__':
    os.umask(0o077);threading.Thread(target=background,daemon=True).start();ThreadingHTTPServer(('127.0.0.1',8791),Handler).serve_forever()
