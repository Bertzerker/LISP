#!/usr/bin/python3
"""Stage official pre-update MW3 server depots with anonymous Steam access.

Does not modify an installed Steam game or enable a portal game. Depot IDs
come from the firsthand downgrade guide on Plutonium's support forum:
https://forum.plutonium.pw/topic/46446/mw3-downgrade-and-update-prevention-guide
"""
import json,os,pathlib,subprocess
ROOT=pathlib.Path('/srv/lan-party/servers')
DEPOTS=[(42682,'6067691797475126381'),(42683,'6381783964590594065'),(42751,'9089183337461621316')]

def main():
 if os.geteuid()==0:raise SystemExit('Run as lanserver')
 home=ROOT/'install-media/iw5-legacy';home.mkdir(mode=0o700,exist_ok=True)
 steamcmd=ROOT/'steamcmd/steamcmd.sh'
 # A dedicated SteamCMD cache isolates anonymous metadata from other installs.
 runtime=home/'steamcmd'
 if not runtime.exists():subprocess.run(['cp','-a','--reflink=auto',str(steamcmd.parent),str(runtime)],check=True)
 env=os.environ.copy();env['HOME']=str(home)
 report=[]
 for depot,manifest in DEPOTS:
  marker=home/('depot-'+str(depot)+'.json')
  target=runtime/('steamapps/content/app_42750/depot_'+str(depot))
  if marker.exists() and target.is_dir():
   report.append(json.loads(marker.read_text()));continue
  print('Requesting official Steam depot',depot,'manifest',manifest,flush=True)
  log=home/('depot-'+str(depot)+'.log')
  with log.open('w') as output:
   result=subprocess.run([str(runtime/'steamcmd.sh'),'+login','anonymous','+download_depot','42750',str(depot),manifest,'+quit'],cwd=runtime,env=env,stdout=output,stderr=subprocess.STDOUT)
  text=log.read_text(errors='replace')
  if result.returncode or 'Depot download complete' not in text or not target.is_dir():
   tail='\n'.join(text.splitlines()[-12:])
   raise RuntimeError('Official anonymous depot download did not complete; no game files were applied.\n'+tail)
  item={'app':42750,'depot':depot,'manifest':manifest,'folder':str(target),'files':sum(p.is_file() for p in target.rglob('*'))}
  if not item['files']:raise RuntimeError('Depot is empty')
  marker.write_text(json.dumps(item,indent=2)+'\n');report.append(item)
 (home/'staged-depots.json').write_text(json.dumps(report,indent=2)+'\n')
 print('Legacy Steam depots staged; compatibility validation is required before applying.',flush=True)

if __name__=='__main__':main()
