/* LISP adaptation of alfg/mumble-widget v0.3.1.
 * Copyright (c) Alfred Gutierrez. MIT; see THIRD-PARTY.md.
 * Local CVP JSON and safe DOM rendering replace CDN dependencies and JSONP.
 */
(()=>{
 const box=document.getElementById('mumble-widget-container');if(!box)return;
 const text=document.createElement('p');text.className='muted';box.append(text);
 const tree=document.createElement('ul');tree.className='mumble-channels';box.append(tree);
 const join=document.getElementById('mumble-join');let loading=false,timer;
 function channel(node,depth=0){
  const item=document.createElement('li');if(depth>16)return item;
  const name=document.createElement('strong');name.textContent=node.name;item.append(name);
  if(node.users?.length){const people=document.createElement('ul');for(const user of node.users){const row=document.createElement('li');row.className='mumble-user';row.textContent=user.name+(user.deaf||user.selfDeaf?' · deafened':user.mute||user.selfMute?' · muted':'');people.append(row)}item.append(people)}
  if(node.channels?.length){const children=document.createElement('ul');for(const child of node.channels)children.append(channel(child,depth+1));item.append(children)}
  return item;
 }
 async function refresh(){
  if(loading||document.hidden||document.getElementById('sidebar-mumble')?.hidden||!LISP.user||LISP.user.mustChange)return;loading=true;
  try{const response=await fetch('/mumble-api/cvp',{cache:'no-store'});if(!response.ok)throw Error();const data=await response.json();if(!data.root)throw Error();tree.replaceChildren(channel(data.root));text.textContent=data.userCount+' online';join.hidden=false;join.href='mumble://'+encodeURIComponent(LISP.user.name)+'@'+(window.LISP_GAME_HOST||location.hostname)+':64738/?version=1.2.0';}
  catch{tree.replaceChildren();text.textContent='Voice server unavailable';join.hidden=true;}
  finally{loading=false;}
 }
 LISP.ready.then(user=>{if(user&&!user.mustChange){refresh();timer=setInterval(refresh,15000)}else{text.textContent='Log in to see voice channels.';join.hidden=true}});
 document.addEventListener('lisp-sidebar-view',refresh);document.addEventListener('visibilitychange',refresh);window.addEventListener('pagehide',()=>clearInterval(timer));
})();
