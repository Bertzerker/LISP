(()=>{
 const controls=document.createElement('section');controls.className='forum-account-controls';controls.setAttribute('aria-label','Your account');controls.hidden=true;
 controls.innerHTML='<p id="account-message" role="status"></p><div class="button-row"><button id="account-logout" class="quiet" type="button">Log out</button></div><details id="change-password"><summary>Change password</summary><form id="account-change" class="admin-form"><label>Current password<input name="current" type="password" autocomplete="current-password" maxlength="128" required></label><label>New password<input name="new" type="password" autocomplete="new-password" minlength="12" maxlength="128" required></label><label>Confirm new password<input name="confirm" type="password" autocomplete="new-password" minlength="12" maxlength="128" required></label><button>Save password</button></form></details>';
 document.querySelector('.page-content').prepend(controls);
 // SMF does not own the portal session; the account button above signs out of both.
 document.querySelectorAll('a[href*="action=logout"]').forEach(a=>a.closest('li')?.remove());
 function open(){document.getElementById('change-password').open=true;document.querySelector('#account-change input').focus()}
 window.addEventListener('hashchange',()=>{if(location.hash==='#change-password')open()});
 LISP.ready.then(user=>{if(!user||user.mustChange){location.replace('/login/');return}controls.hidden=false;LISP.bindAccountControls();if(location.hash==='#change-password')open();if(new URLSearchParams(location.search).get('account')==='logout')document.getElementById('account-logout').focus()});
})();
