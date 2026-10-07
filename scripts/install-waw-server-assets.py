#!/usr/bin/python3
"""Fetch the versioned World at War 1.7 dedicated-server package.

The package/checksum come from LinuxGSM's maintained install_server_files.sh.
Extract to staging only; preserve the owned DVD installation until reviewed.
"""
import hashlib,pathlib,subprocess,tarfile,urllib.request
ROOT=pathlib.Path('/srv/lan-party/servers')
URL='https://linuxgsm.download/CallOfDutyWorldAtWar/codwaw-lnxded-1.7-full.tar.xz'
MD5='2c6be1bb66ea631b9b2e7ae6216c6680'
def main():
 dest=ROOT/'runtimes/codwaw-lnxded-1.7-full.tar.xz';dest.parent.mkdir(parents=True,exist_ok=True)
 if not dest.is_file():
  tmp=dest.with_suffix(dest.suffix+'.partial')
  subprocess.run(['curl','--fail','--location','--silent','--show-error','--retry','12','--retry-all-errors','--retry-delay','10','--connect-timeout','20','--speed-limit','1024','--speed-time','90','--continue-at','-','--output',str(tmp),URL],check=True)
  digest=hashlib.md5()
  with tmp.open('rb') as f:
   for chunk in iter(lambda:f.read(8*1024*1024),b''):digest.update(chunk)
  if digest.hexdigest()!=MD5:raise ValueError('World at War package checksum mismatch')
  tmp.rename(dest)
 digest=hashlib.md5()
 with dest.open('rb') as f:
  for chunk in iter(lambda:f.read(8*1024*1024),b''):digest.update(chunk)
 if digest.hexdigest()!=MD5:raise ValueError('Saved World at War package checksum mismatch')
 staging=ROOT/'install-media/waw-1.7';staging.mkdir(parents=True,exist_ok=True)
 with tarfile.open(dest) as archive:archive.extractall(staging,filter='data')
 print('Verified and staged World at War 1.7 server package',flush=True)
if __name__=='__main__':main()
