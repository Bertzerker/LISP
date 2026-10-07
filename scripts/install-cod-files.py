#!/usr/bin/python3
"""Stage already-owned Call of Duty data and fetch official mod runtimes.

No account credentials or game keys are accepted or saved by this helper.
Run as root on the LAN server. Installed markers require separate live tests.
"""
import concurrent.futures,hashlib,json,os,pathlib,pwd,subprocess,tarfile,tempfile,urllib.request
ROOT=pathlib.Path('/srv/lan-party/servers')
STEAM=pathlib.Path('/home/robert/.local/share/Steam/steamapps/common')
GAMES={'iw4x':'Call of Duty Modern Warfare 2','iw5':'Call of Duty Modern Warfare 3','t5':'Call of Duty Black Ops','t6':'Call of Duty Black Ops II'}
def manifest_hash(blob):
 return hashlib.sha1(blob).hexdigest()
def fetch(url,path,sha=None,size=None,sha256=None):
 path.parent.mkdir(parents=True,exist_ok=True)
 if path.is_file() and sha and manifest_hash(path.read_bytes())==sha:return
 if path.is_file() and sha256 and hashlib.sha256(path.read_bytes()).hexdigest()==sha256:return
 tmp=path.with_name(path.name+'.partial')
 # curl can resume interrupted large CDN transfers without losing the prefix.
 subprocess.run(['curl','--fail','--location','--silent','--show-error','--retry','8','--retry-all-errors','--retry-delay','10','--connect-timeout','20','--speed-limit','1024','--speed-time','90','--continue-at','-','--output',str(tmp),url],check=True)
 blob=tmp.read_bytes()
 if sha and manifest_hash(blob)!=sha:raise ValueError('Manifest checksum mismatch: '+path.name)
 if sha256 and hashlib.sha256(blob).hexdigest()!=sha256:raise ValueError('Release checksum mismatch: '+path.name)
 if size and len(blob)!=size:raise ValueError('Manifest size mismatch: '+path.name)
 tmp.replace(path)
def main():
 if os.geteuid()!=0:raise SystemExit('Run as root')
 runtime=ROOT/'runtimes/plutonium';runtime.mkdir(parents=True,exist_ok=True)
 runtime.parent.chmod(0o755)
 for game,folder in GAMES.items():
  source=STEAM/folder;target=ROOT/'templates'/game
  if not source.is_dir():raise FileNotFoundError('Missing installed game: '+folder)
  target.mkdir(exist_ok=True)
  if not (target/'.lisp-files-copied').is_file():
   subprocess.run(['cp','-a','--reflink=auto',str(source)+'/.',str(target)],check=True)
   (target/'.lisp-files-copied').write_text('Owned Steam data staged; validation pending.\n')
  print('Staged',game,flush=True)
 waw=ROOT/'templates/t4';waw.mkdir(exist_ok=True)
 if not (waw/'.lisp-files-copied').is_file():
  source=ROOT/'install-media/waw/Setup/Data'
  if not (source/'CoDWaWmp.exe').is_file():raise FileNotFoundError('Mount the owned World at War DVD image first')
  subprocess.run(['cp','-a','--reflink=auto',str(source)+'/.',str(waw)],check=True)
  (waw/'.lisp-files-copied').write_text('Owned German DVD 1.0 data staged; patches and validation pending.\n')
 print('Staged World at War DVD data',flush=True)
 metadata=json.loads((ROOT/'plutonium-metadata.json').read_text())
 info=json.load(urllib.request.urlopen(metadata['manifests'][0],timeout=60))
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
  futures=[]
  for entry in info['files']:
   name=pathlib.PurePosixPath(entry['name'])
   if name.is_absolute() or '..' in name.parts:raise ValueError('Invalid runtime path')
   futures.append(pool.submit(fetch,info['baseUrl']+entry['hash'],runtime/name,entry['hash'],entry['size']))
  try:
   for f in concurrent.futures.as_completed(futures):f.result()
  except Exception:
   for f in futures:f.cancel()
   raise
 (runtime/'lisp-runtime-version.json').write_text(json.dumps({'revision':info['revision'],'product':info['product']})+'\n')
 print('Verified Plutonium runtime revision',info['revision'],flush=True)
 release=json.loads((ROOT/'iw4x-release-metadata.json').read_text())
 asset=next(x for x in release['assets'] if x['name'].endswith('x86_64-linux-glibc.tar.xz'))
 archive=ROOT/'runtimes'/asset['name'];fetch(asset['browser_download_url'],archive,size=asset['size'],sha256=asset.get('digest','').removeprefix('sha256:') or None)
 # Extract separately and rename into place. An updater already running from
 # this template keeps its inode and does not cause ETXTBSY during staging.
 target=ROOT/'templates/iw4x'
 with tempfile.TemporaryDirectory(prefix='iw4x-release-',dir=ROOT/'runtimes') as scratch:
  staging=pathlib.Path(scratch)
  with tarfile.open(archive) as t:t.extractall(staging,filter='data')
  for file in staging.rglob('*'):
   if file.is_symlink():raise ValueError('Unexpected launcher archive symlink')
   if file.is_file():
    dest=target/file.relative_to(staging);dest.parent.mkdir(parents=True,exist_ok=True)
    file.replace(dest)
 user=pwd.getpwnam('lanserver')
 for folder in [runtime,*[ROOT/'templates'/g for g in [*GAMES,'t4']]]:
  subprocess.run(['chown','-R',str(user.pw_uid)+':'+str(user.pw_gid),str(folder)],check=True)
 print('Call of Duty data and launch tools prepared; no installed markers created.',flush=True)
if __name__=='__main__':main()
