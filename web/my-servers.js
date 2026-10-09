(()=>{
const $=id=>document.getElementById(id);let user,refreshing=false;const stopping=new Set();let timer;
function message(text,error=false){$('message').textContent=text;$('message').className=error?'error':''}
async function manage(server,action){
 stopping.add(server.id);
 message(action==='delete'?'Deleting entry. Keeping saved world…':action==='restore'?'Restoring entry…':action==='restart'?'Restarting server…':server.persistentWorld?'Saving the world and stopping…':'Stopping server…');
 try{
  await LISP.request('/api/servers/'+server.id+'/'+action,{});
  message(action==='delete'?'Entry deleted. Saved world kept. Restore is available below.':action==='restore'?'Entry restored. Restart when ready.':action==='restart'?'Server restarted. Wait for running status.':server.persistentWorld?'Server stopped. World saved.':'Server stopped. Your settings are kept.');
 }catch(error){message(error.message,true);throw error}
 finally{stopping.delete(server.id);await refresh()}
}
const stop=server=>manage(server,'stop'),restart=server=>manage(server,'restart'),remove=server=>manage(server,'delete'),restore=server=>manage(server,'restore');
function render(id,servers,empty){
 const box=$(id);box.replaceChildren();
 if(!servers.length){const p=document.createElement('p');p.className='muted';p.textContent=empty;box.append(p)}
 for(const server of LISPServerList.sorted(servers)){
  const card=LISPServerList.card(server,stop,restart,remove,restore);for(const button of card.querySelectorAll('button.stop,button.restart,button.delete,button.restore'))button.disabled=stopping.has(server.id);box.append(card);
 }
}
async function refresh(){
 if(refreshing)return;refreshing=true;
 try{
  const data=await LISP.request('/api/servers');
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
