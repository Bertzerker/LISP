"""Native ET: Legacy validation; stop only instances created by this test."""
import os,json,secrets,socket,time
from urllib.request import Request,urlopen
from urllib.parse import urlparse
BASE=os.environ.get('LISP_TEST_URL','http://192.168.8.138');HOST=urlparse(BASE).hostname
ids=[]
def api(path,data=None):
    with urlopen(Request(BASE+path,data=json.dumps(data).encode() if data is not None else None,headers={'X-LAN-Request':'1','Content-Type':'application/json'}),timeout=180) as r:return json.load(r)
def ready(ident):
    deadline=time.monotonic()+45
    while time.monotonic()<deadline:
        state=next(s for s in api('/api/servers')['servers'] if s['id']==ident)
        if state['status']=='running':return state
        assert state['status']!='failed','ET server exited: '+str(state['exitCode'])
        time.sleep(2)
    raise AssertionError('ET readiness timed out')
def packet(port,command):
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
        s.settimeout(2);s.connect((HOST,port));s.send(b'\xff\xff\xff\xff'+command.encode()+b'\n');return s.recv(32768)
def info(port):
    data=packet(port,'getstatus lisp').decode('latin1')
    assert data.startswith('\xff\xff\xff\xffstatusResponse\n')
    fields=data.splitlines()[1].split('\\');return dict(zip(fields[1::2],fields[2::2]))
def rcon(port,password,command):return packet(port,'rcon "'+password+'" '+command).decode('latin1')
try:
    catalog=next(g for g in api('/api/catalog')['games'] if g['id']=='etlegacy')
    assert {'battery','fueldump','goldrush','oasis','radar','railgun'}<=set(catalog['maps'])
    assert len(api('/api/servers')['servers'])<=2,'Need two free slots'
    for index,(mode,level,count,value) in enumerate([('objective','oasis',8,2),('stopwatch','radar',16,3)]):
        join='Join'+secrets.token_hex(8);admin='Admin'+secrets.token_hex(8)
        x=api('/api/servers',dict(game='etlegacy',mode=mode,map=level,players=count,password=join,adminPassword=admin));ids.append(x['id']);state=ready(x['id'])
        native=info(x['port']);assert native['mapname']==level and native['g_gametype']==str(value) and native['sv_maxclients']==str(count),native
        assert native['g_needpass']=='1',native
        assert join not in json.dumps(state) and admin not in json.dumps(state)
        response=rcon(x['port'],admin,'echo LISP_ET_RCON_OK');assert 'LISP_ET_RCON_OK' in response
        time.sleep(.6)
        response=rcon(x['port'],'WrongTestPassword','echo LISP_ET_BAD');assert 'Bad rconpassword' in response and 'LISP_ET_BAD' not in response
        time.sleep(.6)
        assert join in rcon(x['port'],admin,'g_password')
        time.sleep(.6)
        assert admin in rcon(x['port'],admin,'refereePassword')
        print('PASS ET:',level,mode,count,'slots; native password flag, correct/wrong RCON, join/referee settings and API secret exclusion',flush=True)
    states=api('/api/servers')['servers'];assert len({s['port'] for s in states if s['id'] in ids})==2
    api('/api/servers/'+ids[0]+'/stop',{});ids.pop(0);assert ready(ids[0])['status']=='running'
    print('PASS two isolated ET instances and independent stopping',flush=True)
    # Check the remaining mode options against native serverinfo with one free slot.
    for mode,value in [('lms',5),('mapvote',6)]:
        x=api('/api/servers',dict(game='etlegacy',mode=mode,map='goldrush',players=8,password='',adminPassword=''));ids.append(x['id']);ready(x['id'])
        native=info(x['port']);assert native['g_gametype']==str(value),native
        assert native['g_needpass']=='0'
        print('PASS ET:',mode,'native game type and public match without passwords',flush=True)
        api('/api/servers/'+x['id']+'/stop',{});ids.remove(x['id'])
finally:
    for ident in ids:api('/api/servers/'+ident+'/stop',{})
    print('Removed only ET test matches',flush=True)
