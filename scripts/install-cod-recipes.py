#!/usr/bin/python3
"""Fetch the IW5 recipe files linked by Plutonium's hosting documentation."""
import hashlib,json,os,pathlib,shutil,urllib.request
ROOT=pathlib.Path('/srv/lan-party/servers/templates/iw5')
REPO='xerxes-at/IW5ServerConfig'

def get(url):return urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'LISP-LAN-installer'}),timeout=30).read()
def main():
 if os.geteuid()==0:raise SystemExit('Run as lanserver')
 # Current Steam MW3 packages omit legacy x86 audio/video imports needed by
 # Plutonium. The official IW4x update supplies the matching x86 libraries;
 # copy only missing files into this private server template.
 dependencies={}
 for name in ['mss32.dll','binkw32.dll']:
  source=ROOT.parent/'iw4x'/name;dest=ROOT/name
  if not dest.exists():
   if not source.exists():raise FileNotFoundError('Prepare the verified IW4x runtime first: '+name)
   shutil.copy2(source,dest)
  dependencies[name]=hashlib.sha256(dest.read_bytes()).hexdigest()
 tree=json.loads(get('https://api.github.com/repos/'+REPO+'/git/trees/master?recursive=1'))
 files=[entry for entry in tree['tree'] if entry['type']=='blob' and entry['path'].startswith('admin/') and entry['path'].endswith('.dsr')]
 if not files:raise RuntimeError('No upstream recipes found')
 admin=ROOT/'admin';admin.mkdir(exist_ok=True)
 for entry in files:
  name=pathlib.PurePosixPath(entry['path']);data=get('https://raw.githubusercontent.com/'+REPO+'/'+tree['sha']+'/'+name.as_posix())
  if hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()!=entry['sha']:raise ValueError('Recipe Git blob mismatch')
  path=ROOT.joinpath(*name.parts);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
 (admin/'lisp-recipes-version.json').write_text(json.dumps({'repository':REPO,'commit':tree['sha'],'files':len(files),'legacyImports':dependencies})+'\n')
 print('Installed and verified',len(files),'officially linked IW5 recipes')
if __name__=='__main__':main()
