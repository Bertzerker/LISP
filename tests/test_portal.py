import json,time,socket,os
from urllib.request import urlopen,Request
from urllib.error import HTTPError
BASE=os.environ.get('LISP_TEST_URL','http://192.168.8.138')
def api(path,data=None,headers=None):
    return json.load(urlopen(Request(BASE+path,data=json.dumps(data).encode() if data is not None else None,headers=headers or {'Content-Type':'application/json','X-LAN-Request':'1'}),timeout=20))
def rejects(data,headers=None):
    try: api('/api/servers',data,headers); raise AssertionError('Invalid request was accepted')
    except HTTPError as e: assert e.code in (400,403)
catalog=api('/api/catalog'); maps=catalog['games'][0]['maps']
assert maps and 'campgrounds' in maps
rejects({'game':'quakelive','map':'../../etc/passwd','mode':'ffa','players':8})
rejects({'game':'quakelive','map':'campgrounds','mode':'ffa','players':1000})
rejects({'game':'quakelive','map':'campgrounds','mode':'ffa','players':8},{'Content-Type':'application/json','X-LAN-Request':'1','Origin':'http://untrusted.example'})
rejects({'game':'quakelive','map':'campgrounds','mode':'ffa','players':8},{'Content-Type':'application/json'})
ids=[]
try:
    for mode,players in [('ffa',8),('duel',2)]:
        x=api('/api/servers',{'game':'quakelive','map':'campgrounds','mode':mode,'players':players});ids.append(x['id'])
    deadline=time.monotonic()+60
    while time.monotonic()<deadline:
        servers=[s for s in api('/api/servers')['servers'] if s['id'] in ids]
        if any(s['status']=='failed' for s in servers): raise AssertionError(json.dumps(servers))
        if len(servers)==2 and all(s['status']=='running' for s in servers): break
        time.sleep(3)
    else: raise AssertionError('Servers did not become ready: '+json.dumps(servers))
    assert len({s['port'] for s in servers})==2
    for server in servers:
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
            sock.settimeout(3);sock.sendto(b'\xff\xff\xff\xffgetchallenge 6789',(__import__('urllib.parse',fromlist=['urlparse']).urlparse(BASE).hostname,server['port']))
            info=sock.recv(8192)
            assert b'challengeResponse ' in info or b'No Steam auth token.' in info
        print('LAN UDP response:',server['port'],server['mode'],server['players'])
    api('/api/servers/'+ids[0]+'/stop',{})
    remaining=api('/api/servers')['servers']
    assert not any(s['id']==ids[0] for s in remaining)
    assert any(s['id']==ids[1] and s['status']=='running' for s in remaining)
    print('PASS: two independent instances, LAN UDP reachability, stop isolation, input validation and cross-origin protection;',len(maps),'installed maps')
finally:
    for ident in ids:
        try: api('/api/servers/'+ident+'/stop',{})
        except HTTPError as e:
            if e.code!=400: raise

