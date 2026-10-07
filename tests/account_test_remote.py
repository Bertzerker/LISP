import os,getpass,pathlib,shlex,tempfile
import paramiko
HOST=os.environ.get('LISP_TEST_HOST','192.168.8.138')
USER=os.environ.get('LISP_TEST_SSH_USER','robert')
PASSWORD=getpass.getpass('SSH password for disposable test-account setup: ')
CA_FILE=pathlib.Path(tempfile.gettempdir())/'lisp-test-lan-ca.crt'
def connect():
 c=paramiko.SSHClient();c.load_system_host_keys();c.set_missing_host_key_policy(paramiko.RejectPolicy())
 c.connect(HOST,username=USER,password=PASSWORD,timeout=15,look_for_keys=False,allow_agent=False)
 return c
def run(c,command,sudo=False):
 if sudo:command='sudo -S -p "" sh -c '+shlex.quote(command)
 i,o,e=c.exec_command(command)
 if sudo:i.write(PASSWORD+'\n');i.flush()
 output=o.read().decode();error=e.read().decode();status=o.channel.recv_exit_status()
 print(output,end='')
 if status:raise RuntimeError('Test administration command failed: '+error)
