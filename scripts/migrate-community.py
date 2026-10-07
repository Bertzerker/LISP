#!/usr/bin/python3
"""Private online backup and credential-free export. Migration never alters accounts."""
import json,os,pathlib,sqlite3,subprocess,time
assert os.geteuid()==0,'Run as root'
root=pathlib.Path('/srv/lan-party/community-setup');root.mkdir(mode=0o700,exist_ok=True)
backup=root/('accounts-before-smf-'+time.strftime('%Y%m%d-%H%M%S')+'.sqlite3')
source=sqlite3.connect('file:/var/lib/lisp-accounts/accounts.sqlite3?mode=ro',uri=True);source.row_factory=sqlite3.Row
with sqlite3.connect(backup) as target:source.backup(target)
backup.chmod(0o600)
value={name:[dict(row) for row in source.execute(sql)] for name,sql in {
 'users':'SELECT id,name,role,created FROM users', 'boards':'SELECT * FROM boards', 'topics':'SELECT * FROM topics','posts':'SELECT * FROM posts'}.items()};source.close()
value['members']={str(u['id']):u for u in value['users']}
export=pathlib.Path('/var/lib/lisp-forum/legacy-export.json');export.write_text(json.dumps(value));export.chmod(0o600)
import pwd
os.chown(export,pwd.getpwnam('lanforum').pw_uid,-1)
subprocess.run(['runuser','-u','lanforum','--','php','-c','/etc/lisp/community/forum-php.ini','/opt/lisp-forum/lisp-setup.php',str(export)],check=True)
export.unlink()
print('Legacy forum backed up privately and migrated. No account credentials were exported.')
