from test_helpers import *
catalog=api('/api/catalog')['games'];adapters=registry()
only=set(sys.argv[1:]) or {g['id'] for g in catalog if g['id']!='quakelive'};failed=[]
for game in catalog:
    if only and game['id'] not in only:continue
    adapter=adapters[game['id']]
    mode=game['modes'][0];level=game['maps'][0]
    for want in ['campgrounds','crossfire','Crossfire','de_dust2','c1m1_hotel']:
        if want in game['maps']:level=want;break
    count=8 if 8 in mode['players'] else mode['players'][0]
    join=('Join'+secrets.token_hex(8)) if game.get('joinPasswordSupported',True) else '';admin='Admin'+secrets.token_hex(10)
    server=api('/api/servers',{'game':game['id'],'mode':mode['id'],'map':level,'players':count,'password':join,'adminPassword':admin})
    print('START',game['id'],server['id'],len(game['maps']),'maps',flush=True)
    try:
        deadline=time.monotonic()+55
        while time.monotonic()<deadline:
            state=next(s for s in api('/api/servers')['servers'] if s['id']==server['id'])
            assert (not join or join not in json.dumps(state)) and admin not in json.dumps(state)
            if state['status']=='failed':raise AssertionError('process exited '+str(state['exitCode']))
            if state['status']=='running':break
            time.sleep(3)
        else:raise AssertionError('did not become ready')
        if adapter.engine!='quake':
            info=adapter.query(server['port']);assert info is not None
            if 'passwordProtected' in info:assert info['passwordProtected']==bool(join),info
            rcon(adapter,server['port'],admin)
        assert state['passwordProtected']==bool(join) and state['adminEnabled']
        print('PASS',game['id'],'readiness, join-password flag, RCON, API secret exclusion',flush=True)
        api('/api/servers/'+server['id']+'/stop',{})
        assert not (Path('/srv/lan-party/servers/instances')/server['id']).exists()
    except Exception as e:
        print('FAIL',game['id'],server['id'],str(e).replace(join,'[hidden]').replace(admin,'[hidden]'),flush=True);failed.append(game['id'])
if failed:raise SystemExit('Failed: '+','.join(failed))
