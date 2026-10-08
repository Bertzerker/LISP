const $=id=>document.getElementById(id);let catalog=[];let busy=false;
function message(text,error=false){$('message').textContent=text;$('message').className=error?'error':''}
async function api(path,data){await LISP.ready;const r=await fetch(path,{cache:'no-store',...(data?{method:'POST',headers:{'Content-Type':'application/json','X-LAN-Request':'1','X-CSRF-Token':LISP.user?.csrf||''},body:JSON.stringify(data)}:{})});const x=await r.json();if(!r.ok)throw Error(x.error||'Request failed');return x}
function option(select,value,label){const o=document.createElement('option');o.value=value;o.textContent=label;select.append(o)}
function game(){return catalog.find(x=>x.id===$('game').value)}
function modes(){const g=game();$('mode').disabled=false;$('map').disabled=false;worldOptions();for(const id of ['password','admin-password']){$(id).maxLength=g.passwordMaxLength||64;if($(id).value.length>$(id).maxLength)$(id).value=''}$('password').disabled=g.joinPasswordSupported===false;$('password-help').textContent=g.joinPasswordNote||'';if($('password').disabled)$('password').value='';$('mode').replaceChildren();$('map').replaceChildren();for(const m of g.modes)option($('mode'),m.id,m.name);updateMaps();$('mutator-field').hidden=!g.mutators?.length;$('mutators').replaceChildren();for(const m of g.mutators||[])option($('mutators'),m.id,m.name);for(const preferred of ['campgrounds','crossfire','de_dust2','c1m1_hotel','Crossfire','mp_shop','dm_lockdown','cp_dustbowl'])if(g.maps.includes(preferred)){$('map').value=preferred;break}$('start').disabled=!$('map').options.length;$('ql-admin').hidden=g.adminKind!=='steamid-zmq';$('admin-help').textContent=g.adminInstructions?g.adminInstructions+' '+(g.clientNote||''):g.adminKind==='cod'?g.adminInstructions+' '+g.clientNote:g.adminKind==='zomboid'?'Sign in as admin with the admin password to manage the world in game. '+g.clientNote:g.adminKind==='swbf2'?'In global chat (Ctrl+T): /admin /login YOUR_ADMIN_PASSWORD, then /admin /players or /admin /nextmap. '+g.clientNote:g.adminKind==='unreal'?'In the game console: adminlogin YOUR_ADMIN_PASSWORD. '+g.clientNote:g.id==='etlegacy'?'In the game console: rconpassword YOUR_ADMIN_PASSWORD, then rcon COMMAND. For in-game referee controls: ref YOUR_ADMIN_PASSWORD. '+g.clientNote:g.id==='sof2'?'In the game console: rconpassword YOUR_ADMIN_PASSWORD, then rcon COMMAND. '+g.clientNote:g.adminKind==='steamid-zmq'?'Quake Live: in-game admin uses your SteamID64 below. This password is for an external ZeroMQ RCON client.':'In the game console: rcon_password YOUR_ADMIN_PASSWORD, then rcon COMMAND.';playerLimit();worldSelection()}
function playerLimit(){const m=game().modes.find(x=>x.id===$('mode').value);const old=$('players').value;$('players').replaceChildren();for(const p of m.players)option($('players'),p,p);$('players').value=m.players.includes(Number(old))?old:String(m.players.includes(8)?8:m.players[0]);$('players').disabled=m.players.length===1}
async function refresh(){
 try{
  const x=await api('/api/servers');$('servers').replaceChildren();
  if(!x.servers.length)$('servers').textContent='No servers running. Start a match above.';
  for(const server of LISPServerList.sorted(x.servers))$('servers').append(LISPServerList.card(server));
 }catch(e){message('Unable to refresh servers: '+e.message,true)}
}
$('game').onchange=modes;$('mode').onchange=()=>{playerLimit();updateMaps()};$('launch').onsubmit=async e=>{e.preventDefault();if(busy)return;busy=true;$('start').disabled=true;message('Preparing and starting server…');try{const x=await api('/api/servers',{game:$('game').value,world:game().id==='zomboid'?$('world').value:'new',worldName:game().id==='zomboid'?$('world-name').value:'',players:Number($('players').value),mode:$('mode').value,map:$('map').value,port:$('port').value?Number($('port').value):null,password:$('password').value,adminPassword:$('admin-password').value,mutators:[...$('mutators').selectedOptions].map(x=>x.value),adminSteamIds:game().adminKind==='steamid-zmq'?$('admin-ids').value:''});$('password').value='';$('admin-password').value='';message(`Server requested on port ${x.port}. Wait for running status.`);await reloadWorlds();await refresh()}catch(e){message(e.message,true)}finally{busy=false;$('start').disabled=false}};
(async()=>{await LISP.ready;try{const x=await api('/api/catalog');catalog=x.games.sort((a,b)=>a.name.localeCompare(b.name));for(const port of x.ports)option($('port'),port,port);for(const g of catalog)option($('game'),g.id,g.name);const selected=new URLSearchParams(location.search).get('game');if(catalog.some(g=>g.id===selected))$('game').value=selected;modes();await refresh();setInterval(()=>{if(!document.hidden&&!busy)refresh()},10000)}catch(e){message(e.message,true)}})();

function updateMaps(){
 const g=game();const old=$('map').value,mode=g.modes.find(x=>x.id===$('mode').value),prefix=mode?.mapPrefix,suffix=mode?.mapSuffix;
 $('map').replaceChildren();for(const m of g.maps)if((!prefix||m.startsWith(prefix))&&(!suffix||m.endsWith(suffix)))option($('map'),m,g.mapLabels?.[m]||m);
 if([...$('map').options].some(x=>x.value===old))$('map').value=old;
 $('start').disabled=!$('map').options.length;
}

function worldOptions(){
 const g=game(),previous=$('world').value;
 $('world-field').hidden=!g.persistentWorlds;$('world-name-field').hidden=!g.persistentWorlds;
 $('world').replaceChildren();option($('world'),'new','Create a new world');
 for(const w of g.worlds||[])option($('world'),w.id,w.name);
 if((g.worlds||[]).some(w=>w.id===previous))$('world').value=previous;
}
function worldSelection(){
 const g=game();if(!g.persistentWorlds)return;
 const w=(g.worlds||[]).find(w=>w.id===$('world').value);
 $('world-name-field').hidden=!!w;$('mode').disabled=!!w;$('map').disabled=!!w;
 if(w){$('mode').value=w.mode;updateMaps();$('map').value=w.map;playerLimit()}
}
async function reloadWorlds(){
 if(game()?.id!=='zomboid')return;
 const x=await api('/api/catalog');catalog=x.games.sort((a,b)=>a.name.localeCompare(b.name));worldOptions();worldSelection();
}
$('world').onchange=worldSelection;
