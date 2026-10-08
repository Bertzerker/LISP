#!/usr/bin/python3
import json,os,re,shutil,signal,socket,subprocess,threading,time,uuid,pty,fcntl,termios,struct
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlparse
from adapters import ROOT,registry
from account_client import check
PORTS=range(27015,27019)
MAX_SERVERS=4
ALLOWED_HOSTS=set(os.environ.get('LISP_ALLOWED_HOSTS','192.168.8.138,127.0.0.1,localhost').split(','))
lock=threading.RLock();instances={}

def password(value):
    if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9 !@#$%^&*()_+=.,:?-]{0,64}',value):
        raise ValueError('Passwords may use up to 64 letters, numbers, spaces and !@#$%^&*()_+=.,:?- (no quotes, slashes or semicolons).')
    return value

def listing(actor=None):
    result=[]
    with lock:
        for ident,item in instances.items():
            code=item['process'].poll();info=item['adapter'].query(item['port']) if code is None else None
            # One dropped UDP reply must not turn an established match back into startup.
            now=time.monotonic()
            if info is not None:item['lastInfo']=info;item['lastReady']=now
            elif code is None and now-item.get('lastReady',0)<20:info=item.get('lastInfo')
            result.append({**item['public'],'canStop':bool(actor and (actor['role']=='admin' or actor['id']==item['public'].get('ownerId'))),'status':'running' if info is not None else ('starting' if code is None else 'failed'),'connected':info.get('clients') if info else None,'currentMap':info.get('mapname',item['public']['map']) if info else item['public']['map'],'exitCode':code})
    return result

def start(data,actor):
    adapters=registry();game=data.get('game')
    if not isinstance(game,str) or game not in adapters:raise ValueError('Choose an installed game.')
    adapter=adapters[game];mode=data.get('mode');level=data.get('map');players=data.get('players')
    if not isinstance(mode,str) or mode not in adapter.modes() or level not in adapter.maps():raise ValueError('Choose an installed map and valid mode.')
    if type(players) is not int or players not in adapter.players(mode):raise ValueError('Choose a supported player limit for this mode.')
    if hasattr(adapter,'map_valid') and not adapter.map_valid(mode,level):raise ValueError('Choose a map for the selected game mode.')
    mutators=data.get('mutators',[])
    if not isinstance(mutators,list) or len(mutators)>8 or any(not isinstance(x,str) or x not in adapter.mutators() for x in mutators):raise ValueError('Choose installed mutators from the list.')
    mutators=list(dict.fromkeys(mutators))
    join=password(data.get('password',''));admin=password(data.get('adminPassword',''))
    if adapter.id=='l4d2' and join:raise ValueError('Left 4 Dead 2 join passwords break connections in this engine build. Clear the join password; the admin password is supported.')
    if adapter.id=='swbf2' and (len(join)>15 or len(admin)>15):raise ValueError('Battlefront II passwords may use at most 15 characters.')
    rawids=data.get('adminSteamIds','')
    if not isinstance(rawids,str):raise ValueError('Admin Steam IDs must be text.')
    ids=[x for x in re.split(r'[,\s]+',rawids.strip()) if x]
    if len(ids)>16 or any(not re.fullmatch(r'7656119\d{10}',x) for x in ids):raise ValueError('Enter valid 17-digit SteamID64 values separated by commas.')
    if ids and adapter.engine!='quake':raise ValueError('Steam ID admin entries are supported for Quake Live only.')
    with lock:
        active=[i for i in instances.values() if i['process'].poll() is None]
        if len(active)>=MAX_SERVERS:raise ValueError('Four servers are already running. Stop one first.')
        if adapter.id=='zomboid':
            if sum(i['adapter'].id=='zomboid' for i in active)>=2:raise ValueError('Two Zomboid worlds are already running. Stop one first.')
            world=data.get('world','new')
            if world!='new' and any(i['public'].get('worldId')==world for i in active):raise ValueError('That world is already running. Choose another world.')
        requested=data.get('port')
        if requested is not None and (type(requested) is not int or requested not in PORTS):raise ValueError('Choose a valid port.')
        used={number for i in active for number,typ in i['adapter'].reserved_ports(i['port']) if typ==socket.SOCK_DGRAM};port=None
        for candidate in ([requested] if requested is not None else PORTS):
            reserved=adapter.reserved_ports(candidate)
            if (adapter.engine in ('unreal','zomboid','brink') or adapter.id=='t5') and candidate+1 not in PORTS:continue
            if any(n in used for n,t in reserved if t==socket.SOCK_DGRAM):continue
            probes=[]
            try:
                for number,typ in reserved:
                    probe=socket.socket(socket.AF_INET,typ);probes.append(probe);probe.bind(('0.0.0.0',number))
                port=candidate;break
            except OSError:pass
            finally:
                for probe in probes:probe.close()
        if port is None:raise ValueError('That port is busy. Choose automatic or another port.')
        ident=uuid.uuid4().hex[:12];home=ROOT/'instances'/ident;home.mkdir(mode=0o700,parents=True)
        try:
            if hasattr(adapter,'prepare_request'):
                if adapter.engine=='cod':data={**data,'_queryClients':[actor['ip']]}
                args,cwd=adapter.prepare_request(home,port,mode,level,players,join,admin,ids,mutators,data)
            else:args,cwd=adapter.prepare(home,port,mode,level,players,join,admin,ids,mutators)
            log=(home/'server.log').open('ab');os.chmod(home/'server.log',0o600)
            child_env=os.environ.copy()
            if adapter.id in ('l4d2','tf2','hl2dm'):
                app={'l4d2':'550','tf2':'440','hl2dm':'320'}[adapter.id];child_env.update(HOME=str(home),SteamAppId=app,SteamGameId=app)
            if adapter.id=='zomboid':
                game_dir=home/'game'
                child_env.update(HOME=str(home),LD_LIBRARY_PATH=str(game_dir/'linux64')+':'+str(game_dir)+':'+str(game_dir/'jre64/lib'))
            if adapter.id=='jabroni':
                # This engine's Linux console expects a terminal with real dimensions.
                master,slave=pty.openpty()
                fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',24,120,0,0))
                try:proc=subprocess.Popen(args,cwd=cwd,env=child_env,stdin=slave,stdout=slave,stderr=slave,start_new_session=True)
                except Exception:
                    os.close(master);raise
                finally:os.close(slave)
                def drain(fd,destination):
                    try:
                        while True:
                            chunk=os.read(fd,65536)
                            if not chunk:break
                            destination.write(chunk);destination.flush()
                    except (OSError,ValueError):pass
                    finally:os.close(fd)
                threading.Thread(target=drain,args=(master,log),daemon=True).start()
            else:
                proc=subprocess.Popen(args,cwd=cwd,env=child_env,stdin=subprocess.PIPE if adapter.engine=='zomboid' else subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        except Exception:
            shutil.rmtree(home);raise
        public={'id':ident,'game':adapter.name,'gameId':game,'mode':mode,'modeName':adapter.modes()[mode],'players':players,'map':level,'port':port,'started':int(time.time()),'passwordProtected':bool(join),'adminEnabled':bool(admin or ids),'mutators':mutators,'adminKind':'steamid-zmq' if adapter.engine=='quake' else 'unreal' if adapter.engine=='unreal' else 'swbf2' if adapter.engine=='swbf2' else 'etlegacy' if adapter.id=='etlegacy' else 'zomboid' if adapter.id=='zomboid' else 'rcon','inGameAdminEnabled':bool(ids) if adapter.engine=='quake' else bool(admin),'adminPort':(port+1000 if adapter.engine=='quake' else port) if admin else None}
        if hasattr(adapter,'public_details'):public.update(adapter.public_details())
        public.update(ownerId=actor['id'],ownerName=actor['name'])
        instances[ident]={'public':public,'process':proc,'adapter':adapter,'port':port,'home':home,'log':log}
        return {'id':ident,'port':port}

def stop(ident,actor=None):
    with lock:
        if ident not in instances:raise ValueError('Server not found.')
        item=instances[ident];proc=item['process']
        if actor is not None and actor['role']!='admin' and actor['id']!=item['public'].get('ownerId'):raise PermissionError('Only the creator or an administrator can stop this server.')
        if proc.poll() is None:
            if hasattr(item['adapter'],'stop_process'):item['adapter'].stop_process(proc)
            else:
                os.killpg(proc.pid,signal.SIGTERM)
                try:proc.wait(timeout=8)
                except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=3)
        if hasattr(item['adapter'],'after_stop'):item['adapter'].after_stop()
        item['log'].close()
        home=item['home'].resolve()
        if home.parent!=(ROOT/'instances').resolve() or home.name!=ident:raise RuntimeError('Invalid instance cleanup path')
        shutil.rmtree(home)
        del instances[ident]

class Handler(BaseHTTPRequestHandler):
    def allowed_host(self):
        return urlparse('//'+self.headers.get('Host','')).hostname in ALLOWED_HOSTS
    def reply(self,code,value):
        payload=json.dumps(value).encode();self.send_response(code)
        self.send_header('Content-Type','application/json');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload)
    def do_GET(self):
        if not self.allowed_host():self.reply(403,{'error':'Use the LAN server address.'});return
        try:
            actor=check(self.headers)
            if self.path=='/api/catalog':self.reply(200,{'games':[a.catalog() for a in registry().values()],'maxServers':MAX_SERVERS,'ports':list(PORTS)})
            elif self.path=='/api/servers':self.reply(200,{'servers':listing(actor)})
            else:self.reply(404,{'error':'Not found'})
        except PermissionError as e:self.reply(401,{'error':str(e)})
    def do_POST(self):
        origin=self.headers.get('Origin')
        if not self.allowed_host() or self.headers.get('X-LAN-Request')!='1' or (origin and urlparse(origin).netloc!=self.headers.get('Host')):
            self.reply(403,{'error':'Open the LAN portal to manage servers.'});return
        try:
            actor=check(self.headers,write=True)
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=4096:raise ValueError('Invalid request size.')
            data=json.loads(self.rfile.read(length))
            if not isinstance(data,dict):raise ValueError('Invalid request.')
            if self.path=='/api/servers':result=start(data,actor)
            elif re.fullmatch(r'/api/servers/[a-f0-9]{12}/stop',self.path):stop(self.path.split('/')[3],actor);result={'stopped':True}
            else:self.reply(404,{'error':'Not found'});return
            self.reply(200,result)
        except PermissionError as e:self.reply(403,{'error':str(e)})
        except (ValueError,TypeError) as e:self.reply(400,{'error':str(e)})
        except Exception as e:
            # Never log request bodies or configuration values (passwords).
            print(type(e).__name__,flush=True);self.reply(500,{'error':'Could not launch the game. Check its private server log.'})

if __name__=='__main__':
    os.umask(0o077)
    def shutdown(signum,frame):
        for ident in list(instances):
            try:stop(ident)
            except Exception:print('Could not finish saving an instance before controller shutdown.',flush=True)
        raise SystemExit(0)
    signal.signal(signal.SIGTERM,shutdown)
    signal.signal(signal.SIGINT,shutdown)
    ThreadingHTTPServer(('127.0.0.1',8787),Handler).serve_forever()

