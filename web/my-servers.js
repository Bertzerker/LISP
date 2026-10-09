(()=>{
const $=id=>document.getElementById(id);let user,refreshing=false;const stopping=new Set();let timer;const portDrafts=new Map();
function message(text,error=false){$('message').textContent=text;$('message').className=error?'error':''}
async function manage(server,action,data={}){
 stopping.add(server.id);
 message(action==='port'?'Saving server port…':action==='delete'?'Deleting entry. Keeping saved world…':action==='restore'?'Restoring entry…':action==='restart'?'Restarting server…':server.persistentWorld?'Saving the world and stopping…':'Stopping server…');
 try{
  const result=await LISP.request('/api/servers/'+server.id+'/'+action,data);
  if(action==='port')portDrafts.delete(server.id);
  message(action==='port'?`Port saved: ${result.port}. Restart when ready.`:action==='delete'?'Entry deleted. Saved world kept. Restore is available below.':action==='restore'?'Entry restored. Restart when ready.':action==='restart'?'Server restarted. Wait for running status.':server.persistentWorld?'Server stopped. World saved.':'Server stopped. Your settings are kept.');
 }catch(error){message(error.message,true);throw error}
 finally{stopping.delete(server.id);await refresh(true)}
}
const stop=server=>manage(server,'stop'),restart=server=>manage(server,'restart'),remove=server=>manage(server,'delete'),restore=server=>manage(server,'restore');
function portEditor(server){
 const form=document.createElement('form');form.className='port-settings';
 const label=document.createElement('label');label.textContent='Server port';
 const select=document.createElement('select');select.setAttribute('aria-label','Server port for '+server.game+' · '+server.currentMap);
 const automatic=document.createElement('option');automatic.value='';automatic.textContent='Automatic — choose a free port';select.append(automatic);
 for(const choice of server.portOptions||[]){const option=document.createElement('option');option.value=String(choice.port);option.textContent=choice.port+(choice.available?'':' — in use');option.disabled=!choice.available;select.append(option)}
 const choices=server.portOptions||[];const previous=portDrafts.has(server.id)?portDrafts.get(server.id):String(server.port);
 select.value=previous===''||choices.some(choice=>String(choice.port)===previous)?previous:'';
 label.append(select);const button=document.createElement('button');button.className='change-port';button.type='submit';button.textContent='Save port';
 function state(){button.disabled=stopping.has(server.id)||!!select.selectedOptions[0]?.disabled||!choices.some(choice=>choice.available)}
 select.onchange=()=>{portDrafts.set(server.id,select.value);state()};state();
 form.onsubmit=async e=>{e.preventDefault();if(button.disabled||stopping.has(server.id))return;button.disabled=true;select.disabled=true;try{await manage(server,'port',{port:select.value===''?null:Number(select.value)})}catch{}};
 const help=document.createElement('p');help.className='muted';help.textContent='Changes apply while stopped. Saving a port keeps the world and settings; restart when ready.';
 form.append(label,button,help);return form;
}
function render(id,servers,empty){
 const box=$(id);box.replaceChildren();
 if(!servers.length){const p=document.createElement('p');p.className='muted';p.textContent=empty;box.append(p)}
 for(const server of LISPServerList.sorted(servers)){
  const card=LISPServerList.card(server,stop,restart,remove,restore,portEditor);for(const button of card.querySelectorAll('button.stop,button.restart,button.delete,button.restore,button.change-port'))if(stopping.has(server.id))button.disabled=true;box.append(card);
 }
}
async function refresh(force=false){
 if(refreshing||(!force&&document.activeElement?.closest?.('.port-settings')))return;refreshing=true;
 try{
  const data=await LISP.request('/api/servers');
  if(data.credits){const credit=data.credits;$('credit-summary').textContent=credit.creditExempt?'Admin account · servers are free':`${Number(credit.creditTokenBalance).toFixed(6)} Credit Tokens · negative limit ${credit.creditPolicy.negativeLimit} · ${credit.canStartPaidServer?'Servers can start':'Credit limit reached — ask an admin for tokens'}`}
  render('owned-servers',LISPServerList.owned(data.servers,user),'You have no servers. Start one from Game Servers.');
  const deleted=data.deletedServers||[];$('deleted-section').hidden=!deleted.length;render('deleted-servers',deleted,'No deleted entries.');
  $('other-servers-section').hidden=user.role!=='admin';
  if(user.role==='admin')render('other-servers',data.servers.filter(server=>server.ownerId!==user.id),'No other players have servers.');
 }catch(error){message('Unable to refresh your servers: '+error.message,true)}
 finally{refreshing=false}
}
LISP.ready.then(async account=>{
 user=account;if(!user||user.mustChange)return;await refresh();timer=setInterval(()=>{if(!document.hidden)refresh()},10000);
});
document.addEventListener('visibilitychange',()=>{if(!document.hidden&&user&&!user.mustChange)refresh()});window.addEventListener('pagehide',()=>clearInterval(timer));
})();
