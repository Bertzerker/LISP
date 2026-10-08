#!/usr/bin/python3
"""Publish community features after installing their official pinned runtimes.

Keeps games and firewall untouched. Account/forum state is backed up privately.
"""
import json,os,pathlib,shutil,subprocess,time,zipfile
P=pathlib.Path
ROOT=P(__file__).resolve().parents[1]

def run(args,**kw):subprocess.run(args,check=True,**kw)
def install(source,dest,mode=0o644):
    run(['install','-m',oct(mode)[2:],str(source),str(dest)])
def main():
    assert os.geteuid()==0,'Run as root'
    config=P('/etc/nginx/lan-party.conf').read_text()
    for glob in ['/etc/nginx/lisp-community/http/*.conf','/etc/nginx/lisp-community/portal/*.conf']:
        assert glob in config,'Add the optional community include from config/nginx.conf: '+glob
    assert P('/opt/lisp-bracket/backend/.venv/bin/python').exists(),'Install community runtimes first'
    backup=P('/srv/lan-party/community-setup/backup')/time.strftime('%Y%m%d-%H%M%S');backup.mkdir(parents=True,mode=0o700);backup.chmod(0o700)
    for name in ['accounts.py','account_server.py','account_client.py']:
        existing=P('/opt/lan-portal')/name
        if existing.exists():shutil.copy2(existing,backup/name)
    for name in ['accounts.py','account_server.py','account_client.py','community.py','community_server.py']:install(ROOT/'src'/name,P('/opt/lan-portal')/name)
    for source,dest in [('Lisp.php','Sources/Lisp.php'),('bridge.php','lisp-bridge.php'),('setup.php','lisp-setup.php')]:install(ROOT/'forum'/source,P('/opt/lisp-forum')/dest)
    for name in ['Lisp.php','lisp-bridge.php','lisp-setup.php']:
        path=P('/opt/lisp-forum')/('Sources/Lisp.php' if name=='Lisp.php' else name)
        run(['php','-c','/etc/lisp/community/forum-php.ini','-l',str(path)])
    install(ROOT/'scripts/patch-bracket-frontend.py','/opt/lisp-bracket/lisp-patch-frontend.py')
    run(['runuser','-u','lanbracket','--','python3','/opt/lisp-bracket/lisp-patch-frontend.py','/opt/lisp-bracket'])
    frontend='/opt/lisp-bracket/frontend'
    run(['runuser','-u','lanbracket','--','pnpm','install','--frozen-lockfile'],cwd=frontend)
    run(['runuser','-u','lanbracket','--','pnpm','run','build'],cwd=frontend)
    # Freeze retired forum writes before taking the online migration snapshot.
    marker=P('/var/lib/lisp-accounts/forum-migrated.json')
    if not marker.exists():marker.write_text(json.dumps({'forum':'/forum/','migration':'in-progress'}));marker.chmod(0o600)
    run(['systemctl','restart','lisp-accounts'])
    run(['python3',str(ROOT/'scripts/migrate-community.py')])
    run(['python3',str(ROOT/'scripts/repair-forum-runtime.py')])
    marker.write_text(json.dumps({'forum':'/forum/','migration':'complete'}));marker.chmod(0o600)
    site=P('/srv/lan-party/site')
    for name in ['tournaments','profile']:
        (site/name).mkdir(exist_ok=True);install(ROOT/'web'/(name+'.html'),site/name/'index.html')
    for name in ['tournaments.js','profile.js','community.css','forum-portal.css','forum-editor.css','shell.js','servers.js']:install(ROOT/'web'/name,site/name)
    for kind,name in [('http','community-http.conf'),('portal','community-locations.conf')]:
        directory=P('/etc/nginx/lisp-community')/kind;directory.mkdir(parents=True,exist_ok=True);install(ROOT/'config'/name,directory/'runtime.conf')
    run(['python3',str(ROOT/'scripts/package-bracket-source.py'),'/opt/lisp-bracket','/srv/lan-party/community-source'])
    run(['nginx','-t','-c','/etc/nginx/lan-party.conf'])
    run(['systemctl','daemon-reload']);run(['systemctl','enable','--now','lisp-community'])
    run(['systemctl','restart','lisp-community','lisp-forum']);run(['systemctl','reload','lan-party-web'])
    print('Community portal published. Game controller and firewall unchanged.')
if __name__=='__main__':main()
