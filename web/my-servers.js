(()=>{
const $=id=>document.getElementById(id);let user,refreshing=false;const stopping=new Set();let timer;
function message(text,error=false){$('message').textContent=text;$('message').className=error?'error':''}
async function stop(server){
 stopping.add(server.id);
 message(server.gameId==='zomboid'?'Saving the world and stopping…':server.status==='failed'?'Dismissing failed server…':'Stopping server…');
 try{
  await LISP.request('/api/servers/'+server.id+'/stop',{});
  message(server.status==='failed'?'Failed server dismissed.':server.gameId==='zomboid'?'Server stopped. World saved.':'Server stopped.');
 }catch(error){message(error.message,true);throw error}
 finally{stopping.delete(server.id);await refresh()}
}
function render(id,servers,empty){
 const box=$(id);box.replaceChildren();
 if(!servers.length){const p=document.createElement('p');p.className='muted';p.textContent=empty;box.append(p)}
 for(const server of LISPServerList.sorted(servers)){
  const card=LISPServerList.card(server,stop);const button=card.querySelector('button.stop');if(button)button.disabled=stopping.has(server.id);box.append(card);
 }
}
async function refresh(){
 if(refreshing)return;refreshing=true;
 try{
  const data=await LISP.request('/api/servers');
  render('owned-servers',LISPServerList.owned(data.servers,user),'You have no servers. Start one from Game Servers.');
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
