#!/usr/bin/python3
"""Preconvert owned Steam x64 fastfiles using IW4x's official Unlinker.

This follows the probe and converter command in IW4x ZoneConvert.cpp. It
only writes IW4x's derived x86 cache in the private template, never originals.
No game socket, installed marker, account or Steam library is changed.
"""
import json,os,pathlib,struct,subprocess,zlib
ROOT=pathlib.Path('/srv/lan-party/servers')

def architecture(path):
 try:
  with path.open('rb') as f:
   h=f.read(21)
   if len(h)!=21 or struct.unpack_from('<I',h,8)[0]!=276:return None
   if h[:8]==b'IWffu100':offset=21
   elif h[:8] in (b'IWff0100',b'ABff0100'):offset=21+2*0x2000
   else:return None
   f.seek(offset);head=zlib.decompressobj().decompress(f.read(0x10000),72)
  if len(head)<72:return None
  def pointer(at):
   count=struct.unpack_from('<I',head,at)[0];value=struct.unpack_from('<Q',head,at+8)[0]
   return value==0 if count==0 else value in (2**64-1,2**64-2)
  return 'x64' if head[44:48]==b'\0'*4 and head[60:64]==b'\0'*4 and pointer(40) and pointer(56) else 'x86'
 except (OSError,zlib.error,struct.error):return None

def main():
 if os.geteuid()==0:raise SystemExit('Run as lanserver')
 game=ROOT/'templates/iw4x';converter=game/'Unlinker.exe'
 if not converter.is_file():raise FileNotFoundError('Official IW4x Unlinker.exe is missing')
 home=ROOT/'install-media/iw4x-conversion';home.mkdir(mode=0o700,exist_ok=True)
 prefix=home/'wine'
 if not prefix.exists():subprocess.run(['cp','-a','--reflink=auto',str(ROOT/'templates/iw4x-wine-prefix'),str(prefix)],check=True)
 env=os.environ.copy();env.update(HOME=str(home),WINEPREFIX=str(prefix),WINEDEBUG='-all',WINEDLLOVERRIDES='mscoree,mshtml=d')
 results=[]
 try:
  for group in sorted((game/'zone').iterdir()):
   if not group.is_dir() or group.name.casefold()=='iw4x' or group.name=='old' or group.name.endswith('_old'):continue
   for source in sorted(group.glob('*.ff')):
    if source.is_symlink() or architecture(source)!='x64':continue
    target=game/'zone/iw4x/x86'/group.name/source.name
    if architecture(target)=='x86':
     results.append(str(source.relative_to(game)));continue
    target.parent.mkdir(parents=True,exist_ok=True)
    print('Converting',str(source.relative_to(game)),flush=True)
    subprocess.run(['xvfb-run','-a','wine',str(converter),'--game','IW4MS','--convert-to','IW4','-o',str(target.parent.relative_to(game)),str(source.relative_to(game))],cwd=game,env=env,check=True,timeout=900)
    if architecture(target)!='x86':raise RuntimeError('Converted fastfile did not pass x86 probe: '+source.name)
    results.append(str(source.relative_to(game)))
  if not results:raise RuntimeError('No owned x64 Steam files were found')
  (game/'.lisp-assets-converted.json').write_text(json.dumps({'files':results,'count':len(results),'converter':'official IW4x Unlinker','liveValidation':'pending'},indent=2)+'\n')
  print('PASS private x86 conversion cache:',len(results),'files; live tests still required.',flush=True)
 finally:subprocess.run(['wineserver','-k'],env=env,timeout=10,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)

if __name__=='__main__':main()
