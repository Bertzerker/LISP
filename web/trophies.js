(()=>{
const $=id=>document.getElementById(id),ranks=['','Gold','Silver','Bronze'];
function avatar(person){
 const box=document.createElement('span');box.className='trophy-avatar';
 const initial=document.createElement('span');initial.className='trophy-initial';initial.textContent=person.name.slice(0,1).toUpperCase();initial.setAttribute('aria-hidden','true');box.append(initial);
 if(person.avatar?.startsWith('/forum/')){const image=document.createElement('img');image.width=image.height=64;image.alt=person.name+' avatar';image.loading='lazy';image.onload=()=>initial.hidden=true;image.onerror=()=>{image.remove();initial.hidden=false};image.src=person.avatar;box.append(image)}
 return box;
}
function medals(person){
 const row=document.createElement('div');row.className='medal-totals';
 for(const [index,name] of ['gold','silver','bronze'].entries()){const badge=document.createElement('span');badge.className='medal-total rank-'+(index+1);const number=document.createElement('strong');number.textContent=String(person[name]);const label=document.createElement('span');label.textContent=name;badge.append(number,label);row.append(badge)}
 return row;
}
async function load(){
 const user=await LISP.ready;if(!user||user.mustChange)return;
 try{
  const data=await LISP.request('/community-api/trophies');
  if(!data.avatarsAvailable)$('trophy-message').textContent='Forum avatars are temporarily unavailable. Trophy totals are still shown.';
  const raw=new URLSearchParams(location.search).get('user');
  if(raw!==null){
   if(!/^[1-9][0-9]*$/.test(raw))throw Error('Player not found.');
   const person=data.users.find(p=>p.id===Number(raw));if(!person)throw Error('Player not found.');
   const profile=await LISP.request('/community-api/profile?user='+person.id);
   $('trophy-directory').hidden=true;$('trophy-player').hidden=false;$('trophy-player-name').textContent=person.name;$('trophy-player-heading').prepend(avatar(person));$('trophy-player-medals').append(medals(person));$('trophy-forum-profile').href='/forum/index.php?action=profile;u='+person.id;document.title=person.name+' · Trophy Room';
   if(!profile.trophies.length){const empty=document.createElement('p');empty.className='muted';empty.textContent='No trophies yet. Trophies appear when tournament results are confirmed.';$('trophy-awards').append(empty)}
   for(const award of profile.trophies){
    const card=document.createElement('article');card.className='trophy rank-'+award.rank;
    const rank=document.createElement('strong');rank.textContent=ranks[award.rank]+' / '+['','1st','2nd','3rd'][award.rank];
    const game=document.createElement('h3');game.textContent=award.gameName||award.game||'Unknown game';
    const tournament=document.createElement('a');tournament.textContent=award.name;tournament.href='/tournaments/?id='+award.poll;
    const date=document.createElement('time');date.dateTime=new Date(award.created*1000).toISOString();date.textContent=new Date(award.created*1000).toLocaleDateString();
    card.append(rank,game,tournament,date);$('trophy-awards').append(card);
   }
  }else{
   if(!data.users.length)$('trophy-players').textContent='No players yet.';
   for(const person of data.users){const card=document.createElement('a');card.className='trophy-player-card';card.href='/trophies/?user='+person.id;const name=document.createElement('h2');name.textContent=person.name;card.append(avatar(person),name,medals(person));$('trophy-players').append(card)}
  }
 }catch(error){$('trophy-message').textContent=error.message;$('trophy-message').className='error';const back=document.createElement('a');back.href='/trophies/';back.textContent='All players';$('trophy-message').append(document.createTextNode(' '),back)}
}
load();
})();
