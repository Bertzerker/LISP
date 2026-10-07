(()=>{
 const el=id=>document.getElementById(id),say=(text,error=false)=>{el('account-message').textContent=text;el('account-message').className=error?'error':'success'};
 function view(user){el('guest-account').hidden=!!user;el('player-account').hidden=!user;el('member-links').hidden=!user||user.mustChange;el('change-account').hidden=!user;el('irc-section').hidden=!user||user.mustChange;
  if(user){el('account-self').textContent=`${user.name} · ${user.role} · ${user.ip} · ${user.mac}`;el('account-admin').hidden=user.role!=='admin';el('home-admin').hidden=user.role!=='admin';el('change-title').textContent=user.mustChange?'Set a new password to continue':'Change your password';el('change-details').open=user.mustChange}
 }
 for(const [form,path] of [['account-login','login'],['account-register','register']])el(form).onsubmit=async e=>{e.preventDefault();const f=e.currentTarget,b=f.querySelector('button');b.disabled=true;try{const user=await LISP.request('/auth-api/'+path,{name:f.elements.name.value,password:f.elements.password.value});f.reset();LISP.user=user;LISP.ready=Promise.resolve(user);location.reload()}catch(e){say(e.message,true)}finally{b.disabled=false}};
 el('account-change').onsubmit=async e=>{e.preventDefault();const f=e.currentTarget;if(f.elements.new.value!==f.elements.confirm.value){say('The new passwords do not match.',true);return}try{const user=await LISP.request('/auth-api/password',{current:f.elements.current.value,new:f.elements.new.value});f.reset();LISP.user=user;LISP.ready=Promise.resolve(user);location.reload()}catch(e){say(e.message,true)}};
 el('account-logout').onclick=()=>LISP.logout().catch(e=>say(e.message,true));
 el('irc-code').onclick=async()=>{try{const x=await LISP.request('/auth-api/irc-code',{});el('irc-instructions').textContent=`Server: ${location.hostname}:6667 · nickname: ${x.name} · server password: ${x.code}\nUse this code within two minutes, then /join #general, #shooter or #strategy. Never send your account password to IRC.`}catch(e){say(e.message,true)}};
 LISP.ready.then(view);
})();
