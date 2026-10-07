#!/usr/bin/python3
"""Apply supplied retail patch file payloads to a private WaW server copy.

Run as lanserver. InstallShield runs only inside a disposable extraction prefix;
no CD key is required, recorded or embedded. The original DVD/files stay intact.
"""
import hashlib,json,os,pathlib,shutil,subprocess
ROOT=pathlib.Path('/srv/lan-party/servers')
SOURCE=pathlib.Path('/srv/lan-party/files/Games/Call of Duty/WaW')
PATCHES=['1.1','1.2','1.3','1.4','1.4.1-DEU','1.5','1.6','1.7']

def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
 return h.hexdigest()

def main():
 if os.geteuid()==0:raise SystemExit('Run as the unprivileged lanserver account')
 home=ROOT/'install-media/waw-retail-patches';home.mkdir(mode=0o700,exist_ok=True)
 prefix=home/'wine'
 if not prefix.exists():subprocess.run(['cp','-a','--reflink=auto',str(ROOT/'templates/cod-wine-prefix'),str(prefix)],check=True)
 env=os.environ.copy();env.update(HOME=str(home),WINEPREFIX=str(prefix),WINEDEBUG='-all',WINEDLLOVERRIDES='mscoree,mshtml=d')
 game=ROOT/'templates/t4';backup=home/'dvd-original'
 if not backup.exists():subprocess.run(['cp','-a','--reflink=auto',str(game),str(backup)],check=True)
 report={'source':'supplied retail DVD patches','patches':[],'uncut':False}
 for version in PATCHES:
  source=SOURCE/('CoDWaW-'+version+'-PatchSetup.exe')
  if not source.is_file():raise FileNotFoundError(source.name)
  cache=prefix/('drive_c/patchcache-'+version);cache.mkdir(exist_ok=True)
  packages=list(cache.rglob('*.msi'))
  if not packages:
   windows='C:\\patchcache-'+version
   try:
    subprocess.run(['xvfb-run','-a','wine',str(source),'/s','/b'+windows,'/v/qn'],cwd=home,env=env,timeout=180,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
   except subprocess.TimeoutExpired:
    # A retail patch may wait for an installed-product dialog after caching.
    # Only a complete MSI whose cabinets successfully extract is used below.
    pass
   finally:subprocess.run(['wineserver','-k'],env=env,timeout=10,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
   packages=list(cache.rglob('*.msi'))
  if len(packages)!=1:raise RuntimeError('Expected one cached patch MSI: '+version)
  extracted=home/('payload-'+version);extracted.mkdir(exist_ok=True)
  if not (extracted/'.lisp-extracted').exists():
   subprocess.run(['msiextract','-C',str(extracted),str(packages[0])],check=True,stdout=subprocess.DEVNULL)
   (extracted/'.lisp-extracted').write_text('Cabinet payload extracted successfully\n')
  executables=list(extracted.rglob('CoDWaWmp.exe'))
  if executables:
   base=executables[0].parent
   if base.name.startswith('.:'):base=base.parent
  else:
   # The German 1.4.1 hotfix only updates asset files, not the executable.
   roots=[p for p in extracted.rglob('Data') if p.is_dir() and p.parent.name=='Program Files']
   if len(roots)!=1:raise RuntimeError('Cannot identify patch game-data root: '+version)
   base=roots[0]
  count=0
  for file in base.rglob('*'):
   if not file.is_file() or file.is_symlink():continue
   relative=file.relative_to(base)
   # MSI target:source names select the target segment. WW is the worldwide
   # variant, restored by the supplied uncut conversion after the updates.
   if any(part=='.:German' for part in relative.parts) and 'DEU' not in version:continue
   parts=[part.split(':',1)[0].split('|')[-1] for part in relative.parts]
   parts=[part for part in parts if part not in ('','.')] 
   if not parts or '..' in parts:raise ValueError('Invalid patch destination')
   dest=game.joinpath(*parts);dest.parent.mkdir(parents=True,exist_ok=True)
   subprocess.run(['cp','--reflink=auto','--',str(file),str(dest)],check=True);count+=1
  report['patches'].append({'version':version,'sha256':digest(source),'filesApplied':count})
  print('Applied retail patch payload',version,'files',count,flush=True)
 archive=SOURCE/'Uncut Patch.7z';uncut=home/'uncut-installer';uncut.mkdir(exist_ok=True)
 exe=uncut/'CallOfDutyWaW_UCPV4/CallOfDutyWaW_UCPV4.exe'
 if not exe.exists():subprocess.run(['7z','x','-y','-o'+str(uncut),str(archive)],check=True,stdout=subprocess.DEVNULL)
 output=home/'uncut-files';output.mkdir(exist_ok=True)
 subprocess.run(['innoextract','--silent','--output-dir',str(output),str(exe)],check=True)
 app=output/'app'
 if not (app/'CoDWaWmp.exe').exists():raise RuntimeError('Uncut payload is incomplete')
 # Remaining unchanged original maps are shared between languages. The uncut
 # payload supplies the English localized counterparts and additional assets.
 german=game/'zone/German'
 if not german.exists():german=game/'zone/german'
 english=game/'zone/english';english.mkdir(exist_ok=True)
 if german.is_dir():
  subprocess.run(['cp','-an','--reflink=auto',str(german)+'/.',str(english)],check=True)
 subprocess.run(['cp','-a','--reflink=auto',str(app)+'/.',str(game)],check=True)
 report.update(uncut=True,uncutSha256=digest(archive),version=(game/'version.inf').read_text(errors='replace') if (game/'version.inf').exists() else 'unknown')
 (game/'.lisp-retail-patched.json').write_text(json.dumps(report,indent=2)+'\n')
 print('Retail patches and uncut files applied; live validation is still required.',flush=True)

if __name__=='__main__':main()
