#!/usr/bin/python3
"""Use verified 1.7 dedicated assets in the private patched retail template.

Retain both original DVD backup and all patched/uncut data separately. The
mixed-language retail copy failed actual Plutonium startup on duplicate fonts.
"""
import hashlib,json,os,pathlib,subprocess,tempfile
ROOT=pathlib.Path('/srv/lan-party/servers')
EXPECTED='2c6be1bb66ea631b9b2e7ae6216c6680'
def main():
 if os.geteuid()==0:raise SystemExit('Run as lanserver')
 game=ROOT/'templates/t4';marker=game/'.lisp-server-assets.json'
 if marker.exists():raise SystemExit('Verified server assets were already applied; do not repeat')
 if (game/'.lisp-installed').exists():raise SystemExit('Do not repair a published game template')
 archive=ROOT/'runtimes/codwaw-lnxded-1.7-full.tar.xz'
 digest=hashlib.md5()
 with archive.open('rb') as f:
  for block in iter(lambda:f.read(8*1024*1024),b''):digest.update(block)
 if digest.hexdigest()!=EXPECTED:raise ValueError('Dedicated package checksum failed')
 source=ROOT/'install-media/waw-1.7';home=ROOT/'install-media/waw-retail-patches'
 stage=pathlib.Path(tempfile.mkdtemp(dir=home,prefix='server-assets-'))
 for name in ['main','zone']:
  if not (source/name).is_dir():raise FileNotFoundError('Dedicated asset folder missing: '+name)
  if (home/('patched-'+name+'-before-server-repair')).exists():raise RuntimeError('A previous repair backup exists; inspect before continuing')
  subprocess.run(['cp','-a','--reflink=auto',str(source/name),str(stage/name)],check=True)
 if not (stage/'zone/english/common_mp.ff').is_file():raise RuntimeError('Required server asset is missing')
 for name in ['main','zone']:
  (game/name).rename(home/('patched-'+name+'-before-server-repair'))
  (stage/name).rename(game/name)
 marker.write_text(json.dumps({'packageMd5':EXPECTED,'reason':'mixed retail/uncut font-asset startup failure','preservedPatchedData':str(home),'liveValidation':'pending'},indent=2)+'\n')
 print('PASS verified 1.7 dedicated data applied privately; patched/uncut data retained. Live tests are required.',flush=True)
if __name__=='__main__':main()
