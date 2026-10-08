'use strict';
const fs=require('node:fs'),Ice=require('ice').Ice,M=require('./MumbleServer').MumbleServer;
(async()=>{
 const c=Ice.initialize();
 try{
  const ctx=new Map([['secret',fs.readFileSync('/etc/lisp/mumble/write-secret','utf8').trim()]]);
  const meta=await M.MetaPrx.checkedCast(c.stringToProxy('Meta:tcp -h 127.0.0.1 -p 6502 -t 5000'),null,ctx);
  const server=await meta.getServer(1,ctx);
  const channels=await server.getChannels(ctx);
  for(const name of ['General','Shooter','Strategy'])if(![...channels.values()].some(x=>x.parent===0&&x.name===name))await server.addChannel(name,0,ctx);
  console.log('Mumble channels ready: General, Shooter, Strategy.');
 }finally{await c.destroy();}
})().catch(()=>{console.error('Mumble channel setup failed; inspect the local service.');process.exit(1);});
