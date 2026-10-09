// Shared by forum account settings and the mandatory first-login password screen.
LISP.bindAccountControls=function(onChanged=()=>location.reload()){
 const message=document.getElementById('account-message');
 const say=(text,error=false)=>{message.textContent=text;message.className=error?'error':'success'};
 const form=document.getElementById('account-change');
 if(form)form.onsubmit=async e=>{
  e.preventDefault();if(form.elements.new.value!==form.elements.confirm.value){say('The new passwords do not match.',true);return}
  const button=form.querySelector('button');button.disabled=true;
  try{const user=await LISP.request('/auth-api/password',{current:form.elements.current.value,new:form.elements.new.value});form.reset();LISP.user=user;LISP.ready=Promise.resolve(user);onChanged()}
  catch(e){say(e.message,true)}finally{button.disabled=false}
 };
 const logout=document.getElementById('account-logout');
 if(logout)logout.onclick=()=>LISP.logout().catch(e=>say(e.message,true));
};
