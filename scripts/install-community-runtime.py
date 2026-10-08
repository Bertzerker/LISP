#!/usr/bin/python3
"""Install official pinned app sources, private credentials and local runtimes.

Root installs services; application processes/builds run under their own users.
No game engine, player match or firewall is touched. Re-running retains databases.
The portal/SSO cutover is performed only after migration and validation.
"""
import json,os,pathlib,re,secrets,subprocess,time
P=pathlib.Path
BRACKET_REV='04d914157565683cda47e481c56c83b4b3051475'
SMF_REV='d49255b955cbeeb3a702d77009c85aae517ed1e4'
def run(args,**kw):subprocess.run(args,check=True,**kw)
def user(name,args,**kw):run(['runuser','-u',name,'--',*args],**kw)
def put(path,text,mode=0o640,owner=None,group=None):
 p=P(path);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf8');p.chmod(mode)
 if owner or group:
  import pwd,grp
  os.chown(p,pwd.getpwnam(owner).pw_uid if owner else 0,grp.getgrnam(group).gr_gid if group else 0)
def directory(path,owner,group,mode=0o750):
 run(['install','-d','-o',owner,'-g',group,'-m',oct(mode)[2:],path])
def clone(url,rev,path):
 if not P(path).exists():run(['git','clone','--depth','1',url,path])
 if subprocess.check_output(['git','-C',path,'rev-parse','HEAD'],text=True).strip()!=rev:
  run(['git','-C',path,'fetch','--depth','1','origin',rev]);run(['git','-C',path,'checkout','--detach',rev])
def pg(sql,db='postgres'):
 user('postgres',['psql','-X','-v','ON_ERROR_STOP=1','-h','/run/lisp-postgres','-p','5433','-d',db],input=sql,text=True,stdout=subprocess.DEVNULL)
def main():
 assert os.geteuid()==0,'Run as root.'
 source=P(__file__).resolve().parents[1];host=os.getenv('LAN_HOST','192.168.8.138')
 assert re.fullmatch(r'[A-Za-z0-9.-]+',host)
 run(['groupadd','-f','lispcommunity'])
 for name,home in [('lancommunity','/var/lib/lisp-community'),('lanforum','/var/lib/lisp-forum'),('lanbracket','/var/lib/lisp-bracket')]:
  import pwd
  try:pwd.getpwnam(name)
  except KeyError:run(['useradd','--system','--home-dir',home,'--shell','/usr/bin/nologin','--gid','lispcommunity','--groups','lanserver',name])
  directory(home,name,'lispcommunity',0o700)
 directory('/etc/lisp/community','root','lispcommunity')
 private=P('/etc/lisp/community/settings.json')
 if private.exists():cfg=json.loads(private.read_text())
 else:
  cfg={'host':host,'bracketPassword':secrets.token_hex(32),'forumPassword':secrets.token_hex(32),'jwtSecret':secrets.token_hex(32),'adminPassword':secrets.token_hex(32),'forumSecret':secrets.token_hex(32),'smfSecret':secrets.token_hex(32)}
  put(str(private),json.dumps(cfg),group='lispcommunity')
 for name in ['lisp-community-postgres','lisp-bracket','lisp-forum','lisp-community']:
  run(['install','-m','644',str(source/'config'/(name+'.service')),'/etc/systemd/system/'])
 if not P('/var/lib/lisp-postgres/PG_VERSION').exists():
  directory('/var/lib/lisp-postgres','postgres','postgres',0o700)
  user('postgres',['initdb','-D','/var/lib/lisp-postgres','--auth-local=peer','--auth-host=scram-sha-256','--encoding=UTF8','--locale=C.UTF-8'],stdout=subprocess.DEVNULL)
  with P('/var/lib/lisp-postgres/postgresql.conf').open('a') as f:f.write("\nlisten_addresses='127.0.0.1'\nport=5433\nunix_socket_directories='/run/lisp-postgres'\nshared_buffers='64MB'\nmax_connections=25\nlog_statement='none'\n")
 run(['systemctl','daemon-reload']);run(['systemctl','enable','--now','lisp-community-postgres'])
 for _ in range(20):
  if subprocess.run(['pg_isready','-h','127.0.0.1','-p','5433'],stdout=subprocess.DEVNULL).returncode==0:break
  time.sleep(.5)
 for name,key in [('bracket','bracketPassword'),('forum','forumPassword')]:
  role='lisp_'+name;db='lisp_'+name
  pg("DO $$ BEGIN IF NOT EXISTS(SELECT FROM pg_roles WHERE rolname='"+role+"') THEN CREATE ROLE "+role+" LOGIN PASSWORD '"+cfg[key]+"'; END IF; END $$;")
  exists=subprocess.check_output(['runuser','-u','postgres','--','psql','-X','-h','/run/lisp-postgres','-p','5433','-Atc',"SELECT count(*) FROM pg_database WHERE datname='"+db+"'"],text=True).strip()
  if exists=='0':pg('CREATE DATABASE '+db+' OWNER '+role+';')
 clone('https://github.com/evroon/bracket.git',BRACKET_REV,'/opt/lisp-bracket')
 run(['chown','-R','lanbracket:lispcommunity','/opt/lisp-bracket'])
 user('lanbracket',['env','UV_CACHE_DIR=/var/lib/lisp-bracket/cache','UV_PYTHON_INSTALL_DIR=/var/lib/lisp-bracket/python','uv','sync','--locked','--no-dev','--python','3.12'],cwd='/opt/lisp-bracket/backend')
 directory('/opt/lisp-bracket/backend/static','lanbracket','lispcommunity')
 put('/etc/lisp/community/bracket.env','\n'.join(['ENVIRONMENT=PRODUCTION','PG_DSN=postgresql://lisp_bracket:'+cfg['bracketPassword']+'@127.0.0.1:5433/lisp_bracket','JWT_SECRET='+cfg['jwtSecret'],'ADMIN_EMAIL=organizer@lan.invalid','ADMIN_PASSWORD='+cfg['adminPassword'],'ALLOW_USER_REGISTRATION=false','ALLOW_DEMO_USER_REGISTRATION=false','ALLOW_INSECURE_HTTP_SSO=false','CORS_ORIGINS=https://'+host,'BASE_URL=https://'+host+'/bracket-api','SERVE_FRONTEND=false'])+'\n',group='lispcommunity')
 clone('https://github.com/SimpleMachines/SMF.git',SMF_REV,'/opt/lisp-forum')
 phpini=P('/etc/php/php.ini').read_text()
 for ext in ['pgsql','pdo_pgsql','gd','iconv']:
  phpini=re.sub(r'^;extension='+ext+r'$', 'extension='+ext,phpini,flags=re.M)
 phpini+='\ndisplay_errors=Off\nlog_errors=On\nerror_log=/var/lib/lisp-forum/php-errors.log\nsession.save_path=/var/lib/lisp-forum/sessions\nsession.cookie_secure=1\nsession.cookie_httponly=1\nsession.cookie_samesite=Strict\nupload_max_filesize=8M\npost_max_size=10M\nmemory_limit=96M\n'
 put('/etc/lisp/community/forum-php.ini',phpini,group='lispcommunity')
 nginxuser=subprocess.check_output(['ps','-C','nginx','-o','user='],text=True).split()
 nginxuser=next((u for u in nginxuser if u!='root'),'http')
 put('/etc/lisp/community/forum-fpm.conf',f'''[global]
error_log=/var/lib/lisp-forum/fpm-errors.log
[forum]
user=lanforum
group=lispcommunity
listen=/run/lisp-forum/php.sock
listen.owner={nginxuser}
listen.group={nginxuser}
listen.mode=0600
pm=ondemand
pm.max_children=4
pm.process_idle_timeout=30s
pm.max_requests=300
clear_env=yes
security.limit_extensions=.php
''',group='lispcommunity')
 for d in ['cache','attachments','custom_avatar']:
  directory('/opt/lisp-forum/'+d,'lanforum','lispcommunity')
 directory('/var/lib/lisp-forum/sessions','lanforum','lispcommunity',0o700)
 settings=P('/opt/lisp-forum/Settings.php')
 if not settings.exists():
  values={'maintenance':0,'mtitle':'Maintenance','mmessage':'Forum update in progress','mbname':'LISP LAN Forum','language':'english','boardurl':'https://'+host+'/forum','webmaster_email':'admin@lan.invalid','cookiename':'LISP_SMF','db_type':'postgresql','db_server':'127.0.0.1','db_port':5433,'db_name':'lisp_forum','db_user':'lisp_forum','db_passwd':cfg['forumPassword'],'db_prefix':'smf_','db_persist':False,'db_error_send':0,'db_character_set':'utf8','boarddir':'/opt/lisp-forum','sourcedir':'/opt/lisp-forum/Sources','cachedir':'/opt/lisp-forum/cache','packagesdir':'/opt/lisp-forum/Packages','auth_secret':cfg['smfSecret']}
  # JSON strings are valid PHP double-quoted literals after escaping $.
  put(str(settings),'<?php\n'+''.join('$'+k+' = '+json.dumps(v).replace('$','\\$')+';\n' for k,v in values.items()),0o600,'lanforum','lispcommunity')
  put('/opt/lisp-forum/Settings_bak.php',settings.read_text(),0o600,'lanforum','lispcommunity')
 count=subprocess.check_output(['runuser','-u','postgres','--','psql','-X','-h','/run/lisp-postgres','-p','5433','-d','lisp_forum','-Atc',"SELECT count(*) FROM information_schema.tables WHERE table_name='smf_members'"],text=True).strip()
 if count=='0':
  sql=P('/opt/lisp-forum/other/install_2-1_postgresql.sql').read_text()
  values={'db_prefix':'smf_','boarddir':'/opt/lisp-forum','boardurl':'https://'+host+'/forum','attachdir':'/opt/lisp-forum/attachments','smf_version':'2.1.7','current_time':str(int(time.time())),'databaseSession_enable':'1','registration_method':'3','enableCompressedOutput':'0','sched_task_offset':'0','default_time_format':'%Y-%m-%d %H:%M','default_board_name':'General','default_category_name':'LAN Party','default_topic_subject':'Welcome','default_topic_message':'Welcome to the LISP LAN forum.','default_theme_name':'Curve2'}
  sql=re.sub(r'\{\$(\w+)\}',lambda m:str(values.get(m[1],m[1].removeprefix('default_').replace('_',' ').title())).replace("'","''"),sql)
  sql='\n'.join(line for line in sql.splitlines() if not line.lstrip().startswith('#'))
  # Schema functions belong to the forum owner, not the database superuser.
  pg('SET ROLE lisp_forum;\n'+sql,'lisp_forum')
  pg("SET ROLE lisp_forum; UPDATE smf_settings SET value='3' WHERE variable='registration_method'; UPDATE smf_settings SET value='0' WHERE variable IN ('send_welcomeEmail','mail_queue','enableCompressedOutput');",'lisp_forum')
 run(['python3',str(source/'scripts/repair-forum-runtime.py')])
 for service in ['lisp-bracket','lisp-forum']:
  run(['systemctl','enable','--now',service])
 print('Official pinned community runtimes installed; local bindings only. Portal unchanged.')
if __name__=='__main__':main()
