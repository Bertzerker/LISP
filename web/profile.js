LISP.ready.then(user=>{if(user&&!user.mustChange)location.replace('/trophies/?user='+encodeURIComponent(new URLSearchParams(location.search).get('user')||user.id));});
