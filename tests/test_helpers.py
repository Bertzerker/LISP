import json,time,socket,struct,secrets,sys,os
from urllib.request import urlopen,Request
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from adapters import registry
BASE=os.environ.get('LISP_TEST_URL','http://127.0.0.1:8787')
TARGET=os.environ.get('LISP_BIND_IP','192.168.8.138')
def api(path,data=None):
    return json.load(urlopen(Request(BASE+path,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json','X-LAN-Request':'1'}),timeout=180))
def packet(ident,kind,text):
    data=struct.pack('<ii',ident,kind)+text.encode()+b'\0\0';return struct.pack('<i',len(data))+data
def receive(s):
    def exact(n):
        out=b''
        while len(out)<n:
            b=s.recv(n-len(out))
            if not b:raise AssertionError('RCON connection closed')
            out+=b
        return out
    n=struct.unpack('<i',exact(4))[0];assert 10<=n<=1000000
    data=exact(n);return struct.unpack('<ii',data[:8]),data[8:-2]
def rcon(adapter,port,pwd):
    if adapter.engine=='source':
        with socket.create_connection((TARGET,port),timeout=5) as sock:
            sock.sendall(packet(42,3,pwd))
            for _ in range(3):
                (ident,kind),data=receive(sock)
                if kind==2:assert ident==42;break
            else:raise AssertionError('No RCON authentication response')
            sock.sendall(packet(43,2,'status'));(ident,kind),data=receive(sock);assert ident==43 and data
    elif adapter.engine=='goldsrc':
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
            sock.settimeout(5);sock.sendto(b'\xff\xff\xff\xffchallenge rcon\n',(TARGET,port));challenge=sock.recv(8192).decode('latin1').strip('\x00\n').split()[-1]
            sock.sendto(('\xff'*4+'rcon '+challenge+' "'+pwd+'" status\n').encode('latin1'),(TARGET,port));data=sock.recv(16384);assert b'hostname' in data.lower() or b'players' in data.lower(),data

