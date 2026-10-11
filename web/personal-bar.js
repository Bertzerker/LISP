(()=>{
const bar=document.querySelector('.top-bar'),$=id=>document.getElementById(id);
if(!bar)return;
let timer,loading=false;
function label(id,text,active=false){const a=$(id);a.textContent=text;a.classList.toggle('has-update',active)}
async function refresh(){
 if(loading||document.hidden||!LISP.user||LISP.user.mustChange)return;loading=true;
 try{
  const user=LISP.user;
  await Promise.all([
   LISP.request('/api/servers').then(x=>{
    const own=x.servers.filter(s=>s.ownerId===user.id&&['starting','running'].includes(s.status));
    label('personal-servers',own.length?(own.length===1?own[0].game+' · '+own[0].status:own.length+' servers running'):'No servers running',!!own.length);
    $('personal-servers').title=own.map(s=>s.game+' · '+s.currentMap+' · '+s.status).join('\n');
   }).catch(()=>label('personal-servers','Servers unavailable')),
   LISP.request('/community-api/status').then(x=>{
    const image=$('personal-avatar'),fallback=$('personal-initial');
    if(x.avatar){if(image.getAttribute('src')!==x.avatar)image.src=x.avatar;image.hidden=false;fallback.hidden=true}else{image.hidden=true;fallback.hidden=false}
    label('personal-topics',x.forumAvailable?x.unreadTopics+' unread '+(x.unreadTopics===1?'topic':'topics'):'Forum unavailable',x.unreadTopics>0);
    label('personal-messages',x.forumAvailable?x.unreadMessages+' unread '+(x.unreadMessages===1?'message':'messages'):'Messages unavailable',x.unreadMessages>0);
    const next=x.nextMatch;
    label('personal-match',!x.tournamentAvailable?'Matches unavailable':next?'Next match: '+next.tournament+' · '+new Date(next.start*1000).toLocaleString([], {month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'}):'No upcoming match',!!next);
    $('personal-match').href=next?next.url:'/tournaments/';$('personal-match').title=next?'Against '+next.opponent:'';
   }).catch(()=>{label('personal-topics','Forum unavailable');label('personal-messages','Messages unavailable');label('personal-match','Matches unavailable')})
  ]);
 }finally{loading=false}
}
LISP.ready.then(user=>{
 if(!user)return;
 $('personal-bar').hidden=false;$('top-guest').hidden=true;$('personal-name').textContent=user.name;
 $('personal-network').textContent=`${user.role} · IP ${user.ip} · MAC ${user.mac||'unavailable'}`;
 document.querySelector('.personal-links').hidden=!!user.mustChange;
 $('personal-initial').textContent=user.name.slice(0,1).toUpperCase();
 $('personal-avatar').onerror=()=>{$('personal-avatar').hidden=true;$('personal-initial').hidden=false};
 refresh();timer=setInterval(refresh,30000);
});
document.addEventListener('visibilitychange',()=>{if(!document.hidden)refresh()});window.addEventListener('pagehide',()=>clearInterval(timer));
})();
