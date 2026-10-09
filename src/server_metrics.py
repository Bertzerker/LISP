"""Per-engine cgroup CPU and LAN port byte counters; no packet capture."""
import json,socket,time,sys
from collections import deque
from pathlib import Path
def network(data):
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as s:
        s.settimeout(4);s.connect('/run/lisp-network-meter/meter.sock');s.sendall(json.dumps(data).encode()+b'\n');v=json.loads(s.makefile('rb').readline(32769))
    if 'error' in v:raise OSError(v['error'])
    return v
class EngineMeter:
    def __init__(self,ident,ports,run_id):
        self.ident=ident;self.run_id=run_id;self.group=Path('/sys/fs/cgroup/system.slice/lan-portal.service')/('lisp-'+run_id);self.group.mkdir()
        self.started=time.monotonic();self.samples=deque();self.closed=False
        try:
            network({'op':'add','id':run_id,'ports':[{'port':n,'protocol':'udp' if t==socket.SOCK_DGRAM else 'tcp'} for n,t in ports]})
            self.samples.append((self.started,0,0,0))
        except Exception:
            self.group.rmdir();raise
    def command(self,args):return [sys.executable,str(Path(__file__).with_name('engine_exec.py')),str(self.group),*args]
    def sample(self):
        now=time.monotonic();cpu=int(dict(line.split() for line in (self.group/'cpu.stat').read_text().splitlines())['usage_usec']);v=network({'op':'read','id':self.run_id});rx=v['rxBytes'];tx=v['txBytes']
        self.samples.append((now,cpu,rx,tx))
        while len(self.samples)>2 and self.samples[1][0]<now-60:self.samples.popleft()
        first=self.samples[0];span=max(.001,now-first[0]);last=self.samples[-2];interval=max(.001,now-last[0]);total=max(.001,now-self.started)
        value={'cpuPercent':round((cpu-last[1])/10000/interval,2),'cpuAveragePercent':round((cpu-first[1])/10000/span,2),'rxBytesPerSecond':round((rx-last[2])/interval,2),'txBytesPerSecond':round((tx-last[3])/interval,2),'networkAverageBytesPerSecond':round((rx+tx-first[2]-first[3])/span,2),'cpuSeconds':cpu/1000000,'rxBytes':rx,'txBytes':tx,'elapsedSeconds':round(total,2),'averageWindowSeconds':round(span,1),'sampledAt':time.time()}
        return cpu,rx,tx,value
    def close(self):
        if self.closed:return
        self.closed=True
        try:network({'op':'remove','id':self.run_id})
        except OSError:pass
        # Kill only leftover descendants of this exact, isolated owned engine.
        try:
            if 'populated 1' in (self.group/'cgroup.events').read_text():(self.group/'cgroup.kill').write_text('1')
            self.group.rmdir()
        except OSError:pass
