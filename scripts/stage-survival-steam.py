#!/usr/bin/python3
"""Privately stage completed local Steam installations; do not download games."""
import hashlib,json,os,pathlib,pwd,re,subprocess,time
import argparse
cli=argparse.ArgumentParser(description=__doc__)
cli.add_argument('--root',type=pathlib.Path,default=pathlib.Path('/srv/lan-party/servers'))
cli.add_argument('--steamapps',type=pathlib.Path,default=pathlib.Path('/home/robert/.local/share/Steam/steamapps'))
options=cli.parse_args();R=options.root.resolve();STEAM=options.steamapps.resolve()
bootstrap=pathlib.Path(__file__).resolve().parents[1]/'src/LispZomboid.java'
assert os.geteuid()==0
owner=pwd.getpwnam('lanserver')
for ident,app in [('zomboid','380870'),('sevendays','294420')]:
 text=(STEAM/('appmanifest_'+app+'.acf')).read_text();data=dict(re.findall(r'"([^"\n]+)"\s+"([^"\n]*)"',text));assert data['StateFlags']=='4','Steam installation is not complete'
 source=STEAM/'common'/data['installdir'];assert source.is_dir() and source.resolve().parent==(STEAM/'common').resolve()
 target=R/'templates'/ident;staged=R/'templates'/(ident+'-steam-staging');assert not staged.exists(),'An existing staging operation needs inspection'
 if (target/'.lisp-source.json').exists() and json.loads((target/'.lisp-source.json').read_text())['buildid']==data['buildid']:
  print('Already staged',ident,data['buildid'],flush=True);continue
 assert not (target/'.lisp-installed').exists(),'Stop published game instances before replacing their template'
 staged.mkdir(mode=0o700);subprocess.run(['cp','-a','--reflink=auto',str(source)+'/.',str(staged)],check=True)
 stamp={'appid':app,'buildid':data['buildid'],'source':'local Steam dedicated server','staged':int(time.time())};(staged/'.lisp-source.json').write_text(json.dumps(stamp,indent=2)+'\n')
 for folder,dirs,files in os.walk(staged):
  os.chown(folder,owner.pw_uid,owner.pw_gid)
  for name in files:os.chown(pathlib.Path(folder)/name,owner.pw_uid,owner.pw_gid)
 if ident=='zomboid':
  compiler=R/'ecj-3.40.0.jar';assert hashlib.sha256(compiler.read_bytes()).hexdigest()=='05cc22a24e7982970f63a405fc6c820bc80b806f27f3c5a6236fc475f8f7152b'
  subprocess.run(['runuser','-u','lanserver','--',str(staged/'jre64/bin/java'),'-jar',str(compiler),'-17','-d',str(staged/'lispclasses'),str(bootstrap)],check=True)
  assert (staged/'lispclasses/LispZomboid.class').exists()
 if target.exists():
  backup=R/'install-media'/(ident+'-before-steam-'+time.strftime('%Y%m%d-%H%M%S'));assert not backup.exists();target.rename(backup)
 staged.rename(target);print('Staged',ident,'Steam build',data['buildid'],'without replacing the Steam original or saved worlds',flush=True)
