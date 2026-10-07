#!/usr/bin/python3
"""Run and stop only one Call of Duty Wine prefix."""
import json,os,signal,subprocess,sys
from pathlib import Path
def main():
 home=Path(sys.argv[1]).resolve();job=json.loads((home/'cod-launch.json').read_text())
 env=os.environ.copy();env.update(HOME=str(home),WINEPREFIX=str(home/'wine'),WINEDEBUG=os.environ.get('LISP_WINE_DEBUG','-all,err+all'),WINEDLLOVERRIDES='mscoree,mshtml=d',DXVK_LOG_LEVEL='none')
 def stop(signum,frame):raise SystemExit(0)
 signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop);child=None
 try:
  child=subprocess.Popen(['/usr/bin/xvfb-run','-a',job['wine'],job['executable'],*job['args']],cwd=job['cwd'],env=env)
  return child.wait()
 finally:
  signal.signal(signal.SIGTERM,signal.SIG_IGN)
  server=Path(job['wine']).with_name('wineserver')
  try:subprocess.run([str(server),'-k'],env=env,timeout=5,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  except (OSError,subprocess.TimeoutExpired):pass
  if child and child.poll() is None:
   child.terminate()
   try:child.wait(timeout=3)
   except subprocess.TimeoutExpired:child.kill();child.wait()
if __name__=='__main__':sys.exit(main())
