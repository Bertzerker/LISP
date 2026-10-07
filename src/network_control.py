#!/usr/bin/python3
"""Narrow privileged network controller. No changes occur until an admin applies a plan."""
import ipaddress,json,os,pwd,re,secrets,shlex,socket,socketserver,struct,subprocess,threading,time
from pathlib import Path
STATE=Path(os.environ.get('LISP_NETWORK_DIR','/var/lib/lisp-network'))
MGMT=os.environ.get('LISP_MANAGEMENT_IP','192.168.8.138')
GATEWAY=ipaddress.ip_interface(os.environ.get('LISP_GATEWAY_CIDR','10.42.0.1/24'))
IFACE=re.compile(r'^[A-Za-z0-9_.-]{1,15}$');MAC=re.compile(r'^(?:[0-9a-f]{2}:){5}[0-9a-f]{2}$')
def run(args,input=None,check=True):
    p=subprocess.run(args,input=input,text=True,capture_output=True,timeout=35)
    if check and p.returncode:raise ValueError((p.stderr or p.stdout or 'Network command failed').strip()[:400])
    return p.stdout if check else p
def nft_rules(config):
    prefix='destroy table inet lisp_access\n'
    if not config:return prefix
    lan,wan=config['lan'],config['wan']
    if not IFACE.fullmatch(lan) or not IFACE.fullmatch(wan):raise ValueError('Invalid interface.')
    blocked=config.get('blocked',[])
    if any(not MAC.fullmatch(x) for x in blocked):raise ValueError('Invalid client address.')
    elements=', '.join(blocked)
    drop='' if config.get('internet',False) else f'iifname "{lan}" counter drop\n'
    return prefix+f'''table inet lisp_access {{
 set blocked {{ type ether_addr; {'elements = { '+elements+' };' if elements else ''} }}
 chain forward {{ type filter hook forward priority -200; policy accept;
  iifname "{lan}" meta nfproto ipv6 counter drop
  iifname "{lan}" oifname != "{wan}" counter drop
  iifname "{lan}" ether saddr @blocked counter drop
  {drop}
 }}
}}
'''
class Controller:
    def __init__(self,folder=STATE):
        self.folder=Path(folder);self.folder.mkdir(parents=True,exist_ok=True);self.folder.chmod(0o700);self.lock=threading.RLock();self.plans={}
        self.state=self.read('settings.json',{});self.pending=self.read('pending.json',None)
    def read(self,name,default):
        try:return json.loads((self.folder/name).read_text())
        except FileNotFoundError:return default
    def save(self,name,data):
        tmp=self.folder/(name+'.tmp')
        with tmp.open('w') as f:os.chmod(tmp,0o600);json.dump(data,f);f.flush();os.fsync(f.fileno())
        tmp.replace(self.folder/name)
    def audit(self,op,data):
        p=self.folder/'audit.jsonl'
        if p.exists() and p.stat().st_size>1024*1024:p.replace(self.folder/'audit.previous.jsonl')
        with p.open('a') as f:os.chmod(p,0o600);f.write(json.dumps({'at':time.time(),'op':op,'details':data})+'\n')
    def inventory(self):
        addresses=json.loads(run(['ip','-j','address']));routes=json.loads(run(['ip','-j','route']))
        defaults=sorted([r for r in routes if r.get('dst')=='default' and r.get('gateway')],key=lambda r:r.get('metric',0));wan=defaults[0]['dev'] if defaults else None
        interfaces=[]
        for x in addresses:
            name=x['ifname']
            if name=='lo':continue
            ips=[a['local']+'/'+str(a['prefixlen']) for a in x.get('addr_info',[]) if a['family']=='inet']
            wireless=(Path('/sys/class/net')/name/'wireless').exists()
            management=any(a.split('/')[0]==MGMT for a in ips)
            interfaces.append({'name':name,'addresses':ips,'mac':x.get('address'),'state':x.get('operstate'),'wireless':wireless,'management':management,'upstream':name==wan,'canUseForLAN':not wireless and not management and name!=wan and x.get('link_type')=='ether' and name!='lisp-lan'})
        return interfaces,wan,routes
    def clients(self,interfaces):
        found={};config=self.state
        for n in json.loads(run(['ip','-j','neigh'])):
            try:address=ipaddress.ip_address(n['dst'])
            except (ValueError,KeyError):continue
            mac=n.get('lladdr','').lower()
            if address.version!=4 or not MAC.fullmatch(mac):continue
            states=n.get('state',[])
            if isinstance(states,str):states=[states]
            found[(mac,str(address))]={'mac':mac,'ip':str(address),'name':'','interface':n.get('dev'),'seen':', '.join(states),'manageable':bool(config and n.get('dev')==config['lan'] and address in GATEWAY.network),'blocked':mac in config.get('blocked',[])}
        for p in Path('/var/lib/NetworkManager').glob('dnsmasq*.leases'):
            try:lines=p.read_text().splitlines()
            except OSError:continue
            for line in lines:
                v=line.split()
                if len(v)<4:continue
                try:address=ipaddress.ip_address(v[2]);expires=int(v[0])
                except ValueError:continue
                if address.version!=4 or (expires and expires<time.time()):continue
                mac=v[1].lower()
                if not MAC.fullmatch(mac):continue
                key=(mac,str(address));item=found.get(key,{})
                if not item and (not config or address not in GATEWAY.network):continue
                found[key]={**item,'mac':mac,'ip':str(address),'name':'' if v[3]=='*' else v[3],'interface':item.get('interface',config.get('lan')),'seen':item.get('seen','DHCP lease'),'manageable':bool(config and address in GATEWAY.network),'blocked':mac in config.get('blocked',[])}
        return sorted(found.values(),key=lambda x:ipaddress.ip_address(x['ip']))
    def status(self):
        interfaces,wan,routes=self.inventory()
        return {'interfaces':interfaces,'upstream':wan,'gateway':str(GATEWAY),'config':self.state,'clients':self.clients(interfaces),'pending':{'id':self.pending['id'],'expires':self.pending['expires']} if self.pending else None,'note':'Controls apply only to clients using this PC as their gateway. Observed neighbours and active DHCP leases are listed; devices using another router cannot be blocked here.'}
    def plan(self,data):
        if self.pending:raise ValueError('Confirm or roll back the pending change first.')
        interfaces,wan,routes=self.inventory();available={x['name']:x for x in interfaces}
        ports=data.get('ports');mode=data.get('mode')
        if mode not in ('bridge','separate') or not isinstance(ports,list) or len(ports)!=len(set(str(x) for x in ports)) or not 1<=len(ports)<=3:raise ValueError('Choose one to three distinct Ethernet ports.')
        if mode=='separate' and len(ports)!=1:raise ValueError('Separate mode uses one Ethernet port for the LAN; other ports return to their previous connections.')
        if mode=='bridge' and len(ports)<2:raise ValueError('Choose at least two LAN ports to bridge.')
        if not wan:raise ValueError('An upstream default route is required. Connect the Internet interface first.')
        for port in ports:
            if not isinstance(port,str) or port not in available or not available[port]['canUseForLAN']:raise ValueError('Use Ethernet ports other than the management and Internet interfaces.')
        for route in routes:
            if route.get('dev') in self.state.get('ports',[]) or route.get('dev')==self.state.get('lan'):continue
            if route.get('dst') in ('default',None):continue
            try:overlap=ipaddress.ip_network(route['dst'],strict=False).overlaps(GATEWAY.network)
            except ValueError:continue
            if overlap:raise ValueError('The party subnet overlaps an existing network.')
        ident=secrets.token_urlsafe(24);self.plans={k:v for k,v in self.plans.items() if v['expires']>time.time()}
        self.plans[ident]={'expires':time.time()+120,'mode':mode,'ports':ports,'wan':wan}
        return {'plan':ident,'summary':f"{'Bridge '+', '.join(ports) if mode=='bridge' else 'Use '+ports[0]+' as a separate LAN'} at {GATEWAY}. DHCP will provide player addresses. Internet starts blocked until explicitly allowed. The management interface and upstream connection are preserved.",'rollbackSeconds':120}
    def bus(self,method,signature,*args):
        return run(['busctl','call','org.freedesktop.NetworkManager','/org/freedesktop/NetworkManager','org.freedesktop.NetworkManager',method,signature,*map(str,args)])
    def checkpoint(self,ports):
        paths=[shlex.split(self.bus('GetDeviceByIpIface','s',p))[1] for p in ports]
        return shlex.split(self.bus('CheckpointCreate','aouu',len(paths),*paths,120,6))[1]
    def apply_filter(self,config):run(['nft','-f','-'],nft_rules(config))
    def route_rule(self,config,remove=False):
        if config:run(['ufw',*(['--force','delete'] if remove else []),'route','allow','in','on',config['lan'],'out','on',config['wan'],'from',str(GATEWAY.network),'to','any'],check=not remove)
        if config:
            for port,protocol in [('80','tcp'),('443','tcp'),('6667','tcp'),('27015:27018','udp'),('27015:27018','tcp'),('28015:28018','tcp'),('53','udp'),('53','tcp'),('67','udp')]:
                run(['ufw',*(['--force','delete'] if remove else []),'allow','in','on',config['lan'],'from','any' if port=='67' else str(GATEWAY.network),'to','any','port',port,'proto',protocol],check=not remove)
    def add_connection(self,args):
        ident=secrets.token_hex(8);name='lisp-'+ident
        run(['nmcli','connection','add','con-name',name,*args])
        uid=run(['nmcli','-g','connection.uuid','connection','show',name]).strip()
        self.pending['newIds'].append(uid);self.save('pending.json',self.pending);return uid
    def apply(self,data):
        if self.pending:raise ValueError('A change is already pending.')
        plan=self.plans.pop(data.get('plan',''),None)
        if not plan or plan['expires']<time.time() or data.get('confirm')!='APPLY':raise ValueError('Preview again, then confirm Apply.')
        # Revalidate interfaces immediately before any mutation.
        check=self.plan(plan);rechecked=self.plans.pop(check['plan']);
        if rechecked['wan']!=plan['wan']:raise ValueError('The upstream changed. Preview the network again.')
        affected=list(set(plan['ports']+self.state.get('ports',[])))
        if self.state.get('lan') and self.state['lan'] not in affected:affected.append(self.state['lan'])
        checkpoint=self.checkpoint(affected)
        original=dict(self.state.get('original',{}))
        for port in affected:
            if port not in original:original[port]=run(['nmcli','-g','GENERAL.CON-UUID','device','show',port],check=False).stdout.strip()
        self.pending={'id':secrets.token_urlsafe(24),'expires':time.time()+120,'checkpoint':checkpoint,'old':self.state.copy(),'newIds':[],'oldForward':run(['sysctl','-n','net.ipv4.ip_forward']).strip()}
        self.save('pending.json',self.pending)
        try:
            old=self.state
            if old.get('main'):run(['nmcli','--wait','15','connection','down','uuid',old['main']],check=False)
            lan='lisp-lan' if plan['mode']=='bridge' else plan['ports'][0]
            kind=['type','bridge','ifname',lan,'bridge.stp','yes'] if plan['mode']=='bridge' else ['type','ethernet','ifname',lan]
            main=self.add_connection(kind+['ipv4.method','shared','ipv4.addresses',str(GATEWAY),'ipv4.never-default','yes','ipv6.method','disabled','connection.autoconnect','yes'])
            if plan['mode']=='bridge':
                for port in plan['ports']:
                    uid=self.add_connection(['type','ethernet','ifname',port,'controller',main,'port-type','bridge','connection.autoconnect','yes'])
                    run(['nmcli','--wait','15','connection','up','uuid',uid])
            run(['nmcli','--wait','20','connection','up','uuid',main])
            new={'lan':lan,'wan':plan['wan'],'mode':plan['mode'],'ports':plan['ports'],'main':main,'connections':list(self.pending['newIds']),'original':original,'internet':False,'blocked':old.get('blocked',[])}
            self.pending['new']=new;self.save('pending.json',self.pending)
            self.apply_filter(new);self.route_rule(new)
            self.state=new;self.save('settings.json',new);self.audit('apply',{'ports':plan['ports'],'mode':plan['mode']})
            return {'pending':{'id':self.pending['id'],'expires':self.pending['expires']},'message':'Confirm connectivity within two minutes, or the change rolls back.'}
        except Exception:
            self.rollback();raise
    def rollback(self):
        if not self.pending:return {'rolledBack':False}
        p=self.pending
        try:self.bus('CheckpointRollback','o',p['checkpoint'])
        except ValueError:pass # NetworkManager may already have restored its timed checkpoint.
        for uid in p['newIds']:run(['nmcli','connection','delete','uuid',uid],check=False)
        if p.get('new') and (p['new'].get('lan'),p['new'].get('wan'))!=(p['old'].get('lan'),p['old'].get('wan')):self.route_rule(p['new'],True)
        self.state=p['old'];self.apply_filter(self.state)
        if self.state.get('main'):run(['nmcli','--wait','15','connection','up','uuid',self.state['main']],check=False)
        run(['sysctl','-w','net.ipv4.ip_forward='+p['oldForward']],check=False)
        self.save('settings.json',self.state);self.pending=None;self.save('pending.json',None);self.audit('rollback',{})
        return {'rolledBack':True}
    def confirm(self,data):
        if not self.pending or data.get('id')!=self.pending['id']:raise ValueError('No matching pending change.')
        if self.pending['expires']<=time.time():self.rollback();raise ValueError('The confirmation window expired; the previous network was restored.')
        self.bus('CheckpointDestroy','o',self.pending['checkpoint']);old=self.pending['old']
        for uid in old.get('connections',[]):run(['nmcli','connection','delete','uuid',uid],check=False)
        for port in set(old.get('ports',[]))-set(self.state['ports']):
            uid=self.state['original'].get(port)
            if uid and uid!='--':run(['nmcli','--wait','15','connection','up','uuid',uid],check=False)
            else:run(['nmcli','device','disconnect',port],check=False)
        if old and (old['lan'],old['wan'])!=(self.state['lan'],self.state['wan']):self.route_rule(old,True)
        self.pending=None;self.save('pending.json',None);self.audit('confirm',{});return {'confirmed':True}
    def access(self,data):
        if self.pending:raise ValueError('Confirm the network change first.')
        if not self.state:raise ValueError('Configure the party gateway first.')
        enabled=data.get('allowed')
        if type(enabled) is not bool:raise ValueError('Choose allow or block.')
        new=json.loads(json.dumps(self.state));mac=data.get('mac')
        if mac is None:new['internet']=enabled
        else:
            if not isinstance(mac,str) or not MAC.fullmatch(mac):raise ValueError('Invalid client address.')
            known={x['mac'] for x in self.clients(self.inventory()[0]) if x['manageable']}
            if mac not in known and mac not in self.state.get('blocked',[]):raise ValueError('Choose a client on the managed party LAN.')
            blocked=set(new.get('blocked',[]));blocked.discard(mac) if enabled else blocked.add(mac);new['blocked']=sorted(blocked)
        self.apply_filter(new);self.state=new;self.save('settings.json',new);self.audit('access',{'mac':mac,'allowed':enabled});return {'updated':True}
    def dispatch(self,data):
        with self.lock:
            op=data.get('op')
            if op=='status':return self.status()
            if op=='preview':return self.plan(data)
            if op=='apply':return self.apply(data)
            if op=='confirm':return self.confirm(data)
            if op=='rollback':return self.rollback()
            if op=='access':return self.access(data)
            raise ValueError('Unsupported network operation.')
    def watchdog(self):
        while True:
            time.sleep(1)
            with self.lock:
                if self.pending and time.time()>=self.pending['expires']:
                    try:self.rollback()
                    except Exception:self.audit('rollback-failed',{});time.sleep(3)
class Request(socketserver.StreamRequestHandler):
    def handle(self):
        self.request.settimeout(60);uid=struct.unpack('3i',self.request.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))[1]
        if uid not in (0,pwd.getpwnam('lanadmin').pw_uid):return
        try:
            raw=self.rfile.readline(8193)
            if len(raw)>8192 or not raw.endswith(b'\n'):raise ValueError('Invalid request size.')
            data=json.loads(raw)
            if not isinstance(data,dict):raise ValueError('Invalid request.')
            result=self.server.controller.dispatch(data)
        except ValueError as e:result={'error':str(e)}
        except Exception:result={'error':'Network operation failed. Check the controller journal.'}
        self.wfile.write(json.dumps(result).encode()+b'\n')
class Server(socketserver.ThreadingUnixStreamServer):daemon_threads=True
if __name__=='__main__':
    os.umask(0o077);controller=Controller()
    if controller.pending:controller.rollback()
    if controller.state:controller.apply_filter(controller.state);controller.route_rule(controller.state)
    path='/run/lisp-network/control.sock';Path(path).unlink(missing_ok=True)
    server=Server(path,Request);server.controller=controller;os.chown(path,0,pwd.getpwnam('lanadmin').pw_gid);os.chmod(path,0o660)
    threading.Thread(target=controller.watchdog,daemon=True).start();server.serve_forever()
