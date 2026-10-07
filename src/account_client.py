"""Session checks over a local socket; credentials stay with the account service."""
import json,socket,os
from http.cookies import SimpleCookie,CookieError
def cookie(headers):
    try:return SimpleCookie(headers.get('Cookie',''))['lisp_session'].value
    except (KeyError,CookieError):return ''
def check(headers,write=False,admin=False,allow_change=False):
    return call({'op':'session','token':cookie(headers),'ip':headers.get('X-Real-IP',''),'csrf':headers.get('X-CSRF-Token','') if write else None,'admin':admin,'allowChange':allow_change})
def call(data):
    try:
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as s:
            s.settimeout(8);s.connect(os.environ.get('LISP_ACCOUNT_SOCKET','/run/lisp-accounts/auth.sock'));s.sendall(json.dumps(data).encode()+b'\n')
            value=json.loads(s.makefile('rb').readline(65537))
    except (OSError,ValueError):raise PermissionError('Account service is unavailable. Try again shortly.')
    if 'error' in value:raise PermissionError(value['error'])
    return value
