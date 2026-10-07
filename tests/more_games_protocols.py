"""Native Source authentication and Unreal query checks used by live tests."""
import socket, struct
HOST='192.168.8.138'

def source_rcon(port,password,command):
    with socket.create_connection((HOST,port),timeout=3) as s:
        def read(n):
            result=b''
            while len(result)<n:
                b=s.recv(n-len(result))
                if not b:raise OSError('RCON closed')
                result+=b
            return result
        def receive():
            size=struct.unpack('<i',read(4))[0]
            if not 10<=size<=1024*1024:raise ValueError('Invalid RCON packet')
            b=read(size);ident,typ=struct.unpack_from('<ii',b)
            return ident,typ,b[8:-2].decode('utf8','replace')
        def send(typ,text):
            data=struct.pack('<ii',12345,typ)+text.encode()+b'\0\0';s.sendall(struct.pack('<i',len(data))+data)
        send(3,password)
        for _ in range(4):
            ident,typ,_=receive()
            if ident==-1:raise PermissionError('RCON rejected')
            if typ==2:break
        else:raise ValueError('No authentication response')
        send(2,command)
        for _ in range(4):
            ident,typ,body=receive()
            if ident==12345 and typ==0:return body
        raise ValueError('No command response')

def unreal1_rules(port):
    parts=[]
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
        s.settimeout(2);s.sendto(b'\\status\\',(HOST,port+1))
        for _ in range(16):
            try:b=s.recv(16384).decode('latin1')
            except socket.timeout:break
            parts.append(b)
            if '\\final\\' in b:break
    values={}
    for b in parts:
        items=b.split('\\');values.update(dict(zip(items[1::2],items[2::2])))
    return values

def unreal2_rules(port):
    parts=[]
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
        s.settimeout(.7);s.sendto(bytes([0x79,0,0,0,1]),(HOST,port+1))
        for _ in range(16):
            try:b=s.recv(16384)
            except socket.timeout:break
            if len(b)>=5 and b[4]==1:parts.append(b[5:])
    data=b''.join(parts);pos=0;values={}
    def string():
        nonlocal pos
        n=data[pos];pos+=1;wide=bool(n&128);size=(n&127)*(2 if wide else 1)
        if wide and data[pos]==1:pos+=1
        value=data[pos:pos+size].decode('utf-16-le' if wide else 'latin1').rstrip('\0');pos+=size
        return value
    while pos<len(data):
        k=string();v=string();values.setdefault(k,[]).append(v)
    return values
