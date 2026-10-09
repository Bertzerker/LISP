#!/usr/bin/python3
import json,os,re,shutil,signal,socket,subprocess,threading,time,uuid,pty,fcntl,termios,struct
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlparse
from adapters import ROOT,registry,private_file
from account_client import check,call
from server_metrics import EngineMeter
PORTS=range(27015,27051)
MAX_SERVERS=6
MONITOR_ENABLED=os.environ.get("LISP_MONITOR_ENABLED")=="1"
ALLOWED_HOSTS=set(os.environ.get('LISP_ALLOWED_HOSTS','192.168.8.138,127.0.0.1,localhost').split(','))
lock=threading.RLock();instances={};records={}
RECORDS=ROOT/'records'
for record_path in RECORDS.glob('*.json'):
    try:
        value=json.loads(record_path.read_text())
        if re.fullmatch(r'[a-f0-9]{12}',record_path.stem) and value['public']['id']==record_path.stem:records[record_path.stem]=value
    except (OSError,ValueError,KeyError):pass

DELETED=ROOT/'deleted-records';deleted_records={}
for record_path in DELETED.glob('*.json'):
    try:
        value=json.loads(record_path.read_text())
        if re.fullmatch(r'[a-f0-9]{12}',record_path.stem) and value['public']['id']==record_path.stem:deleted_records[record_path.stem]=value
    except (OSError,ValueError,KeyError):pass

def save_record(ident,value):
    RECORDS.mkdir(parents=True,exist_ok=True,mode=0o700);RECORDS.chmod(0o700)
    temporary=RECORDS/(ident+'.tmp');private_file(temporary,json.dumps(value,separators=(',',':'))+'\n');temporary.replace(RECORDS/(ident+'.json'));records[ident]=value

def permitted(public,actor):return bool(actor and (actor['role']=='admin' or actor['id']==public.get('ownerId')))


def password(value):
    if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9 !@#$%^&*()_+=.,:?-]{0,64}',value):
        raise ValueError('Passwords may use up to 64 letters, numbers, spaces and !@#$%^&*()_+=.,:?- (no quotes, slashes or semicolons).')
    return value

def load_details(item,actor):
    value={'load':item.get('load'),'loadError':item.get('loadError')}
    if permitted(item['public'],actor):value['billing']=item.get('credit')
    return value

def pending_usage(data):
    directory=ROOT/'usage-pending';directory.mkdir(mode=0o700,exist_ok=True);directory.chmod(0o700)
    path=directory/(data['runId']+'.json');temporary=path.with_suffix('.tmp');private_file(temporary,json.dumps(data)+'\n');temporary.replace(path)
    return path

def settle_pending():
    for path in (ROOT/'usage-pending').glob('*.json'):
        try:
            data=json.loads(path.read_text());call(data);path.unlink()
        except Exception:pass

def sample_usage(ident,item,final=False):
    cpu,rx,tx,load=item['meter'].sample()
    item['load']=load;item.pop('loadError',None)
    data={'op':'credit-charge','runId':item['runId'],'serverId':ident,'cpuUs':cpu,'rxBytes':rx,'txBytes':tx}
    pending=pending_usage(data);value=call(data);pending.unlink(missing_ok=True)
    policy=value['creditPolicy']
    value['tokensPerHour']=round(load['cpuAveragePercent']/100*60/policy['cpuMinutesPerToken']+load['networkAverageBytesPerSecond']*3600/(policy['networkGiBPerToken']*1073741824),6) if not value['creditExempt'] else 0
    item['credit']=value
    if final:
        record=json.loads(json.dumps(records[ident]));record['lastLoad']=load;record['lastBilling']=value;save_record(ident,record)
    return value

def monitor_tick():
    exhausted=set()
    with lock:
        settle_pending()
        for ident,item in list(instances.items()):
            if not item.get('meter'):continue
            try:
                value=sample_usage(ident,item)
                if value['limitReached']:exhausted.add(item['public']['ownerId'])
                item.pop('monitorFailureSince',None)
            except Exception:
                item['loadError']='Usage monitoring unavailable; accounting is delayed.'
                since=item.setdefault('monitorFailureSince',time.monotonic())
                if time.monotonic()-since>=30 and not (item.get('credit') or {}).get('creditExempt'):exhausted.add(item['public']['ownerId'])
        for ident,item in list(instances.items()):
            if item['public']['ownerId'] in exhausted:
                try:
                    record=json.loads(json.dumps(records[ident]));record['public']['stopReason']='Credit limit reached or usage monitoring unavailable. Add credits or ask an admin before restarting.';save_record(ident,record)
                    stop(ident)
                except Exception:print('Could not save/stop metered instance '+ident,flush=True)

def monitor_loop():
    while True:
        time.sleep(5)
        monitor_tick()


def valid_port(adapter,port):
    if type(port) is not int or port not in PORTS:return False
    if adapter.engine=='sevendays' and port+2 not in PORTS:return False
    if (adapter.engine in ('unreal','zomboid','brink') or adapter.id=='t5') and port+1 not in PORTS:return False
    return True

def free_port(adapter,port):
    # Caller holds lock: include ports of starting engines before they bind sockets.
    if not valid_port(adapter,port):return False
    reserved=adapter.reserved_ports(port)
    used={(number,typ) for item in instances.values() if item['process'].poll() is None for number,typ in item['adapter'].reserved_ports(item['port'])}
    if any(pair in used for pair in reserved):return False
    probes=[]
    try:
        for number,typ in reserved:
            probe=socket.socket(socket.AF_INET,typ);probes.append(probe);probe.bind(('0.0.0.0',number))
        return True
    except OSError:return False
    finally:
        for probe in probes:probe.close()

def choose_port(adapter,requested):
    if requested is not None and not valid_port(adapter,requested):raise ValueError('Choose a valid port for this game.')
    for candidate in ([requested] if requested is not None else PORTS):
        if free_port(adapter,candidate):return candidate
    raise ValueError('That port is busy. Choose automatic or another port.')

def listing(actor=None):
    result=[]
    with lock:
        installed=registry() if any(ident not in instances and permitted(record['public'],actor) for ident,record in records.items()) else {}
        for ident,item in instances.items():
            code=item['process'].poll();info=item['adapter'].query(item['port']) if code is None else None
            # One dropped UDP reply must not turn an established match back into startup.
            now=time.monotonic()
            if info is not None:item['lastInfo']=info;item['lastReady']=now
            elif code is None and now-item.get('lastReady',0)<20:info=item.get('lastInfo')
            result.append({**item['public'],**load_details(item,actor),'canStop':permitted(item['public'],actor),'canRestart':permitted(item['public'],actor),'canDelete':False,'canChangePort':False,'status':'running' if info is not None else ('starting' if code is None else 'failed'),'connected':info.get('clients') if info else None,'currentMap':info.get('mapname',item['public']['map']) if info else item['public']['map'],'exitCode':code})
        for ident,record in records.items():
            if ident not in instances:
                row={**record['public'],'load':record.get('lastLoad'),**({'billing':record.get('lastBilling')} if permitted(record['public'],actor) else {}),'canStop':False,'canRestart':permitted(record['public'],actor),'canDelete':permitted(record['public'],actor),'canChangePort':False,'status':'stopped','connected':0,'currentMap':record['public']['map'],'exitCode':None}
                if permitted(record['public'],actor):
                    adapter=installed.get(record['public']['gameId'])
                    if adapter:
                        row['canChangePort']=True
                        row['portOptions']=[{'port':port,'available':free_port(adapter,port)} for port in PORTS if valid_port(adapter,port)]
                        row['portBusy']=not any(option['port']==row['port'] and option['available'] for option in row['portOptions'])
                result.append(row)
    return result

def start(data,actor,existing=None):
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
    if ids and adapter.engine not in ('quake','sevendays'):raise ValueError('Steam ID admin entries are supported for Quake Live and 7 Days to Die only.')
    with lock:
        active=[i for i in instances.values() if i['process'].poll() is None]
        if len(active)>=MAX_SERVERS:raise ValueError('Six servers are already running. Stop one first.')
        if adapter.engine in ('zomboid','sevendays'):
            world=data.get('world','new')
            if world!='new' and any(i['public'].get('worldId')==world for i in active):raise ValueError('That world is already running. Choose another world.')
        owner_id=existing['public']['ownerId'] if existing else actor['id']
        run_id=uuid.uuid4().hex
        if MONITOR_ENABLED:settle_pending()
        credit=call({'op':'credit-authorize','ownerId':owner_id,'runId':run_id,'serverId':existing['public']['id'] if existing else None}) if MONITOR_ENABLED else None
        port=choose_port(adapter,data.get('port'))
        ident=existing['public']['id'] if existing else uuid.uuid4().hex[:12];home=ROOT/'instances'/ident
        if existing and home.exists():
            if home.is_symlink() or home.resolve().parent!=(ROOT/'instances').resolve():raise ValueError('Invalid instance folder.')
            # Inspect only the explicitly requested stopped entry. Never move a
            # folder referenced by a live engine; retain stale private logs.
            for cmdline in __import__('pathlib').Path('/proc').glob('[0-9]*/cmdline'):
                try:
                    if str(home).encode() in cmdline.read_bytes():raise ValueError('This instance still has a running process. Retry after it stops.')
                except (OSError,PermissionError):pass
            archive=ROOT/'retired-instances';archive.mkdir(mode=0o700,exist_ok=True)
            home.rename(archive/(ident+'-'+uuid.uuid4().hex[:8]))
        home.mkdir(mode=0o700,parents=True)
        meter=None
        try:
            if MONITOR_ENABLED:meter=EngineMeter(ident,adapter.reserved_ports(port),run_id)
            if hasattr(adapter,'prepare_request'):
                data={**data,'_actor':{'id':actor['id'],'role':actor['role']}}
                if adapter.engine=='cod':data={**data,'_queryClients':[actor['ip']]}
                args,cwd=adapter.prepare_request(home,port,mode,level,players,join,admin,ids,mutators,data)
            else:args,cwd=adapter.prepare(home,port,mode,level,players,join,admin,ids,mutators)
            if meter:args=meter.command(args)
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
            if meter:meter.close()
            shutil.rmtree(home);raise
        public={'id':ident,'game':adapter.name,'gameId':game,'mode':mode,'modeName':adapter.modes()[mode],'players':players,'map':level,'port':port,'started':int(time.time()),'passwordProtected':bool(join),'adminEnabled':bool(admin or ids),'mutators':mutators,'adminKind':'steamid-zmq' if adapter.engine=='quake' else 'unreal' if adapter.engine=='unreal' else 'swbf2' if adapter.engine=='swbf2' else 'etlegacy' if adapter.id=='etlegacy' else 'zomboid' if adapter.id=='zomboid' else 'rcon','inGameAdminEnabled':bool(ids) if adapter.engine=='quake' else bool(admin),'adminPort':(port+1000 if adapter.engine=='quake' else port) if admin else None}
        if hasattr(adapter,'public_details'):public.update(adapter.public_details())
        public['billingRunId']=run_id
        public.update(ownerId=existing['public']['ownerId'] if existing else actor['id'],ownerName=existing['public']['ownerName'] if existing else actor['name'])
        preset={k:v for k,v in data.items() if not k.startswith('_')};preset['port']=port
        if public.get('worldId'):preset['world']=public['worldId']
        instances[ident]={'public':public,'process':proc,'adapter':adapter,'port':port,'home':home,'log':log,'meter':meter,'runId':run_id,'credit':credit}
        try:save_record(ident,{'public':public,'launch':preset})
        except Exception:
            stop(ident,actor);raise
        return {'id':ident,'port':port}

def stop(ident,actor=None):
    with lock:
        if ident not in instances:
            if ident not in records:raise ValueError('Server not found.')
            if actor is not None and not permitted(records[ident]['public'],actor):raise PermissionError('Only the creator or an administrator can stop this server.')
            return
        item=instances[ident];proc=item['process']
        if actor is not None and actor['role']!='admin' and actor['id']!=item['public'].get('ownerId'):raise PermissionError('Only the creator or an administrator can stop this server.')
        if proc.poll() is None:
            if hasattr(item['adapter'],'stop_process'):item['adapter'].stop_process(proc)
            else:
                os.killpg(proc.pid,signal.SIGTERM)
                try:proc.wait(timeout=8)
                except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=3)
        if hasattr(item['adapter'],'after_stop'):item['adapter'].after_stop()
        if item.get('meter'):
            try:sample_usage(ident,item,final=True)
            except Exception:print('Final usage accounting pending for '+ident,flush=True)
            item['meter'].close()
        item['log'].close()
        home=item['home'].resolve()
        if home.parent!=(ROOT/'instances').resolve() or home.name!=ident:raise RuntimeError('Invalid instance cleanup path')
        shutil.rmtree(home)
        del instances[ident]

def restart(ident,actor):
    with lock:
        if ident not in records:raise ValueError('Server not found.')
        record=records[ident]
        if not permitted(record['public'],actor):raise PermissionError('Only the creator or an administrator can restart this server.')
        if ident in instances:stop(ident,actor)
        return start(dict(record['launch']),actor,existing=record)

def change_port(ident,requested,actor):
    with lock:
        if ident not in records:raise ValueError('Server not found.')
        record=records[ident]
        if not permitted(record['public'],actor):raise PermissionError('Only the creator or an administrator can change this server port.')
        if ident in instances:raise ValueError('Stop the server before changing its port.')
        adapter=registry().get(record['public']['gameId'])
        if adapter is None:raise ValueError('This game is no longer installed.')
        port=choose_port(adapter,requested)
        updated=json.loads(json.dumps(record));public=updated['public'];old=public['port']
        public['port']=port;updated['launch']['port']=port
        for key in ('adminPort','directPort'):
            previous=public.get(key)
            if previous is not None:public[key]=port+(previous-old)
        if record['public'].get('adminPort') is not None and isinstance(public.get('adminInstructions'),str):
            public['adminInstructions']=re.sub(r'(?<!\d)'+str(record['public']['adminPort'])+r'(?!\d)',str(public['adminPort']),public['adminInstructions'])
        save_record(ident,updated)
        return {'id':ident,'port':port}

def delete_entry(ident,actor):
    with lock:
        if ident not in records:raise ValueError('Server not found.')
        if not permitted(records[ident]['public'],actor):raise PermissionError('Only the creator or an administrator can delete this entry.')
        if ident in instances:raise ValueError('Stop the server before deleting its entry.')
        DELETED.mkdir(mode=0o700,exist_ok=True);DELETED.chmod(0o700)
        (RECORDS/(ident+'.json')).replace(DELETED/(ident+'.json'))
        deleted_records[ident]=records.pop(ident)

def restore_entry(ident,actor):
    with lock:
        if ident not in deleted_records:raise ValueError('Deleted entry not found.')
        record=deleted_records[ident]
        if not permitted(record['public'],actor):raise PermissionError('Only the creator or an administrator can restore this entry.')
        if ident in records or ident in instances:raise ValueError('That entry already exists.')
        RECORDS.mkdir(mode=0o700,exist_ok=True)
        (DELETED/(ident+'.json')).replace(RECORDS/(ident+'.json'))
        records[ident]=deleted_records.pop(ident)

def deleted_listing(actor):
    with lock:
        return [{**record['public'],'status':'deleted','canStop':False,'canRestart':False,'canDelete':False,'canRestore':True,'canChangePort':False,'connected':0,'currentMap':record['public']['map']} for record in deleted_records.values() if permitted(record['public'],actor)]

def catalog_for(adapter,actor):
    result=adapter.catalog()
    if result.get('persistentWorlds'):
        result['worlds']=[{k:w[k] for k in ('id','name','mode','map')} for w in result['worlds'] if actor['role']=='admin' or w.get('ownerId')==actor['id']]
    return result

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
            if self.path=='/api/catalog':self.reply(200,{'games':[catalog_for(a,actor) for a in registry().values()],'maxServers':MAX_SERVERS,'ports':list(PORTS)})
            elif self.path=='/api/servers':self.reply(200,{'servers':listing(actor),'deletedServers':deleted_listing(actor),'credits':call({'op':'credit-status','ownerId':actor['id']}) if MONITOR_ENABLED else None})
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
            elif re.fullmatch(r'/api/servers/[a-f0-9]{12}/port',self.path):
                if 'port' not in data:raise ValueError('Choose a port or automatic.')
                result=change_port(self.path.split('/')[3],data['port'],actor)
            elif re.fullmatch(r'/api/servers/[a-f0-9]{12}/restart',self.path):result=restart(self.path.split('/')[3],actor)
            elif re.fullmatch(r'/api/servers/[a-f0-9]{12}/delete',self.path):delete_entry(self.path.split('/')[3],actor);result={'deleted':True,'worldKept':True}
            elif re.fullmatch(r'/api/servers/[a-f0-9]{12}/restore',self.path):restore_entry(self.path.split('/')[3],actor);result={'restored':True}
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
    if MONITOR_ENABLED:threading.Thread(target=monitor_loop,daemon=True).start()
    ThreadingHTTPServer(('127.0.0.1',8787),Handler).serve_forever()

