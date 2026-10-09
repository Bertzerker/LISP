/* Isolated ownership, Join/Stop placement and failed-server dismissal fixtures. */
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const root=path.resolve(__dirname,'..');
class Element{
 constructor(tag){this.tagName=tag;this.children=[];this.textContent='';this.hidden=false;this.className=''}
 append(...nodes){this.children.push(...nodes)}
 replaceChildren(...nodes){this.children=[...nodes];this.textContent=''}
 querySelectorAll(selector){return this.walk().filter(el=>el.tagName==='button'&&selector.split(',').includes('button.'+el.className))}
 querySelector(selector){return this.querySelectorAll(selector)[0]||null}
 walk(){return this.children.flatMap(el=>[el,...el.walk()])}
}
function context(user,servers){
 const elements={};for(const id of ['message','owned-servers','other-servers','other-servers-section','deleted-section','deleted-servers'])elements[id]=new Element('div');
 const calls=[];let deleted=[];const ctx={window:{},location:{hostname:'192.168.8.138'},document:{hidden:false,createElement:tag=>new Element(tag),getElementById:id=>elements[id],addEventListener:()=>{}},LISP:{ready:Promise.resolve(user),request:async(url,data)=>{calls.push({url,data});if(data){const id=url.split('/')[3];const action=url.split('/')[4];if(action==='delete'){deleted.push({...servers.find(s=>s.id===id),status:'deleted',canStop:false,canRestart:false,canDelete:false,canRestore:true});servers=servers.filter(s=>s.id!==id)}else if(action==='restore'){servers.push({...deleted.find(s=>s.id===id),status:'stopped',canRestart:true,canDelete:true,canRestore:false});deleted=deleted.filter(s=>s.id!==id)}else servers=servers.map(s=>s.id===id?{...s,status:action==='stop'?'stopped':'running',canStop:action!=='stop',canRestart:true,canDelete:action==='stop'}:s);return {stopped:action==='stop'}}return {servers,deletedServers:deleted}}},setInterval:()=>1,clearInterval:()=>{}};
 ctx.window.addEventListener=()=>{};vm.createContext(ctx);vm.runInContext(fs.readFileSync(path.join(root,'web/server-list.js'),'utf8'),ctx);ctx.LISPServerList=ctx.window.LISPServerList;
 return {ctx,elements,calls};
}
function server(id,owner,status='running',canStop=true){return {id,ownerId:owner,ownerName:'Player '+owner,game:'Quake Live',gameId:'quakelive',adminKind:'steamid-zmq',modeName:'Free for all',currentMap:'campgrounds',status,players:8,port:27015,canStop,canRestart:canStop}}
async function flush(){for(let n=0;n<8;n++)await Promise.resolve()}
async function main(){
 const items=[server('owned',2),server('other',3),server('failed',2,'failed'),server('denied',4,'running',false)];
 const a=context({id:2,role:'player'},items);
 for(const item of items){const card=a.ctx.LISPServerList.card(item);assert.equal(card.querySelector('button.stop'),null,'Public Game Servers must not have any stop/dismiss controls');if(item.status==='running')assert(card.walk().some(el=>el.textContent==='Join'),'Join preserved')}
 assert.equal(a.ctx.LISPServerList.card(items[3],()=>{}).querySelector('button.stop'),null,'Server authorization cannot be bypassed');
 assert.deepEqual(Array.from(a.ctx.LISPServerList.owned(items,{id:2}),s=>s.id),['owned','failed'],'Same-game instances are filtered by account ID');
 vm.runInContext(fs.readFileSync(path.join(root,'web/my-servers.js'),'utf8'),a.ctx);await flush();
 assert.equal(a.elements['owned-servers'].children.length,2);assert.equal(a.elements['other-servers-section'].hidden,true);
 const dismiss=a.elements['owned-servers'].children[1].querySelector('button.stop');assert.equal(dismiss.textContent,'Stop server');await dismiss.onclick();await flush();
 assert.equal(a.calls.filter(call=>call.data).length,1);assert.equal(a.calls.find(call=>call.data).url,'/api/servers/failed/stop');assert.equal(a.elements['owned-servers'].children.length,2,'Stop retains the owned entry and does not touch another owner');assert.equal(a.elements['owned-servers'].children[1].querySelector('button.stop'),null);await a.elements['owned-servers'].children[1].querySelector('button.restart').onclick();await flush();assert.equal(a.calls.filter(call=>call.data)[1].url,'/api/servers/failed/restart');assert(a.elements['owned-servers'].children[1].querySelector('button.stop'),'Restart re-enables Stop');
 await a.elements['owned-servers'].children[1].querySelector('button.stop').onclick();await flush();
 await a.elements['owned-servers'].children[1].querySelector('button.delete').onclick();await flush();
 assert.equal(a.elements['owned-servers'].children.length,1);assert.equal(a.elements['deleted-section'].hidden,false);assert(a.elements['deleted-servers'].children[0].querySelector('button.restore'));
 assert.equal(a.ctx.LISPServerList.card({id:'deleted',status:'stopped',canDelete:true,game:'Fixture',port:27015}).querySelector('button.delete'),null,'No public Delete control');
 await a.elements['deleted-servers'].children[0].querySelector('button.restore').onclick();await flush();assert.equal(a.elements['owned-servers'].children.length,2);assert.equal(a.elements['deleted-section'].hidden,true);
 const b=context({id:2,role:'admin'},items);vm.runInContext(fs.readFileSync(path.join(root,'web/my-servers.js'),'utf8'),b.ctx);await flush();
 assert.equal(b.elements['owned-servers'].children.length,2);assert.equal(b.elements['other-servers-section'].hidden,false);assert.equal(b.elements['other-servers'].children.length,2);
 assert(b.elements['other-servers'].children[0].querySelector('button.stop'),'Administrator keeps permitted controls for other owners');
 const empty=context({id:99,role:'player'},items);vm.runInContext(fs.readFileSync(path.join(root,'web/my-servers.js'),'utf8'),empty.ctx);await flush();assert.match(empty.elements['owned-servers'].children[0].textContent,/You have no servers/);
 console.log('PASS My Servers: own/other accounts, admin controls, no public stop/dismiss, Join preserved, retained stopped entries, restart, Delete/Restore and empty state');
}
main().catch(error=>{console.error(error);process.exitCode=1});
