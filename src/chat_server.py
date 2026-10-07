#!/usr/bin/python3
import json,os
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlparse,parse_qs
from account_client import check
from chat import Chat,start_irc
CHAT=Chat();HOSTS=set(os.environ.get('LISP_ALLOWED_HOSTS','192.168.8.138,10.42.0.1,127.0.0.1,localhost').split(','))
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def allowed(self):return self.headers.get('X-Forwarded-Proto')=='https' and urlparse('//'+self.headers.get('Host','')).hostname in HOSTS
    def reply(self,status,value):
        body=json.dumps(value).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    def do_GET(self):
        if not self.allowed():self.reply(403,{'error':'Use the secure LAN portal.'});return
        try:
            user=check(self.headers);token=CHAT.account(user)
            u=urlparse(self.path)
            if u.path!='/api/chat':self.reply(404,{'error':'Not found'});return
            since=int(parse_qs(u.query).get('since',['0'])[0])
            if not 0<=since<=2**63-1:raise ValueError('Invalid cursor.')
            room=parse_qs(u.query).get('room',['general'])[0]
            self.reply(200,CHAT.read(token,since,room))
        except PermissionError as e:self.reply(401,{'error':str(e)})
        except ValueError as e:self.reply(400,{'error':str(e)})
    def do_POST(self):
        origin=urlparse(self.headers.get('Origin',''))
        if not self.allowed() or self.headers.get('X-LAN-Request')!='1' or (origin.netloc and (origin.scheme!='https' or origin.netloc!=self.headers.get('Host'))):self.reply(403,{'error':'Use the secure portal to chat.'});return
        try:
            user=check(self.headers,write=True);token=CHAT.account(user)
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=4096:raise ValueError('Invalid message size.')
            data=json.loads(self.rfile.read(size))
            if not isinstance(data,dict):raise ValueError('Invalid request.')
            if self.path=='/api/chat/message':self.reply(200,CHAT.send(token,data.get('text'),data.get('room','general')))
            elif self.path=='/api/chat/join':
                room=data.get('room','general');CHAT.enter(token,room);self.reply(200,{'joined':True,'nick':user['name'],'room':room})
            elif self.path=='/api/chat/leave':CHAT.leave(token,'browser');self.reply(200,{'left':True})
            else:self.reply(404,{'error':'Not found'})
        except PermissionError as e:self.reply(401,{'error':str(e)})
        except (ValueError,TypeError) as e:self.reply(400,{'error':str(e)})
if __name__=='__main__':
    os.umask(0o077);start_irc(CHAT);ThreadingHTTPServer(('127.0.0.1',8789),Handler).serve_forever()
