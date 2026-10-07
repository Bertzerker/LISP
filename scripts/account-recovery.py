#!/usr/bin/python3
"""Root-only account bootstrap/recovery; never print passwords or stored hashes."""
import argparse,getpass,os,sqlite3,sys,time
from pathlib import Path
sys.path.insert(0,'/opt/lan-portal')
from accounts import Accounts,interface
def main():
    if os.geteuid()!=0:raise SystemExit('Run this on the LAN server with sudo.')
    p=argparse.ArgumentParser();p.add_argument('action',choices=['bootstrap','bind','password']);p.add_argument('--name',default='admin');p.add_argument('--ip');a=p.parse_args()
    auth=Accounts('/var/lib/lisp-accounts')
    if a.action=='bootstrap':
        with auth.db() as c:
            if c.execute('SELECT 1 FROM users').fetchone():print('Existing accounts retained.');return
            device=interface(a.ip)
            old=Path('/var/lib/lisp-admin/auth.sqlite3')
            if old.exists():
                db=sqlite3.connect(old);row=db.execute('SELECT salt,digest,must_change FROM account WHERE id=1').fetchone();db.close()
                if not row:raise SystemExit('Existing administrator credentials missing.')
                c.execute("INSERT INTO users(name,salt,digest,role,ip,mac,enabled,must_change,created) VALUES(?,?,?,'admin',?,?,1,?,?)",(a.name,row[0],row[1],device['ip'],device['mac'],row[2],time.time()))
            else:auth.create(a.name,getpass.getpass('Initial administrator password (12+ characters): '),device,'admin',True,c)
        print('Administrator account created and bound; existing network password retained when available.')
    else:
        with auth.db() as c:
            row=c.execute('SELECT * FROM users WHERE name=?',(a.name,)).fetchone()
            if not row:raise SystemExit('Account not found.')
            if a.action=='bind':
                device=interface(a.ip);c.execute('UPDATE users SET ip=?,mac=? WHERE id=?',(device['ip'],device['mac'],row['id']))
            else:
                secret=getpass.getpass('New temporary password (12+ characters): ');auth.password(secret)
                import secrets
                salt=secrets.token_hex(16);c.execute('UPDATE users SET salt=?,digest=?,must_change=1 WHERE id=?',(salt,auth.digest(secret,salt),row['id']))
            c.execute('DELETE FROM sessions WHERE user_id=?',(row['id'],));c.execute('DELETE FROM irc_tickets WHERE user_id=?',(row['id'],));auth.audit(c,0,'recovery-'+a.action,row['id'])
        print('Account updated; existing sessions revoked.')
    import pwd
    uid=pwd.getpwnam('lanadmin').pw_uid;gid=pwd.getpwnam('lanserver').pw_gid
    for item in [auth.folder,*auth.folder.iterdir()]:os.chown(item,uid,gid)
if __name__=='__main__':main()
