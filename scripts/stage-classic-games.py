#!/usr/bin/python3
"""Stage owned classic game media and verified engines; does not enable or deploy them.

Run as lanserver on a fresh installation with 7z, msiextract, innoextract,
Xvfb and the configured Wine runtime. Existing enabled templates are protected.
"""
import os,socket
from pathlib import Path
if os.geteuid()==0:raise RuntimeError('Run as lanserver, never root')
templates=Path('/srv/lan-party/servers/templates');templates.mkdir(parents=True,exist_ok=True)
for ident in ('eliteforce','jka','wolf2009','avp2ph'):
 if (templates/ident/'.lisp-installed').exists():raise RuntimeError('An enabled template is present; use the documented private upgrade procedure')
for port in range(27015,27019):
 with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as probe:probe.bind(('0.0.0.0',port))
import hashlib,json,subprocess,zipfile,urllib.request
from pathlib import Path
root=Path('/srv/lan-party/servers/install-media/classic-games')
root.mkdir(parents=True,exist_ok=True);root.chmod(0o700)
def run(*args):subprocess.run(args,check=True,stdout=subprocess.DEVNULL)
def extract_zip(source,dest,filter=None):
 dest.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(source) as z:
  for n in z.namelist():
   p=Path(n)
   if p.is_absolute() or '..' in p.parts:raise ValueError('Invalid archive path')
   if filter is None or filter(n):z.extract(n,dest)
games=Path('/srv/lan-party/files/Games')
extract_zip(games/'Star Wars/Jedi Academy/Star_Wars_Jedi_Knight_Jedi_Academy.zip',root/'jka-media')
for iso in (root/'jka-media').glob('*.iso'):
 dest=root/iso.stem;dest.mkdir(exist_ok=True);run('7z','x','-y','-o'+str(dest),str(iso))
extract_zip(games/'Star Trek/Elite Force/Star Trek - Voyager - Elite Force (USA) (Rerelease).zip',root/'ef-media')
# Strip Mode1/Mode2 2352-byte sectors into a private ISO after inspecting the CD mode.
binfile=next((root/'ef-media').glob('*.bin'))
with binfile.open('rb') as f:
 header=f.read(24)
mode=header[15]
offset=16 if mode==1 else 24 if mode==2 else None
assert offset is not None, 'Unsupported CD sector mode'
iso=root/'ef-media/disc.iso'
with binfile.open('rb') as src,iso.open('wb') as dst:
 while chunk:=src.read(2352*1024):
  assert len(chunk)%2352==0
  for pos in range(0,len(chunk),2352):dst.write(chunk[pos+offset:pos+offset+2048])
dest=root/'ef-disc';dest.mkdir(exist_ok=True);run('7z','x','-y','-o'+str(dest),str(iso))
dest=root/'wolf-lite';dest.mkdir(exist_ok=True)
run('7z','x','-y','-o'+str(dest),str(games/'Wolfenstein/Wolfenstein 2009/dark-dvd1.iso'),'LiteServer/Setup/Data/*','LiteServer/Docs/ENU/*')
patch=root/'wolf-patch';patch.mkdir(exist_ok=True)

extract_zip(games/'Aliens versus Predator/Aliens Versus Predator 2 Primal Hunt/avp2_avp2ph_aio_exe.zip',root/'avp-media',lambda n:n.endswith('.exe') and 'Full Game' in n)
for installer in (root/'avp-media').rglob('*.exe'):
 print('AvP installer:',installer.relative_to(root),flush=True)
 # Extract only, never run or apply bundled No-CD replacements.
 dest=root/('avp-ph' if 'Primal Hunt.exe' in installer.name else 'avp-base');dest.mkdir(exist_ok=True)
 result=subprocess.run(['innoextract','-d',str(dest),str(installer)],stdout=subprocess.DEVNULL)
 if result.returncode:run('7z','x','-y','-o'+str(dest),str(installer))
extract_zip(games/'Aliens versus Predator/Aliens Versus Predator 2 Primal Hunt/avp2phmsinstall_1.1.zip',root/'avp-ph-patch')

import os,shutil,tarfile
media=root
runtime=Path(os.environ.get('LISP_CLASSIC_WINE_RUNTIME','/usr/share/steam/compatibilitytools.d/proton-cachyos-slr/files'))
wine=runtime/'bin/wine';wineserver=runtime/'bin/wineserver'
if not wine.is_file():raise RuntimeError('Configure LISP_CLASSIC_WINE_RUNTIME with a working Wine/Proton runtime')
assets=[('jka','OpenJK-linux-x86_64.tar.gz','https://github.com/JACoders/OpenJK/releases/download/latest/OpenJK-linux-x86_64.tar.gz','8116857544cc8ca90713edae43db0b13108cb044af7ea7312c739a677464c297'),('eliteforce','ioEF-cMod_v1.30_linux_x86_64.zip','https://github.com/Chomenor/ioef-cmod/releases/download/v1.30/ioEF-cMod_v1.30_linux_x86_64.zip','19426ca04167f13e6927117dade0435625dda3dc8143214894cc80679ef47245')]
def fetch(name,url,digest):
 path=media/name
 if not path.exists():urllib.request.urlretrieve(url,path)
 h=hashlib.sha256()
 with path.open('rb') as f:
  while block:=f.read(1024*1024):h.update(block)
 if h.hexdigest()!=digest:raise RuntimeError('Upstream asset changed or download is damaged: '+name)
 return path
def copy(source,dest):
 dest.mkdir(parents=True,exist_ok=True);run('cp','-a','--reflink=auto',str(source)+'/.',str(dest))
for ident,name,url,digest in assets:
 archive=fetch(name,url,digest);target=templates/ident;target.mkdir(exist_ok=True)
 if name.endswith('.zip'):extract_zip(archive,target)
 else:
  with tarfile.open(archive) as t:t.extractall(target,filter='data')
 if ident=='jka':
  (target/'base').mkdir(exist_ok=True)
  for p in media.glob('LucasArts*/GameData/GameData/base/*.pk3'):shutil.copy2(p,target/'base'/p.name)
 else:copy(media/'ef-disc/Setup/BaseEF',target/'baseEF')
 for p in target.rglob('*'):
  if p.is_file() and ('x86_64' in p.name or p.suffix=='.so' or p.name=='cMod-dedicated'):p.chmod(0o755)
 (target/'.lisp-source.json').write_text(json.dumps({'asset':name,'url':url,'sha256':digest}))
copy(media/'wolf-lite/LiteServer/Setup/Data',templates/'wolf2009')
isx=fetch('ISx-v0.3.11.7z','https://github.com/lifenjoiner/ISx/releases/download/v0.3.11/ISx-v0.3.11.7z','145c254a8e656a2f1df9a384759700a2e686ca5e760fea1103224e3a2b818417')
run('7z','x','-y','-o'+str(media/'isx'),str(isx))
expanded=media/'wolf-patch-expanded';expanded.mkdir(exist_ok=True)
source=games/'Wolfenstein/Wolfenstein 2009/WolfensteinLiteServer_1_2_PatchSetup.exe';shutil.copy2(source,expanded/source.name)
env=os.environ.copy();env.update(HOME=str(media),WINEPREFIX=str(media/'wolf-extract-prefix'),WINEARCH='wow64',WINEDEBUG='-all',WINEDLLOVERRIDES='mscoree,mshtml=d')
try:subprocess.run(['xvfb-run','-a',str(wine),str(next((media/'isx').rglob('ISx.exe'))),str(expanded/source.name)],cwd=expanded,env=env,check=True,timeout=45)
finally:subprocess.run([str(wineserver),'-k'],env=env,timeout=5)
msi=next(expanded.rglob('*.msi'));run('msiextract','-C',str(expanded/'data'),str(msi));copy(expanded/'data/Program Files/Data',templates/'wolf2009')
installer=next((media/'avp-ph-patch').glob('*.exe'));run('7z','x','-y','-o'+str(media/'avp-ph-patch-files'),str(installer))
copy(media/'avp-base',templates/'avp2ph');copy(media/'avp-ph',templates/'avp2ph')
base=templates/'avp2ph/base-resources';base.mkdir(exist_ok=True)
for p in (media/'avp-base').glob('*.REZ'):run('cp','--reflink=auto',str(p),str(base))
for p in (media/'avp-ph-patch-files').iterdir():
 if p.is_file() and p.suffix.lower() in ('.rez','.dll'):shutil.copy2(p,templates/'avp2ph'/p.name)
prefix=templates/'classic-wine-prefix';prefix.mkdir(exist_ok=True)
donor=templates/'swbf2-wine-prefix'
if donor.is_dir():copy(donor,prefix)
else:
 env.update(WINEPREFIX=str(prefix))
 try:subprocess.run(['xvfb-run','-a',str(runtime/'bin/wineboot'),'-u'],env=env,timeout=60,check=True)
 finally:subprocess.run([str(wineserver),'-k'],env=env,timeout=5)
print('Private templates staged. Run live tests and publish only passing games; markers were not created.')
