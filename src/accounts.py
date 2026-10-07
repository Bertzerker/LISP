"""Local accounts, IP/MAC-bound sessions and a persistent plain-text forum."""
import hashlib,hmac,ipaddress,json,os,re,secrets,sqlite3,subprocess,threading,time
from contextlib import contextmanager
from pathlib import Path

NAME=re.compile(r'^[A-Za-z][A-Za-z0-9_-]{1,19}$')
MAC=re.compile(r'^[0-9a-f]{2}(:[0-9a-f]{2}){5}$')
BOARDS=('General','Games','Servers','Tools','Emulators')

def interfaces():
    rows=json.loads(subprocess.check_output(['ip','-j','neigh','show'],timeout=3))
    result=[];seen=set()
    for row in rows:
        try:ip=ipaddress.IPv4Address(row['dst']);mac=row.get('lladdr','').lower()
        except (ValueError,KeyError):continue
        nets=[ipaddress.ip_network(x) for x in os.environ.get('LISP_ACCOUNT_NETWORKS','192.168.8.0/24,10.42.0.0/24').split(',')]
        if not any(ip in net for net in nets) or not MAC.fullmatch(mac) or int(mac[:2],16)&1:continue
        if not set(row.get('state',[]))&{'REACHABLE','STALE','DELAY','PROBE','PERMANENT'}:continue
        # One player can appear on both server interfaces on the same LAN.
        # Keep both observations so interface() can select the routed device.
        key=(str(ip),mac,row['dev'])
        if key not in seen:result.append({'ip':str(ip),'mac':mac,'interface':row['dev']});seen.add(key)
    return result

def interface(address):
    try:ip=str(ipaddress.IPv4Address(address))
    except (ValueError,TypeError):raise PermissionError('Connect directly to the party LAN.')
    route=json.loads(subprocess.check_output(['ip','-j','route','get',ip],timeout=3))[0]
    if route.get('gateway') or route.get('type')=='local':raise PermissionError('Connect directly to the party LAN; a routed connection cannot identify your interface.')
    rows=[row for row in interfaces() if row['ip']==ip and row['interface']==route.get('dev')]
    if len(rows)!=1:raise PermissionError('Your interface is not visible yet. Reconnect to the LAN and try again.')
    return rows[0]

class Accounts:
    def __init__(self,folder,lookup=interface):
        self.folder=Path(folder);self.folder.mkdir(parents=True,exist_ok=True);self.folder.chmod(0o700)
        self.lookup=lookup;self.lock=threading.RLock();self.attempts={};self.post_times={}
        with self.db() as c:
            c.executescript('''
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,name TEXT COLLATE NOCASE UNIQUE,salt TEXT,digest TEXT,role TEXT CHECK(role IN ('admin','player')),ip TEXT,mac TEXT,enabled INTEGER,must_change INTEGER,created REAL);
CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user_id INTEGER REFERENCES users(id),csrf TEXT,expires REAL,ip TEXT,mac TEXT);
CREATE TABLE IF NOT EXISTS boards(id INTEGER PRIMARY KEY,name TEXT UNIQUE);
CREATE TABLE IF NOT EXISTS topics(id INTEGER PRIMARY KEY,board INTEGER REFERENCES boards(id),title TEXT,user_id INTEGER REFERENCES users(id),created REAL,locked INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS posts(id INTEGER PRIMARY KEY,topic INTEGER REFERENCES topics(id),user_id INTEGER REFERENCES users(id),body TEXT,created REAL);
CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,actor INTEGER,action TEXT,target INTEGER,created REAL);
CREATE TABLE IF NOT EXISTS irc_tickets(token TEXT PRIMARY KEY,user_id INTEGER,expires REAL,ip TEXT,mac TEXT);
''')
            for i,name in enumerate(BOARDS,1):c.execute('INSERT OR IGNORE INTO boards VALUES(?,?)',(i,name))
        (self.folder/'accounts.sqlite3').chmod(0o600)
    @contextmanager
    def db(self):
        c=sqlite3.connect(self.folder/'accounts.sqlite3',timeout=10);c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON')
        try:
            with c:yield c
        finally:c.close()
    @staticmethod
    def digest(password,salt):return hashlib.scrypt(password.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1).hex()
    @staticmethod
    def password(value):
        if not isinstance(value,str) or not 12<=len(value)<=128 or '\0' in value:raise ValueError('Use a password of 12–128 characters.')
        return value
    @staticmethod
    def name(value):
        if not isinstance(value,str) or not NAME.fullmatch(value) or value.casefold() in ('server','system','lisp'):raise ValueError('Names use 2–20 letters, digits, _ or -, starting with a letter.')
        return value
    def throttle(self,ip):
        now=time.time();self.attempts={k:v for k,v in self.attempts.items() if v and now-v[-1]<300}
        recent=[t for t in self.attempts.get(ip,[]) if now-t<300]
        if len(recent)>=5:raise PermissionError('Too many attempts. Wait five minutes.')
        self.attempts[ip]=recent+[now]
    def audit(self,c,actor,action,target):
        c.execute('INSERT INTO audit(actor,action,target,created) VALUES(?,?,?,?)',(actor,action,target,time.time()))
        c.execute('DELETE FROM audit WHERE id < (SELECT max(id)-2000 FROM audit)')
    def create(self,name,password,device,role='player',must=False,c=None):
        name=self.name(name);password=self.password(password)
        salt=secrets.token_hex(16)
        if role not in ('admin','player'):raise ValueError('Choose player or admin.')
        def insert(db):
            if db.execute('SELECT count(*) FROM users').fetchone()[0]>=500:raise ValueError('Account limit reached. Ask an administrator.')
            try:return db.execute('INSERT INTO users(name,salt,digest,role,ip,mac,enabled,must_change,created) VALUES(?,?,?,?,?,?,1,?,?)',(name,salt,self.digest(password,salt),role,device['ip'],device['mac'],int(must),time.time())).lastrowid
            except sqlite3.IntegrityError:raise ValueError('That account name is already used.')
        if c is not None:return insert(c)
        with self.lock,self.db() as db:return insert(db)
    def register(self,name,password,ip):
        with self.lock:
            self.throttle(ip);device=self.lookup(ip)
            if str(name).casefold()=='admin':raise ValueError('That account name is reserved.')
            self.create(name,password,device)
            return self.login(name,password,ip)
    def login(self,name,password,ip):
        with self.lock,self.db() as c:
            self.throttle(ip);device=self.lookup(ip)
            row=c.execute('SELECT * FROM users WHERE name=?',(str(name),)).fetchone()
            # Perform the same expensive transform for an unknown account.
            salt=row['salt'] if row else '0'*32
            good=isinstance(password,str) and len(password)<=128 and hmac.compare_digest(self.digest(password,salt),row['digest'] if row else '0'*128)
            if not row or not good or not row['enabled']:raise PermissionError('Incorrect account name or password.')
            if (row['ip'],row['mac'])!=(device['ip'],device['mac']):raise PermissionError('Your network interface changed. Ask an admin to bind this interface to your account.')
            self.attempts.pop(ip,None)
            return self.new_session(c,row,device)
    def new_session(self,c,user,device):
        now=time.time();c.execute('DELETE FROM sessions WHERE expires<?',(now,))
        if c.execute('SELECT count(*) FROM sessions').fetchone()[0]>=1000:raise ValueError('Session limit reached. Try again later.')
        token=secrets.token_urlsafe(32);csrf=secrets.token_urlsafe(32)
        c.execute('INSERT INTO sessions VALUES(?,?,?,?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),user['id'],csrf,now+8*3600,device['ip'],device['mac']))
        return token,self.public(user,csrf)
    def public(self,user,csrf):return {'authenticated':True,'id':user['id'],'name':user['name'],'role':user['role'],'mustChange':bool(user['must_change']),'ip':user['ip'],'mac':user['mac'],'csrf':csrf}
    def session(self,token,ip,csrf=None,allow_change=False,admin=False):
        device=self.lookup(ip)
        with self.db() as c:
            row=c.execute('SELECT users.*,sessions.csrf,sessions.expires,sessions.ip AS session_ip,sessions.mac AS session_mac FROM sessions JOIN users ON users.id=sessions.user_id WHERE sessions.token=?',(hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
        if not row or not row['enabled'] or row['expires']<time.time():raise PermissionError('Log in to the LAN portal.')
        if (row['ip'],row['mac'])!=(device['ip'],device['mac']) or (row['session_ip'],row['session_mac'])!=(device['ip'],device['mac']):raise PermissionError('Your interface changed. Ask an admin to update your account binding.')
        if csrf is not None and (not isinstance(csrf,str) or not hmac.compare_digest(csrf,row['csrf'])):raise PermissionError('Refresh your login before making changes.')
        if row['must_change'] and not allow_change:raise PermissionError('Change your temporary password on the home page first.')
        if admin and row['role']!='admin':raise PermissionError('Administrator access required.')
        return self.public(row,row['csrf'])
    def logout(self,token):
        with self.db() as c:
            key=hashlib.sha256(token.encode()).hexdigest();row=c.execute('SELECT user_id FROM sessions WHERE token=?',(key,)).fetchone()
            if row:c.execute('DELETE FROM irc_tickets WHERE user_id=?',(row['user_id'],))
            c.execute('DELETE FROM sessions WHERE token=?',(key,))
    def irc_ticket(self,user):
        code=secrets.token_urlsafe(24)
        with self.db() as c:
            c.execute('DELETE FROM irc_tickets WHERE expires<? OR user_id=?',(time.time(),user['id']))
            c.execute('INSERT INTO irc_tickets VALUES(?,?,?,?,?)',(hashlib.sha256(code.encode()).hexdigest(),user['id'],time.time()+120,user['ip'],user['mac']))
        return {'code':code,'expiresIn':120,'name':user['name']}
    def irc_login(self,name,code,ip):
        device=self.lookup(ip)
        with self.lock,self.db() as c:
            key=hashlib.sha256(str(code).encode()).hexdigest()
            row=c.execute('SELECT users.*,irc_tickets.expires,irc_tickets.ip AS ticket_ip,irc_tickets.mac AS ticket_mac FROM irc_tickets JOIN users ON users.id=irc_tickets.user_id WHERE irc_tickets.token=?',(key,)).fetchone()
            if not row or not row['enabled'] or row['must_change'] or row['expires']<time.time() or row['name'].casefold()!=str(name).casefold() or (row['ticket_ip'],row['ticket_mac'])!=(device['ip'],device['mac']) or (row['ip'],row['mac'])!=(device['ip'],device['mac']):raise PermissionError('Create a fresh IRC code on the portal home page.')
            c.execute('DELETE FROM irc_tickets WHERE token=?',(key,))
            return self.new_session(c,row,device)
    def change(self,user,current,new,ip):
        self.password(new)
        if current==new:raise ValueError('Choose a different password.')
        with self.lock,self.db() as c:
            row=c.execute('SELECT * FROM users WHERE id=?',(user['id'],)).fetchone()
            if not isinstance(current,str) or len(current)>128 or not hmac.compare_digest(self.digest(current,row['salt']),row['digest']):raise PermissionError('Current password is incorrect.')
            salt=secrets.token_hex(16);c.execute('UPDATE users SET salt=?,digest=?,must_change=0 WHERE id=?',(salt,self.digest(new,salt),user['id']));c.execute('DELETE FROM sessions WHERE user_id=?',(user['id'],))
            c.execute('DELETE FROM irc_tickets WHERE user_id=?',(user['id'],))
            self.audit(c,user['id'],'password-change',user['id'])
            return self.new_session(c,c.execute('SELECT * FROM users WHERE id=?',(user['id'],)).fetchone(),self.lookup(ip))
    def users(self):
        with self.db() as c:return [dict(row) for row in c.execute('SELECT id,name,role,ip,mac,enabled,must_change FROM users ORDER BY name')]
    def community_users(self):
        # Public profile data only. Never share password hashes or interface bindings.
        with self.db() as c:return [dict(r) for r in c.execute('SELECT id,name,created FROM users WHERE enabled=1 ORDER BY name')]
    def verify_forum_password(self,user,password):
        with self.lock,self.db() as c:
            self.throttle('forum:'+str(user['id']))
            row=c.execute('SELECT salt,digest FROM users WHERE id=?',(user['id'],)).fetchone()
            good=isinstance(password,str) and len(password)<=128 and hmac.compare_digest(self.digest(password,row['salt']),row['digest'])
            if good:self.attempts.pop('forum:'+str(user['id']),None)
            return {'verified':bool(good)}
    def manage(self,actor,data):
        if actor['role']!='admin':raise PermissionError('Administrator access required.')
        op=data.get('op');ident=data.get('id')
        with self.lock,self.db() as c:
            if op=='create':
                ident=self.create(data.get('name'),data.get('password'),self.lookup(data.get('ip')),data.get('role','player'),True,c)
            else:
                if type(ident) is not int:raise ValueError('Choose an account.')
                row=c.execute('SELECT * FROM users WHERE id=?',(ident,)).fetchone()
                if not row:raise ValueError('Account not found.')
                if op=='reset':
                    self.password(data.get('password'));salt=secrets.token_hex(16)
                    c.execute('UPDATE users SET salt=?,digest=?,must_change=1 WHERE id=?',(salt,self.digest(data['password'],salt),ident))
                elif op=='bind':
                    if ident==actor['id']:raise ValueError('Use another administrator or the recovery script to move your own current interface.')
                    device=self.lookup(data.get('ip'));c.execute('UPDATE users SET ip=?,mac=? WHERE id=?',(device['ip'],device['mac'],ident))
                elif op=='enabled':
                    if type(data.get('enabled')) is not bool:raise ValueError('Choose enabled or disabled.')
                    if ident==actor['id'] and not data['enabled']:raise ValueError('You cannot disable your current account.')
                    if not data['enabled'] and row['role']=='admin' and c.execute("SELECT count(*) FROM users WHERE role='admin' AND enabled=1").fetchone()[0]<=1:raise ValueError('Keep at least one enabled administrator.')
                    c.execute('UPDATE users SET enabled=? WHERE id=?',(int(data['enabled']),ident))
                elif op=='role':
                    role=data.get('role')
                    if role not in ('admin','player'):raise ValueError('Choose player or admin.')
                    if ident==actor['id']:raise ValueError('Another administrator must change your role.')
                    if row['role']=='admin' and role=='player' and row['enabled'] and c.execute("SELECT count(*) FROM users WHERE role='admin' AND enabled=1").fetchone()[0]<=1:raise ValueError('Keep at least one enabled administrator.')
                    c.execute('UPDATE users SET role=? WHERE id=?',(role,ident))
                else:raise ValueError('Unsupported account action.')
                c.execute('DELETE FROM sessions WHERE user_id=?',(ident,))
                c.execute('DELETE FROM irc_tickets WHERE user_id=?',(ident,))
            self.audit(c,actor['id'],op,ident)
        return {'updated':True,'id':ident}
    def boards(self):
        with self.db() as c:return [dict(r) for r in c.execute('SELECT id,name FROM boards ORDER BY id')]
    def topics(self,board):
        with self.db() as c:return [dict(r) for r in c.execute('SELECT topics.id,title,users.name AS author,topics.created,locked,(SELECT count(*) FROM posts WHERE topic=topics.id) AS replies FROM topics JOIN users ON users.id=topics.user_id WHERE board=? ORDER BY topics.id DESC LIMIT 100',(board,))]
    def topic(self,ident):
        with self.db() as c:
            row=c.execute('SELECT topics.id,title,board,locked,users.name AS author FROM topics JOIN users ON users.id=topics.user_id WHERE topics.id=?',(ident,)).fetchone()
            if not row:raise ValueError('Topic not found.')
            return {'topic':dict(row),'posts':[dict(r) for r in c.execute('SELECT posts.id,body,posts.created,users.name AS author FROM posts JOIN users ON users.id=posts.user_id WHERE topic=? ORDER BY posts.id LIMIT 500',(ident,))]}
    def post(self,user,data):
        op=data.get('op');now=time.time()
        with self.lock,self.db() as c:
            if op in ('lock','delete'):
                if user['role']!='admin':raise PermissionError('Administrator access required.')
                ident=data.get('topic')
                if type(ident) is not int or not c.execute('SELECT 1 FROM topics WHERE id=?',(ident,)).fetchone():raise ValueError('Topic not found.')
                if op=='lock':
                    if type(data.get('locked')) is not bool:raise ValueError('Choose locked or unlocked.')
                    c.execute('UPDATE topics SET locked=? WHERE id=?',(int(data['locked']),ident))
                else:c.execute('DELETE FROM posts WHERE topic=?',(ident,));c.execute('DELETE FROM topics WHERE id=?',(ident,))
                self.audit(c,user['id'],'forum-'+op,ident);return {'updated':True}
            body=data.get('body')
            if not isinstance(body,str) or not body.strip() or len(body)>8000 or any(ord(x)<32 and x not in '\n\t' for x in body):raise ValueError('Write 1–8000 characters.')
            if now-self.post_times.get(user['id'],0)<2:raise ValueError('Wait a moment between posts.')
            if op=='topic':
                title=data.get('title');board=data.get('board')
                if not isinstance(title,str) or not title.strip() or len(title)>120 or any(ord(x)<32 for x in title):raise ValueError('Use a title of 1–120 characters.')
                if type(board) is not int or not c.execute('SELECT 1 FROM boards WHERE id=?',(board,)).fetchone():raise ValueError('Choose a forum section.')
                if c.execute('SELECT count(*) FROM topics').fetchone()[0]>=10000:raise ValueError('Forum topic limit reached.')
                ident=c.execute('INSERT INTO topics(board,title,user_id,created) VALUES(?,?,?,?)',(board,title.strip(),user['id'],now)).lastrowid
            elif op=='reply':
                ident=data.get('topic')
                if type(ident) is not int:raise ValueError('Choose a topic.')
                row=c.execute('SELECT locked FROM topics WHERE id=?',(ident,)).fetchone()
                if not row:raise ValueError('Topic not found.')
                if row['locked']:raise ValueError('This topic is locked.')
                if c.execute('SELECT count(*) FROM posts WHERE topic=?',(ident,)).fetchone()[0]>=500:raise ValueError('This topic is full; start another one.')
            else:raise ValueError('Unsupported forum action.')
            c.execute('INSERT INTO posts(topic,user_id,body,created) VALUES(?,?,?,?)',(ident,user['id'],body.strip(),now));self.post_times[user['id']]=now
            return {'topic':ident}
