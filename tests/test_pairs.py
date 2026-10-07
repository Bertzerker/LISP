import sys,secrets,time,json
from pathlib import Path
from test_helpers import *
adapters=registry()
catalog={x['id']:x for x in api('/api/catalog')['games']}
for gameid in ['halflife','cstrike','crossproduct','l4d2','jabroni']:
 g=catalog[gameid];adapter=adapters[gameid];mode=g['modes'][0];level=g['maps'][0]
 for candidate in ['crossfire','Crossfire','de_dust2','c1m1_hotel']:
  if candidate in g['maps']:level=candidate;break
 ids=[];rows=[]
 try:
  for n in range(2):
   join='Join'+secrets.token_hex(8) if g['joinPasswordSupported'] else '';admin='Admin'+secrets.token_hex(10)
   x=api('/api/servers',dict(game=gameid,mode=mode['id'],map=level,players=mode['players'][0],password=join,adminPassword=admin));ids.append(x['id']);rows.append((x,join,admin))
  deadline=time.monotonic()+60
  while time.monotonic()<deadline:
   state=[x for x in api('/api/servers')['servers'] if x['id'] in ids]
   assert not any(x['status']=='failed' for x in state),gameid+' failed'
   if len(state)==2 and all(x['status']=='running' for x in state):break
   time.sleep(2)
  else:raise AssertionError(gameid+' readiness timeout')
  assert len({x['port'] for x in state})==2
  for x,join,admin in rows:
   rcon(adapter,x['port'],admin)
   cfg=Path('/srv/lan-party/servers/instances')/x['id']/'game'/adapter.mod/('cfg' if adapter.engine=='source' else '')/'lisp.cfg'
   data=cfg.read_text();assert f'sv_password "{join}"' in data and f'rcon_password "{admin}"' in data
   assert cfg.stat().st_mode&0o777==0o600
   public=json.dumps(api('/api/servers'));assert admin not in public and (not join or join not in public)
  api('/api/servers/'+ids[0]+'/stop',{});ids.pop(0)
  x,join,admin=rows[1];rcon(adapter,x['port'],admin)
  assert any(s['id']==ids[0] and s['status']=='running' for s in api('/api/servers')['servers'])
  print('PASS',gameid,'two instances, distinct ports/passwords, private config, live RCON and stop isolation',flush=True)
 finally:
  for ident in ids:
   api('/api/servers/'+ident+'/stop',{})
