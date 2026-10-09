async function copyConnectCommand(command){
 if(window.isSecureContext&&navigator.clipboard){await navigator.clipboard.writeText(command);return}
 const previous=document.activeElement,field=document.createElement('textarea');field.value=command;field.setAttribute('readonly','');field.style.position='fixed';field.style.opacity='0';document.body.append(field);field.select();
 try{if(!document.execCommand('copy'))throw Error('Select the connect command manually')}finally{field.remove();if(previous&&previous.focus)previous.focus()}
}
function joinControls(server,command){
 const box=document.createElement('div');box.className='join-controls';
 const row=document.createElement('div');row.className='button-row';
 const appIds={quakelive:282440,tf2:440,hl2dm:320,halflife:70,cstrike:10,l4d2:550,jabroni:869480,contagion:238430,brink:22350};
 const app=appIds[server.gameId];
 const unreal=server.gameId==='ut99'||server.gameId==='ut2004';
 const hint=document.createElement('p');hint.className='muted';hint.hidden=true;
 const copy=document.createElement('button');copy.type='button';copy.className='quiet';copy.textContent=(app||unreal)?'Copy connect command':'Join';
 copy.onclick=async()=>{hint.hidden=false;hint.textContent=server.joinInstructions|| (server.adminKind==='cod'?(server.gameId==='iw4x'?'Open IW4x, open its console (~), and paste the connect command above.':'Open this game through Plutonium in LAN mode, open its console (~), and paste the connect command above.'):server.gameId==='zomboid'?'Open Project Zomboid → Join → Favorites → Add server. Use the address above, create your own player username/password, and enter the optional server password.':server.gameId==='swbf2'?'Open the original 2005 game → Multiplayer → LAN. Select LISP Battlefront II - '+server.port+'. Wait up to 30 seconds for the LAN list to appear.':unreal?'Open the game console and paste the open command above.':server.gameId==='etlegacy'?'Open ET: Legacy, open the console (~), and paste the connect command above.':server.gameId==='sof2'?'Open SoF2 Gold v1.03 multiplayer, open the console (~), and paste the connect command above.':'Open the game console and paste the connect command above.');try{await copyConnectCommand(command);hint.textContent+=['swbf2','zomboid','avp2ph','sevendays'].includes(server.gameId)?' Address copied.':' Command copied.'}catch(e){hint.textContent+=' Select and copy the command above.'}};
 if(app||unreal){const join=document.createElement('a');join.className='join-button';join.textContent='Join';join.href=unreal?(server.gameId==='ut2004'?'ut2004://':'unreal://')+(window.LISP_GAME_HOST||location.hostname)+':'+server.port:'steam://run/'+app+'//'+encodeURIComponent('+connect '+(window.LISP_GAME_HOST||location.hostname)+':'+server.port)+'/';join.onclick=()=>{hint.hidden=false;hint.textContent=unreal?'Allow your browser to open Unreal Tournament. If no handler is installed, use the console command above.':'Allow your browser to open Steam. If the game is already open, use Copy connect command.'+(server.passwordProtected?' Enter the join password in the game console first.':'')};row.append(join)}
 row.append(copy);box.append(row,hint);return box;
}
function loadControls(s){
 const box=document.createElement('section');box.className='server-load';box.setAttribute('aria-label','Server load');const load=s.load;
 const heading=document.createElement('h4');heading.textContent=s.status==='stopped'?'Last session load':'Server load';box.append(heading);
 if(load){const bytes=n=>{if(n<1024)return Math.round(n)+' B/s';if(n>=1048576)return (n/1048576).toFixed(2)+' MiB/s';return (n/1024).toFixed(1)+' KiB/s'};const cpu=document.createElement('p');cpu.textContent=`CPU ${load.cpuPercent.toFixed(1)}% · average ${load.cpuAveragePercent.toFixed(1)}%`;const net=document.createElement('p');net.textContent=`Network ↓ ${bytes(load.rxBytesPerSecond)} · ↑ ${bytes(load.txBytesPerSecond)}`;const average=document.createElement('p');average.className='muted';average.textContent=`Network average ${bytes(load.networkAverageBytesPerSecond??(load.rxBytesPerSecond+load.txBytesPerSecond))} · over ${Math.round(load.averageWindowSeconds)}s · 100% CPU = one core · LAN traffic only`;box.append(cpu,net,average)}
 else{const pending=document.createElement('p');pending.className='muted';pending.textContent=s.status==='stopped'?'No measured session yet.':'Measuring server usage…';box.append(pending)}
 if(s.loadError){const error=document.createElement('p');error.className='error';error.textContent=s.loadError;box.append(error)}
 if(s.billing){const cost=document.createElement('p');cost.className='credit-cost';cost.textContent=s.billing.creditExempt?'Admin server · no token charge':`${Number(s.billing.chargedTokens||0).toFixed(6)} tokens this session · ${Number(s.billing.tokensPerHour||0).toFixed(4)} tokens/hour at average load`;box.append(cost)}
 if(s.stopReason){const reason=document.createElement('p');reason.className='error';reason.textContent=s.stopReason;box.append(reason)}
 return box;
}
function serverCard(s,stopServer,restartServer,deleteServer,restoreServer,portEditor){
const a=document.createElement('article');a.dataset.serverId=s.id;const h=document.createElement('h3');h.textContent=`${s.game} · ${s.modeName} · ${s.currentMap}`;a.append(h);const owner=document.createElement('p');owner.className='muted';owner.textContent='Started by '+(s.ownerName||'administrator');a.append(owner);if(s.worldName){const world=document.createElement('p');world.textContent='World: '+s.worldName+' · Progress is saved when stopped.';a.append(world)}const p=document.createElement('p');p.className='status';p.textContent=`${s.status} · ${s.connected==null?s.players+' player slots':s.connected+'/'+s.players+' players'} · port ${s.port}${s.passwordProtected?' · Password protected':''}`;a.append(p);const c=document.createElement('p');const code=document.createElement('code');code.textContent=(s.joinCommandKind==='address'||['swbf2','zomboid'].includes(s.gameId))?`${window.LISP_GAME_HOST||location.hostname}:${s.port}`:`${s.adminKind==='unreal'?'open':s.gameId==='quakelive'?'/connect':'connect'} ${window.LISP_GAME_HOST||location.hostname}:${s.port}`;c.append(code);a.append(c);if(s.passwordProtected){const help=document.createElement('p');help.textContent=s.joinPasswordInstructions||(s.gameId==='zomboid'?'Enter the server password in the Join form; your player-account password is separate.':s.gameId==='swbf2'?'Enter the join password when the game prompts for it.':s.adminKind==='unreal'?'Join with open IP:PORT?password=YOUR_JOIN_PASSWORD in the game console.':'Set password YOUR_JOIN_PASSWORD in your game console before connecting.');a.append(help)}if(s.adminEnabled){const help=document.createElement('p');help.textContent=s.adminInstructions|| (s.adminKind==='cod'?(s.adminInstructions||'Admin: use the matching game console RCON commands.'):s.gameId==='zomboid'?'Admin: join as username admin using the configured admin password.':s.gameId==='swbf2'?'Admin: global chat (Ctrl+T), /admin /login YOUR_ADMIN_PASSWORD; then /admin /players or /admin /nextmap.':s.adminKind==='steamid-zmq'?[s.inGameAdminEnabled?'In-game admin: configured SteamID64.':'',s.adminPort?`External RCON port: ${s.adminPort}.`:''].filter(Boolean).join(' '):s.adminKind==='unreal'?'Admin: adminlogin YOUR_ADMIN_PASSWORD in the game console.':s.gameId==='etlegacy'?'Admin: set rconpassword, then rcon commands; referee: ref YOUR_ADMIN_PASSWORD.':s.gameId==='sof2'?'Admin: set rconpassword in your game console, then use rcon commands.':'Admin: set rcon_password in your game console, then use rcon commands.');a.append(help)}if(s.status==='failed'){const e=document.createElement('p');e.textContent='This server exited. Its private server log contains startup details. Restart it from My Servers.';a.append(e)}if(s.status==='running')a.append(joinControls(s,code.textContent));if(s.mutators?.length){const m=document.createElement('p');m.textContent='Mutators: '+s.mutators.join(', ');a.append(m)}
 if(s.status!=='deleted')a.append(loadControls(s));
 if(stopServer&&s.canStop){
  const button=document.createElement('button');button.type='button';button.className='stop';button.textContent=s.persistentWorld?'Save & stop':'Stop server';
  button.onclick=async()=>{button.disabled=true;try{await stopServer(s)}catch(error){button.disabled=false}};a.append(button);
 }
 if(portEditor&&s.canChangePort&&s.status==='stopped')a.append(portEditor(s));
 if(restartServer&&s.canRestart){
  const button=document.createElement('button');button.type='button';button.className='restart';button.textContent='Restart server';button.disabled=s.status==='stopped'&&!!s.portBusy;
  button.onclick=async()=>{button.disabled=true;try{await restartServer(s)}catch(error){button.disabled=false}};a.append(button);
 }
 if(deleteServer&&s.canDelete&&s.status==='stopped'){
  const button=document.createElement('button');button.type='button';button.className='delete';button.textContent='Delete entry';
  button.onclick=async()=>{button.disabled=true;try{await deleteServer(s)}catch(error){button.disabled=false}};a.append(button);
 }
 if(restoreServer&&s.canRestore){
  const button=document.createElement('button');button.type='button';button.className='restore';button.textContent='Restore entry';
  button.onclick=async()=>{button.disabled=true;try{await restoreServer(s)}catch(error){button.disabled=false}};a.append(button);
 }
 if(s.status==='deleted'){const notice=document.createElement('p');notice.className='muted';notice.textContent='Entry deleted. Saved world kept. Restore returns this entry without starting it.';a.append(notice)}
 if(s.status==='stopped'){const notice=document.createElement('p');notice.className='muted';notice.textContent=s.portBusy?'This port is in use. Save a free port before restarting.':s.persistentWorld?'World saved. Restart this server to continue.':'Server stopped. Restart to use these settings again.';a.append(notice)}
 return a;
}
window.LISPServerList={
 card:serverCard,
 sorted:servers=>[...servers].sort((a,b)=>a.game.localeCompare(b.game)||a.port-b.port),
 owned:(servers,user)=>servers.filter(server=>server.ownerId===user.id)
};
