(()=>{
 const $=id=>document.getElementById(id),say=text=>{$('account-message').textContent=text;$('account-message').className='error'};
 function view(user){
  if(user&&!user.mustChange){location.replace('/downloads/');return}
  $('guest-account').hidden=!!user;$('change-account').hidden=!user;$('account-logout').hidden=!user;
  if(user){$('change-details').open=true;document.querySelector('#account-change input').focus()}
 }
 for(const [id,path] of [['account-login','login'],['account-register','register']])$(id).onsubmit=async e=>{
  e.preventDefault();const form=e.currentTarget,button=form.querySelector('button');button.disabled=true;
  try{const user=await LISP.request('/auth-api/'+path,{name:form.elements.name.value,password:form.elements.password.value});form.reset();LISP.user=user;LISP.ready=Promise.resolve(user);location.reload()}
  catch(e){say(e.message)}finally{button.disabled=false}
 };
 LISP.bindAccountControls(()=>location.replace('/downloads/'));LISP.ready.then(view);
})();
