/* Read-only, loopback CVP bridge for the local Mumble server. */
'use strict';
const fs=require('node:fs'),http=require('node:http');
const Ice=require('ice').Ice;
const M=require('./MumbleServer').MumbleServer;
const communicator=Ice.initialize();
const ctx=new Map([['secret',fs.readFileSync('/etc/lisp/mumble/view-secret','utf8').trim()]]);
let cached=null,expires=0,pending=null;
async function snapshot(){
 if(cached&&Date.now()<expires)return cached;
 if(pending)return pending;
 pending=(async()=>{
  const meta=await M.MetaPrx.checkedCast(communicator.stringToProxy('Meta:tcp -h 127.0.0.1 -p 6502 -t 3000'),null,ctx);
  if(!meta)throw Error('Invalid Mumble bridge');
  const server=await meta.getServer(1,ctx);
  const [channels,users]=await Promise.all([server.getChannels(ctx),server.getUsers(ctx)]);
  const nodes=new Map();
  for(const [id,c] of channels)nodes.set(id,{id,name:c.name,position:c.position||0,channels:[],users:[]});
  const root=nodes.get(0);if(!root)throw Error('Missing root channel');
  for(const [id,c] of channels)if(id!==0&&nodes.has(c.parent))nodes.get(c.parent).channels.push(nodes.get(id));
  for(const [,u] of users)if(nodes.has(u.channel))nodes.get(u.channel).users.push({name:u.name,mute:u.mute,deaf:u.deaf,selfMute:u.selfMute,selfDeaf:u.selfDeaf,prioritySpeaker:u.prioritySpeaker,recording:u.recording});
  for(const [,n] of nodes){n.channels.sort((a,b)=>a.position-b.position||a.name.localeCompare(b.name));n.users.sort((a,b)=>a.name.localeCompare(b.name));}
  cached={name:'LAN Zocken Voice',root,userCount:users.size,online:true,updated:Date.now()/1000};expires=Date.now()+10000;return cached;
 })();
 try{return await pending;}finally{pending=null;}
}
http.createServer(async(req,res)=>{
 res.setHeader('Content-Type','application/json');res.setHeader('Cache-Control','no-store');
 if(req.method!=='GET'||req.url!=='/mumble-api/cvp'){res.writeHead(404);res.end('{"error":"Not found"}');return;}
 try{res.end(JSON.stringify(await snapshot()));}
 catch(e){res.writeHead(503);res.end('{"online":false,"error":"Voice server is temporarily unavailable."}');}
}).listen(8810,'127.0.0.1');
process.on('SIGTERM',async()=>{await communicator.destroy();process.exit(0);});
