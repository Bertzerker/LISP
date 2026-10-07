"""Single administrator account, forced bootstrap rotation and server-side sessions."""
import hashlib,hmac,json,os,secrets,sqlite3,threading,time
from contextlib import contextmanager
from pathlib import Path
class Auth:
    def __init__(self,folder):
        self.folder=Path(folder);self.folder.mkdir(parents=True,exist_ok=True);self.lock=threading.RLock();self.attempts={}
        with self.db() as c:
            c.executescript('CREATE TABLE IF NOT EXISTS account(id INTEGER PRIMARY KEY,salt TEXT,digest TEXT,must_change INTEGER);CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,csrf TEXT,expires REAL);')
            if not c.execute('SELECT 1 FROM account').fetchone():
                password=secrets.token_urlsafe(18);salt=secrets.token_hex(16)
                c.execute('INSERT INTO account VALUES(1,?,?,1)',(salt,self.digest(password,salt)))
                p=self.folder/'initial-password.txt';p.write_text(password+'\n');p.chmod(0o600)
        (self.folder/'auth.sqlite3').chmod(0o600)
    @contextmanager
    def db(self):
        connection=sqlite3.connect(self.folder/'auth.sqlite3',timeout=10)
        try:
            with connection:yield connection
        finally:connection.close()
    @staticmethod
    def digest(password,salt):return hashlib.scrypt(password.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1).hex()
    def valid(self,password,row):return isinstance(password,str) and len(password)<=128 and hmac.compare_digest(self.digest(password,row[0]),row[1])
    def login(self,password,address):
        now=time.time()
        with self.lock,self.db() as c:
            self.attempts={k:v for k,v in self.attempts.items() if v and now-v[-1]<300}
            attempts=[t for t in self.attempts.get(address,[]) if now-t<300]
            if len(attempts)>=5:raise PermissionError('Too many attempts. Wait five minutes.')
            row=c.execute('SELECT salt,digest,must_change FROM account WHERE id=1').fetchone()
            if not self.valid(password,row):
                self.attempts[address]=attempts+[now];raise PermissionError('Incorrect password.')
            self.attempts.pop(address,None)
            return self.new_session(c,bool(row[2]))
    def new_session(self,c,must_change):
        now=time.time();c.execute('DELETE FROM sessions WHERE expires<?',(now,))
        if c.execute('SELECT count(*) FROM sessions').fetchone()[0]>=128:c.execute('DELETE FROM sessions WHERE token IN (SELECT token FROM sessions ORDER BY expires LIMIT 1)')
        token=secrets.token_urlsafe(32);csrf=secrets.token_urlsafe(32)
        c.execute('INSERT INTO sessions VALUES(?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),csrf,now+8*3600))
        return token,{'authenticated':True,'mustChange':must_change,'csrf':csrf}
    def session(self,token,allow_change=False):
        with self.db() as c:
            row=c.execute('SELECT csrf,expires FROM sessions WHERE token=?',(hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
            if not row or row[1]<time.time():raise PermissionError('Log in to network administration.')
            must=bool(c.execute('SELECT must_change FROM account').fetchone()[0])
        if must and not allow_change:raise PermissionError('Change the initial password before managing the network.')
        return {'authenticated':True,'mustChange':must,'csrf':row[0]}
    def change(self,token,old,new):
        self.session(token,True)
        if not isinstance(new,str) or not 12<=len(new)<=128 or '\x00' in new:raise ValueError('Choose a password of 12–128 characters.')
        if old==new:raise ValueError('Choose a different password.')
        with self.lock,self.db() as c:
            row=c.execute('SELECT salt,digest FROM account').fetchone()
            if not self.valid(old,row):raise PermissionError('Current password is incorrect.')
            salt=secrets.token_hex(16);c.execute('UPDATE account SET salt=?,digest=?,must_change=0',(salt,self.digest(new,salt)))
            c.execute('DELETE FROM sessions');result=self.new_session(c,False)
        (self.folder/'initial-password.txt').unlink(missing_ok=True)
        return result
    def logout(self,token):
        with self.db() as c:c.execute('DELETE FROM sessions WHERE token=?',(hashlib.sha256(token.encode()).hexdigest(),))
