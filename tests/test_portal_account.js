// Test form/session transitions with a fake transport; no real account is changed.
const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const root=process.argv[2]||path.resolve(__dirname,'..');
function load(name,context){vm.runInNewContext(fs.readFileSync(path.join(root,'web',name),'utf8'),context)}
function fixture(){
 const message={},button={disabled:false},logout={},form={elements:{current:{value:'old-test'},new:{value:'new-test-password'},confirm:{value:'new-test-password'}},querySelector:()=>button,reset(){this.resetCalled=true}};
 const nodes={'account-message':message,'account-change':form,'account-logout':logout};let calls=[],changed=0;
 const LISP={user:{csrf:'old'},request:async(p,d)=>{calls.push({p,d});return {csrf:'new',mustChange:false}},logout:async()=>{calls.push({p:'logout'})}};
 const context={LISP,document:{getElementById:id=>nodes[id]},location:{reload:()=>{changed++}}};load('account-controls.js',context);LISP.bindAccountControls();
 return {nodes,form,button,LISP,calls,changed:()=>changed};
}
(async()=>{
 let x=fixture();x.form.elements.confirm.value='different';await x.form.onsubmit({preventDefault(){}});assert.equal(x.calls.length,0);assert.match(x.nodes['account-message'].textContent,/do not match/);
 x=fixture();await x.form.onsubmit({preventDefault(){}});assert.equal(x.calls[0].p,'/auth-api/password');assert.equal(x.LISP.user.csrf,'new');assert.equal(x.changed(),1);assert.equal(x.form.resetCalled,true);assert.equal(x.button.disabled,false);
 x=fixture();x.LISP.request=async()=>{throw Error('Incorrect current password')};await x.form.onsubmit({preventDefault(){}});assert.equal(x.changed(),0);assert.equal(x.LISP.user.csrf,'old');assert.equal(x.nodes['account-message'].textContent,'Incorrect current password');assert.equal(x.button.disabled,false);
 await x.nodes['account-logout'].onclick();assert.equal(x.calls[0].p,'logout');
 for(const user of [null,{name:'Player',mustChange:true},{name:'Player',mustChange:false}]){
  let destination='';const nodes=Object.fromEntries(['account-message','guest-account','change-account','account-logout','change-details','account-login','account-register'].map(id=>[id,{}]));
  const LISP={ready:Promise.resolve(user),bindAccountControls:()=>{}};load('login.js',{LISP,document:{getElementById:id=>nodes[id],querySelector:()=>({focus(){}})},location:{replace:x=>{destination=x}}});await new Promise(resolve=>setImmediate(resolve));
  if(user&&!user.mustChange)assert.equal(destination,'/forum/');else{assert.equal(destination,'');assert.equal(nodes['guest-account'].hidden,!!user);assert.equal(nodes['change-account'].hidden,!user);if(user)assert.equal(nodes['change-details'].open,true)}
 }
 console.log('PASS password mismatch, success/session rotation, rejected change, logout and guest/temporary-password/normal-login routing');
})().catch(e=>{console.error(e);process.exitCode=1});
