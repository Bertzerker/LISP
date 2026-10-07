#!/usr/bin/python3
"""Network controls require the same bound administrator session as the portal."""
import json,os,socket
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlparse
from account_client import check
HOSTS=set(os.environ.get('LISP_ALLOWED_HOSTS','192.168.8.138,10.42.0.1,127.0.0.1,localhost').split(','))
def network(request):
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as s:
        s.settimeout(110);s.connect('/run/lisp-network/control.sock');s.sendall(json.dumps(request).encode()+b'\n');result=json.loads(s.makefile('rb').readline(131073))
        if 'error' in result:raise ValueError(result['error'])
        return result
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def secure(self):return self.headers.get('X-Forwarded-Proto')=='https' and urlparse('//'+self.headers.get('Host','')).hostname in HOSTS
    def reply(self,status,value):
        body=json.dumps(value).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    def do_GET(self):
        if not self.secure():self.reply(403,{'error':'Use HTTPS.'});return
        try:
            user=check(self.headers,admin=True)
            if self.path=='/admin-api/session':self.reply(200,user)
            elif self.path=='/admin-api/network':self.reply(200,network({'op':'status'}))
            else:self.reply(404,{'error':'Not found'})
        except PermissionError as e:self.reply(403,{'error':str(e)})
        except (OSError,ValueError):self.reply(503,{'error':'Network controller is unavailable.'})
    def do_POST(self):
        origin=urlparse(self.headers.get('Origin',''))
        if not self.secure() or self.headers.get('X-LAN-Request')!='1' or (origin.netloc and (origin.scheme!='https' or origin.netloc!=self.headers.get('Host'))):self.reply(403,{'error':'Use the secure portal.'});return
        try:
            check(self.headers,write=True,admin=True)
            n=int(self.headers.get('Content-Length','0'))
            if not 0<n<=4096:raise ValueError('Invalid request size.')
            data=json.loads(self.rfile.read(n))
            if not isinstance(data,dict):raise ValueError('Invalid request.')
            if self.path=='/admin-api/network':self.reply(200,network(data))
            else:self.reply(404,{'error':'Use the home page for account actions.'})
        except PermissionError as e:self.reply(403,{'error':str(e)})
        except (ValueError,TypeError) as e:self.reply(400,{'error':str(e)})
        except OSError:self.reply(503,{'error':'Network controller is unavailable.'})
if __name__=='__main__':
    os.umask(0o077);ThreadingHTTPServer(('127.0.0.1',8788),Handler).serve_forever()
