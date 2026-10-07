#!/usr/bin/python3
"""Run one private Battlefront Wine prefix and clean up its background services."""
import os, signal, subprocess, sys
from pathlib import Path

def main():
    home=Path(sys.argv[1]).resolve();runtime=Path(sys.argv[2]).resolve()
    env=os.environ.copy();env.update(HOME=str(home),WINEPREFIX=str(home/'wine'),WINEARCH='wow64',WINEDEBUG='-all',WINEDLLOVERRIDES='mscoree,mshtml=d')
    def terminate(signum,frame):raise SystemExit(0)
    signal.signal(signal.SIGTERM,terminate);signal.signal(signal.SIGINT,terminate)
    proc=None
    try:
        proc=subprocess.Popen(['/usr/bin/xvfb-run','-a',str(runtime/'bin/wine'),'BattlefrontII.exe','/win','/norender','/nosound','/nointro','/autonet','dedicated','/resolution','640','480'],cwd=home/'game',env=env)
        return proc.wait()
    finally:
        # wineserver detaches from the process group; kill only this instance's prefix.
        signal.signal(signal.SIGTERM,signal.SIG_IGN)
        try:subprocess.run([str(runtime/'bin/wineserver'),'-k'],env=env,timeout=3,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        except (OSError,subprocess.TimeoutExpired):pass
        if proc and proc.poll() is None:
            proc.terminate()
            try:proc.wait(timeout=2)
            except subprocess.TimeoutExpired:proc.kill();proc.wait()

if __name__=='__main__':sys.exit(main())
