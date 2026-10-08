#!/usr/bin/python3
"""Real Bracket/SMF integration in loopback-only validation databases.

Requires the private validation runtime prepared by the deployment operator.
Never run against production: all credentials/users/events are test-local.
"""
import http.cookiejar,json,os,pathlib,secrets,socketserver,sys,threading,time,urllib.request,urllib.error
sys.path.insert(0,'/opt/lan-portal')
config=json.loads(pathlib.Path(os.environ['LISP_COMMUNITY_CONFIG']).read_text())
assert config['forumDatabase']=='lisp_forum_validation'
assert config['bracketUrl']=='http://127.0.0.1:8794/'
assert config['forumUrl']=='http://127.0.0.1:8795/bridge'
assert '/validation' in os.environ['LISP_COMMUNITY_DIR']
from accounts import Accounts
import community
# Hard boundary even if a future deployment accidentally loads an old client.
real_urlopen=urllib.request.urlopen
def validation_urlopen(request,*args,**kwargs):
    url=request.full_url if isinstance(request,urllib.request.Request) else request
    if not any(url.startswith(prefix) for prefix in ['http://127.0.0.1:8794/','http://127.0.0.1:8795/','http://127.0.0.1:8796/']):raise AssertionError('Validation attempted a non-validation endpoint')
    return real_urlopen(request,*args,**kwargs)
community.urlopen=validation_urlopen
device={'ip':'127.0.0.1','mac':'02:00:00:00:00:01'}
auth=Accounts(pathlib.Path(os.environ['LISP_COMMUNITY_DIR'])/('accounts-'+secrets.token_hex(4)),lookup=lambda ip:device if ip=='127.0.0.1' else (_ for _ in ()).throw(PermissionError('Wrong test interface')))
password=secrets.token_urlsafe(24)
auth.create('ValidationAdmin',password,device,'admin');auth.create('ValidationPlayer',password,device)
class Local(socketserver.StreamRequestHandler):
    def handle(self):
        try:
            d=json.loads(self.rfile.readline(4097));op=d['op']
            if op=='community-users':r={'users':auth.community_users()}
            elif op=='session':r=auth.session(d['token'],d['ip'],d.get('csrf'),False,d.get('admin',False))
            elif op=='verify-password':r=auth.verify_forum_password(auth.session(d['token'],d['ip']),d.get('password'))
            else:raise ValueError('Unsupported test operation')
        except Exception as e:r={'error':str(e)}
        self.wfile.write(json.dumps(r).encode()+b'\n')
sock=os.environ['LISP_ACCOUNT_SOCKET']
if pathlib.Path(sock).exists():pathlib.Path(sock).unlink()
local=socketserver.ThreadingUnixStreamServer(sock,Local);os.chmod(sock,0o660);threading.Thread(target=local.serve_forever,daemon=True).start()
import community_server as app
app.urlopen=validation_urlopen
app.games=lambda headers:{'quakelive':'Quake Live','sof2':'Soldier of Fortune II'}
http_server=app.ThreadingHTTPServer(('127.0.0.1',8796),app.Handler);threading.Thread(target=http_server.serve_forever,daemon=True).start()
threading.Thread(target=app.background,daemon=True).start()
class Client:
    def __init__(self,name):
        self.token,self.user=auth.login(name,password,'127.0.0.1');self.csrf=self.user['csrf'];self.jar=http.cookiejar.CookieJar();self.opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))
    def req(self,path,data=None,method=None,csrf=True,forum=False):
        headers={'X-Forwarded-Proto':'https','X-Real-IP':'127.0.0.1','Host':'localhost','X-LAN-Request':'1','Cookie':'lisp_session='+self.token,'Content-Type':'application/json'}
        if csrf:headers['X-CSRF-Token']=self.csrf
        url=('http://127.0.0.1:8795' if forum else 'http://127.0.0.1:8796')+path
        with self.opener.open(urllib.request.Request(url,json.dumps(data).encode() if data is not None else None,headers=headers,method=method),timeout=30) as r:
            body=r.read();return json.loads(body) if 'application/json' in r.headers.get('Content-Type','') else body.decode()
    def denied(self,path,data=None,method=None,csrf=True):
        try:self.req(path,data,method,csrf);raise AssertionError('Unexpected access: '+path)
        except urllib.error.HTTPError as e:assert e.code in (400,401,403),(path,e.code)
def wait(fn,seconds=70):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        result=fn()
        if result:return result
        time.sleep(2)
    raise AssertionError('Automatic publication did not finish')
try:
    a=Client('ValidationAdmin');p=Client('ValidationPlayer')
    p.denied('/community-api/create',{'name':'forged'});p.denied('/bracket-api/clubs',{'name':'forged'});a.denied('/community-api/create',{'name':'forged'},csrf=False)
    for path in ['/bracket-api/token','/bracket-api/users/register','/bracket-api/users/1']:a.denied(path)
    ident=a.req('/community-api/create',{'name':'Validation LAN Cup','games':['quakelive','sof2'],'deadline':time.time()+3600,'start':time.time()+7200})['id']
    def current():return next(x for x in a.req('/community-api/tournaments')['tournaments'] if x['id']==ident)
    a.req('/community-api/vote',{'id':ident,'game':'quakelive'});p.req('/community-api/vote',{'id':ident,'game':'quakelive'});p.req('/community-api/vote',{'id':ident,'game':'sof2'})
    assert sum(x['votes'] for x in current()['options'])==2
    a.req('/community-api/close',{'id':ident});assert current()['status']=='choice';p.denied('/community-api/close',{'id':ident,'winner':'quakelive'});a.req('/community-api/close',{'id':ident,'winner':'quakelive'})
    row=wait(lambda:(x if x['status']=='ready' and x['thread'] else None) if (x:=current()) else None);bid=row['bracket'];topic=row['thread']
    print('PASS actual Bracket event, automatic SMF Tournament thread, vote change and tie handling',flush=True)
    assert p.req('/bracket-api/tournaments/'+str(bid))['data']['id']==bid
    assert 'data' in p.req('/bracket-api/tournaments/'+str(bid)+'/available_inputs')
    p.denied('/community-api/vote',{'id':ident,'game':'sof2'})
    for cli in (a,p):cli.req('/community-api/signup',{'id':ident})
    row=wait(lambda:(x if len(x['participants'])==2 and all(y['player'] and y['team'] for y in x['participants']) else None) if (x:=current()) else None)
    teams=a.req('/community-api/podium?id='+str(ident))['teams'];assert len(teams)==2
    body=p.req('/index.php?topic='+str(topic)+'.0',forum=True);assert 'Winning game:' in body and 'Live bracket' in body
    # Create and score a real, two-team single-elimination bracket.
    prefix='/bracket-api/tournaments/'+str(bid)
    a.req(prefix+'/stages',{})
    stage=a.req(prefix+'/stages')['data'][0];ranking=a.req(prefix+'/rankings')['data'][0]
    a.req(prefix+'/stage_items',{'stage_id':stage['id'],'name':'LAN Final','type':'SINGLE_ELIMINATION','team_count':2,'ranking_id':ranking['id']})
    item=a.req(prefix+'/stages')['data'][0]['stage_items'][0]
    for slot,team in zip(sorted(item['inputs'],key=lambda x:x['slot']),teams):
        a.req(prefix+'/stage_items/'+str(item['id'])+'/inputs/'+str(slot['id']),{'team_id':team['id']},method='PUT')
    a.req(prefix+'/stages/activate',{'direction':'next'})
    a.req(prefix+'/courts',{'name':'Validation game slot'})
    a.req(prefix+'/schedule_matches',{})
    stages=a.req(prefix+'/stages')['data'];match=stages[0]['stage_items'][0]['rounds'][0]['matches'][0]
    # The personal summary uses the player's mapped team in the actual schedule.
    app.PERSONAL.cache.clear()
    personal=p.req('/community-api/status')
    assert personal['forumAvailable'] and personal['tournamentAvailable'],personal
    assert personal['nextMatch']['matchId']==match['id'] and personal['nextMatch']['bracketId']==bid,personal
    assert p.req('/community-api/status?user='+str(a.user['id']))==personal
    assert personal['unreadMessages']==0 and isinstance(personal['unreadTopics'],int)
    request=urllib.request.Request('http://127.0.0.1:8796/community-api/status',headers={'X-Forwarded-Proto':'https','Host':'localhost','X-Real-IP':'127.0.0.1'})
    try:real_urlopen(request);raise AssertionError('Anonymous personal status allowed')
    except urllib.error.HTTPError as e:assert e.code in (401,403)
    print('PASS actual personal next match, forum counts, verified identity and anonymous rejection',flush=True)
    a.req(prefix+'/matches/'+str(match['id']),{'round_id':match['round_id'],'stage_item_input1_score':3,'stage_item_input2_score':1},method='PUT')
    ids=[match['stage_item_input1']['team_id'],match['stage_item_input2']['team_id']]
    p.denied('/community-api/finalize',{'id':ident,'podium':ids});a.denied('/community-api/finalize',{'id':ident,'podium':ids},csrf=False)
    a.req('/community-api/finalize',{'id':ident,'podium':ids});a.req('/community-api/finalize',{'id':ident,'podium':ids})
    wait(lambda:'Confirmed results' in p.req('/index.php?topic='+str(topic)+'.0',forum=True))
    for uid in (a.user['id'],p.user['id']):
        profile=p.req('/community-api/profile?user='+str(uid));assert len([t for t in profile['trophies'] if t['poll']==ident])==1 and not any(k in profile for k in ['ip','mac','salt','digest','role','csrf'])
        native=p.req('/index.php?action=profile;area=trophies;u='+str(uid),forum=True);assert 'Tournament trophies' in native and 'Validation LAN Cup' in native
    a.denied(prefix+'/stages',{})
    # Run the same final forum publication again: the machine event key prevents duplicates.
    job={'poll':ident,'op':'final','payload':'{}'};app.WORKER.process(job);app.WORKER.process(job)
    body=p.req('/index.php?topic='+str(topic)+'.0',forum=True);assert body.count('Confirmed results')==2
    # Native SMF uses the same test account identity; no second login.
    forum=p.req('/index.php',forum=True);assert 'ValidationPlayer' in forum and 'SMF 2.1.7' in forum
    # Insufficient attendance: zero- and one-player events need no bracket match to end.
    cancelled=a.req('/community-api/create',{'name':'Validation cancelled cup','games':['quakelive','sof2'],'deadline':time.time()+3600,'start':time.time()+7200})['id']
    def archived():return next(x for x in a.req('/community-api/tournaments?archived=1')['tournaments'] if x['id']==cancelled)
    p.denied('/community-api/delete',{'id':cancelled});a.denied('/community-api/delete',{'id':cancelled},csrf=False)
    a.req('/community-api/delete',{'id':cancelled});assert archived()['status']=='cancelled'
    assert not any(x['id']==cancelled for x in a.req('/community-api/tournaments')['tournaments'])
    a.req('/community-api/restore',{'id':cancelled});a.req('/community-api/vote',{'id':cancelled,'game':'quakelive'});a.req('/community-api/close',{'id':cancelled})
    one=wait(lambda:(x if x['status']=='ready' and x['thread'] else None) if (x:=archived()) else None)
    a.req('/community-api/signup',{'id':cancelled});wait(lambda:len(archived()['participants'])==1 and archived()['participants'][0]['team'])
    a.req('/community-api/delete',{'id':cancelled});a.req('/community-api/delete',{'id':cancelled})
    wait(lambda:'Tournament cancelled' in p.req('/index.php?topic='+str(one['thread'])+'.0',forum=True))
    a.denied('/bracket-api/tournaments/'+str(one['bracket'])+'/stages',{})
    assert len(archived()['participants'])==1 and not archived()['awards']
    assert not any(t['id']==one['bracket'] for t in a.req('/bracket-api/tournaments?filter_=ALL')['data'])
    # Native organizer deletion must also use the recoverable portal cancellation.
    a.req('/community-api/restore',{'id':cancelled})
    native_prefix='/bracket-api/tournaments/'+str(one['bracket'])
    a.req(native_prefix,method='DELETE');assert archived()['status']=='cancelled'
    assert app.SERVICES.api('tournaments/'+str(one['bracket']))['data']['id']==one['bracket']
    # Recover an old event already purged through the native UI before this fix.
    for person in archived()['participants']:
        app.SERVICES.api('tournaments/'+str(one['bracket'])+'/teams/'+str(person['team']),method='DELETE')
        app.SERVICES.api('tournaments/'+str(one['bracket'])+'/players/'+str(person['player']),method='DELETE')
    app.SERVICES.api('tournaments/'+str(one['bracket']),method='DELETE')
    a.req('/community-api/restore',{'id':cancelled})
    renewed=wait(lambda:(x if x['status']=='ready' and x['bracket']!=one['bracket'] and x['participants'][0]['team'] else None) if (x:=archived()) else None)
    assert renewed['participants'][0]['name']=='ValidationAdmin'
    a.req('/community-api/delete',{'id':cancelled})
    print('PASS zero/one-player deletion, restore, cancelled forum publication, no awards and blocked edits',flush=True)
    print('PASS real elimination match and score, mapped teams, shared forum identity, both trophy views, idempotent final publication and privilege/CSRF restrictions',flush=True)
    result={'passed':True,'environment':'private loopback validation databases; no production test accounts or events','voteChange':True,'tieAdminChoice':True,'automaticBracketCreation':True,'automaticTournamentThread':True,'personalNextMatchAndForumCounts':True,'personalIdentityAndAnonymousRejection':True,'realEliminationMatchScored':True,'accountSignupMapping':True,'confirmedPodiumTrophies':True,'duplicateFinalizationSafe':True,'sharedSmfIdentity':True,'playerRestrictions':True,'csrfRequired':True,'privateProfileDataExcluded':True,'zeroAndOnePlayerDeletion':True,'recoverableDeletion':True,'cancelledForumPublication':True,'cancelledNativeEditsBlocked':True,'nativeDeleteUsesCancellation':True,'missingNativeBracketRestored':True}
    pathlib.Path(os.environ['LISP_COMMUNITY_DIR']).joinpath('result.json').write_text(json.dumps(result,indent=2)+'\n')
finally:
    http_server.shutdown();local.shutdown()


