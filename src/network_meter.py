"""Privileged, restricted local nft byte-counter helper. Never changes verdicts."""
from pathlib import Path
import ipaddress,json,os,pwd,re,socket,socketserver,struct,subprocess,threading
from credits import controller_peer
TABLE='lisp_meter';lock=threading.RLock();entries={}
NETWORKS=[str(ipaddress.IPv4Network(x)) for x in os.environ.get('LISP_METER_NETWORKS','192.168.8.0/24,10.42.0.0/24').split(',')]
def nft(command):return subprocess.check_output(['/usr/bin/nft','-j','-f','-'],input=command.encode(),stderr=subprocess.PIPE,timeout=3)
def valid_id(ident):
    if not isinstance(ident,str) or not re.fullmatch('[a-f0-9]{32}',ident):raise ValueError('Invalid counter ID.')
    return ident
def add(ident,ports):
    valid_id(ident)
    if not isinstance(ports,list) or not 1<=len(ports)<=16:raise ValueError('Invalid ports.')
    ports=sorted(set((x.get('port'),x.get('protocol')) for x in ports))
    for n,p in ports:
        if type(n) is not int or p not in ('tcp','udp') or not (27015<=n<=27060 or 28015<=n<=28050):raise ValueError('Port is outside server ranges.')
    if ident in entries:
        if entries[ident]!=ports:raise ValueError('Counter already exists.')
        return {}
    for stale in list(entries):
        if not (Path('/sys/fs/cgroup/system.slice/lan-portal.service')/('lisp-'+stale)).exists():remove(stale)
    if len(entries)>=6:raise ValueError('Counter limit reached.')
    if any(pair in other for other in entries.values() for pair in ports):raise ValueError('Port already metered.')
    commands=[f'add counter inet {TABLE} rx_{ident}',f'add counter inet {TABLE} tx_{ident}']
    nets='{ '+', '.join(NETWORKS)+' }'
    for proto in ('udp','tcp'):
        numbers=[str(n) for n,p in ports if p==proto]
        if numbers:
            values='{ '+', '.join(numbers)+' }'
            commands += [f'add rule inet {TABLE} incoming ip saddr {nets} {proto} dport {values} counter name rx_{ident} comment "{ident}"',f'add rule inet {TABLE} outgoing ip daddr {nets} {proto} sport {values} counter name tx_{ident} comment "{ident}"']
    nft('\n'.join(commands));entries[ident]=ports;return {}
def read(ident):
    valid_id(ident)
    if ident not in entries:raise ValueError('Counter unavailable.')
    raw=json.loads(subprocess.check_output(['/usr/bin/nft','-j','list','counters','table','inet',TABLE],timeout=3));values={x['counter']['name']:x['counter']['bytes'] for x in raw['nftables'] if 'counter' in x}
    return {'rxBytes':values['rx_'+ident],'txBytes':values['tx_'+ident]}
def remove(ident):
    valid_id(ident)
    if ident not in entries:return {}
    raw=json.loads(subprocess.check_output(['/usr/bin/nft','-j','list','table','inet',TABLE],timeout=3));commands=[]
    for x in raw['nftables']:
        r=x.get('rule',{})
        if r.get('comment')==ident:commands.append(f'delete rule inet {TABLE} {r["chain"]} handle {r["handle"]}')
    commands += [f'delete counter inet {TABLE} rx_{ident}',f'delete counter inet {TABLE} tx_{ident}'];nft('\n'.join(commands));del entries[ident];return {}
class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        pid,uid,gid=struct.unpack('3i',self.request.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
        if uid not in (0,pwd.getpwnam('lanserver').pw_uid) or not controller_peer(uid,pid):return
        self.request.settimeout(4)
        try:
            raw=self.rfile.readline(4097)
            if len(raw)>4096:raise ValueError('Request too large.')
            d=json.loads(raw)
            with lock:
                if d.get('op')=='add':v=add(d.get('id'),d.get('ports'))
                elif d.get('op')=='read':v=read(d.get('id'))
                elif d.get('op')=='remove':v=remove(d.get('id'))
                else:raise ValueError('Unsupported operation.')
        except Exception:v={'error':'Network counters unavailable.'}
        self.wfile.write(json.dumps(v).encode()+b'\n')
class Server(socketserver.ThreadingUnixStreamServer):daemon_threads=True
if __name__=='__main__':
    # Own table only. No packet is accepted/dropped by these counter rules.
    subprocess.run(['/usr/bin/nft','delete','table','inet',TABLE],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    nft(f'add table inet {TABLE}\nadd chain inet {TABLE} incoming {{ type filter hook input priority 10; policy accept; }}\nadd chain inet {TABLE} outgoing {{ type filter hook output priority 10; policy accept; }}')
    path='/run/lisp-network-meter/meter.sock'
    try:os.unlink(path)
    except FileNotFoundError:pass
    server=Server(path,Handler);os.chown(path,0,pwd.getpwnam('lanserver').pw_gid);os.chmod(path,0o660);server.serve_forever()
