#!/usr/bin/python3
"""Repair SMF's read-only asset setting and PostgreSQL empty-row handling.

Run as root on the LAN host. Keeps accounts, permissions, posts and uploads.
Backups remain private on that host. Safe to rerun after a deployment.
"""
import json, os, pathlib, shutil, subprocess, time
P=pathlib.Path
ROOT=P('/opt/lisp-forum')
PATCHES={
 'Session.php': ("list ($sess_data) = $smcFunc['db_fetch_row']($result);", "list ($sess_data) = $smcFunc['db_fetch_row']($result) ?: array(null);"),
 'Load.php': ("list ($visitTime) = $smcFunc['db_fetch_row']($result);", "list ($visitTime) = $smcFunc['db_fetch_row']($result) ?: array(null);"),
 'Profile-Modify.php': ("'sig' . $memberContext[$context['id_member']]", "'sig' . (int) $context['id_member']"),
}
def pg(sql):
 return subprocess.check_output(['runuser','-u','postgres','--','psql','-X','-v','ON_ERROR_STOP=1','-h','/run/lisp-postgres','-p','5433','-d','lisp_forum','-Atc',sql],text=True).strip()
def main():
 assert os.geteuid()==0,'Run as root'
 # Avatar images are served by authenticated Nginx requests. Only this image
 # directory needs traversal; private attachments and configuration stay private.
 (ROOT/'custom_avatar').chmod(0o755)
 edits=[]
 for name,(old,new) in PATCHES.items():
  p=ROOT/'Sources'/name;s=p.read_text()
  if new in s:continue
  assert s.count(old)==1,'Unexpected upstream source: '+name
  edits.append((p,s.replace(old,new)))
 before=json.loads(pg("SELECT coalesce(json_object_agg(variable,value),'{}'::json) FROM smf_settings WHERE variable IN ('minimize_files','attachmentUploadDir','currentAttachmentUploadDir');"))
 raw=before.get('attachmentUploadDir','')
 try:dirs=json.loads(raw)
 except json.JSONDecodeError:dirs={'1':raw}
 if isinstance(dirs,list):dirs={str(i):v for i,v in enumerate(dirs)}
 assert isinstance(dirs,dict) and dirs,'Invalid attachment directories; needs inspection'
 current=before.get('currentAttachmentUploadDir','1')
 assert current in dirs,'Current attachment directory is missing'
 for path in dirs.values():
  p=P(path)
  assert p.is_dir() and p.resolve().is_relative_to(ROOT/'attachments'),'Unexpected upload directory: '+str(p)
  subprocess.run(['runuser','-u','lanforum','--','test','-w',str(p)],check=True)
 backup=P('/srv/lan-party/community-setup/backup')/('forum-repair-'+time.strftime('%Y%m%d-%H%M%S'))
 backup.mkdir(parents=True,mode=0o700);backup.chmod(0o700)
 (backup/'asset-settings.json').write_text(json.dumps(before));(backup/'asset-settings.json').chmod(0o600)
 for p,s in edits:
  shutil.copy2(p,backup/p.name)
  temporary=p.with_suffix('.lisp-repair.tmp');temporary.write_text(s)
  subprocess.run(['php','-c','/etc/lisp/community/forum-php.ini','-l',str(temporary)],check=True)
  st=p.stat();os.chown(temporary,st.st_uid,st.st_gid);temporary.chmod(st.st_mode & 0o777);temporary.replace(p)
 encoded=json.dumps(dirs,separators=(',',':')).replace("'","''")
 pg("BEGIN; INSERT INTO smf_settings(variable,value) VALUES('minimize_files','0'),('attachmentUploadDir','"+encoded+"') ON CONFLICT(variable) DO UPDATE SET value=excluded.value; COMMIT;")
 print(json.dumps({'minimizeFiles':False,'attachmentDirectories':dirs,'emptyRowGuards':list(PATCHES),'privateBackup':str(backup)}))
if __name__=='__main__':main()
