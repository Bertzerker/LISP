#!/usr/bin/python3
"""Run one original dedicated engine, cleaning up only its private Wine prefix."""
import json,os,signal,subprocess,sys
from pathlib import Path

def main():
 home=Path(sys.argv[1]).resolve();runtime=Path(sys.argv[2]).resolve()
 if os.geteuid()==0:raise RuntimeError('Game engines must not run as root')
 config=json.loads((home/'wine-command.json').read_text())
 env=os.environ.copy();env.update(HOME=str(home),WINEPREFIX=str(home/'wine'),WINEARCH='wow64',WINEDEBUG='-all',WINEDLLOVERRIDES=config.get('dllOverrides','mscoree,mshtml=d'))
 def terminate(signum,frame):raise SystemExit(0)
 signal.signal(signal.SIGTERM,terminate);signal.signal(signal.SIGINT,terminate);proc=None
 try:
  for key,value in config.get('registry',[]):
   subprocess.run([str(runtime/'bin/wine'),'reg','add',key,'/v','InstallDir','/t','REG_SZ','/d',value,'/f','/reg:32'],env=env,timeout=15,check=True,stdout=subprocess.DEVNULL)
  proc=subprocess.Popen(['/usr/bin/xvfb-run','-a',str(runtime/'bin/wine'),config['executable'],*config['args']],cwd=home/'game',env=env)
  return proc.wait()
 finally:
  signal.signal(signal.SIGTERM,signal.SIG_IGN)
  try:subprocess.run([str(runtime/'bin/wineserver'),'-k'],env=env,timeout=5,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  except (OSError,subprocess.TimeoutExpired):pass
  if proc and proc.poll() is None:
   proc.terminate()
   try:proc.wait(timeout=3)
   except subprocess.TimeoutExpired:proc.kill();proc.wait()

if __name__=='__main__':sys.exit(main())
