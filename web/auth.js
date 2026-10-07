window.LISP={user:null};
LISP.request=async(path,data)=>{
 if(data&&!['/auth-api/login','/auth-api/register'].includes(path))await LISP.ready;
 const r=await fetch(path,{cache:'no-store',...(data?{method:'POST',headers:{'Content-Type':'application/json','X-LAN-Request':'1','X-CSRF-Token':LISP.user?.csrf||''},body:JSON.stringify(data)}:{})});
 const x=(r.headers.get('content-type')||'').includes('application/json')?await r.json():{};
 if(!r.ok)throw Object.assign(Error(x.error||(r.status===401?'Log in on the home page.':r.status===403?'You do not have permission for this action.':'Request failed.')),{status:r.status});return x;
};
LISP.ready=LISP.request('/auth-api/session').then(user=>{LISP.user=user;return user}).catch(e=>{if(e.status!==401)console.warn('Account session unavailable');return null});
LISP.logout=async()=>{await LISP.request('/auth-api/logout',{});location.assign('/')};
