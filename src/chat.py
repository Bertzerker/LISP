"""Persistent account-bound browser and IRC chat with fixed local rooms."""
import ipaddress,os,re,secrets,socketserver,sqlite3,threading,time
from contextlib import contextmanager
from pathlib import Path
from account_client import call
STATE=Path(os.environ.get('LISP_CHAT_DIR','/srv/lan-party/chat'))
NICK=re.compile(r'^[A-Za-z][A-Za-z0-9_-]{1,19}$')
ROOMS={'general':'General','shooter':'Shooter','strategy':'Strategy'}
MESSAGE_TTL=2*60*60
def room_id(room):
    if not isinstance(room,str) or room.casefold() not in ROOMS:raise ValueError('Choose General, Shooter or Strategy.')
    return room.casefold()
def irc_room(channel):
    if channel.casefold()=='#lan':return 'general'
    if not channel.startswith('#'):raise ValueError('Use #general, #shooter or #strategy.')
    return room_id(channel[1:])
class Chat:
    def __init__(self,path=STATE):
        self.path=Path(path);self.path.mkdir(parents=True,exist_ok=True);self.lock=threading.RLock();self.peers=set();self.rate={}
        with self.db() as c:
            c.executescript('CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,nick TEXT COLLATE NOCASE UNIQUE,seen REAL);CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY AUTOINCREMENT,nick TEXT,text TEXT,at REAL);')
            if 'room' not in {r[1] for r in c.execute('PRAGMA table_info(messages)')}:
                c.execute("ALTER TABLE messages ADD COLUMN room TEXT NOT NULL DEFAULT 'general'")
            c.executescript('CREATE INDEX IF NOT EXISTS messages_room_id ON messages(room,id);CREATE TABLE IF NOT EXISTS presence(token TEXT,room TEXT,source TEXT,seen REAL,PRIMARY KEY(token,room,source));')
        (self.path/'chat.sqlite3').chmod(0o600)
        self.expire()
    def expire(self,now=None):
        with self.lock,self.db() as c:
            c.execute('DELETE FROM messages WHERE at<=?',((time.time() if now is None else now)-MESSAGE_TTL,))
    @contextmanager
    def db(self):
        connection=sqlite3.connect(self.path/'chat.sqlite3',timeout=10)
        try:
            with connection:yield connection
        finally:connection.close()
    def join(self,nick):
        if not isinstance(nick,str) or not NICK.fullmatch(nick):raise ValueError('Use 2–20 letters, digits, _ or -, starting with a letter.')
        if nick.casefold() in ('server','lisp','system'):raise ValueError('That name is reserved.')
        with self.lock,self.db() as c:
            c.execute('DELETE FROM sessions WHERE seen<?',(time.time()-180,))
            if c.execute('SELECT count(*) FROM sessions').fetchone()[0]>=64:raise ValueError('Chat is full. Try again later.')
            token=secrets.token_urlsafe(32)
            try:c.execute('INSERT INTO sessions VALUES(?,?,?)',(token,nick,time.time()))
            except sqlite3.IntegrityError:raise ValueError('That nickname is already in use.')
        return token,nick
    def identity(self,token):
        with self.lock,self.db() as c:
            row=c.execute('SELECT nick,seen FROM sessions WHERE token=?',(token,)).fetchone()
            if not row or row[1]<time.time()-180:raise PermissionError('Join chat first.')
            c.execute('UPDATE sessions SET seen=? WHERE token=?',(time.time(),token))
            return row[0]
    def account(self,user):
        token='account-'+str(user['id'])
        with self.lock,self.db() as c:
            c.execute('DELETE FROM sessions WHERE nick=? AND token<>?',(user['name'],token))
            c.execute('INSERT OR REPLACE INTO sessions VALUES(?,?,?)',(token,user['name'],time.time()))
        return token
    def enter(self,token,room='general',source='browser'):
        room=room_id(room);nick=self.identity(token);now=time.time()
        with self.lock,self.db() as c:
            c.execute('DELETE FROM presence WHERE seen<? OR token NOT IN (SELECT token FROM sessions)',(now-180,))
            if source=='browser':c.execute('DELETE FROM presence WHERE token=? AND source=? AND room<>?',(token,source,room))
            c.execute('INSERT OR REPLACE INTO presence VALUES(?,?,?,?)',(token,room,source,now))
        return nick
    def part(self,token,room='general',source='browser'):
        room=room_id(room)
        with self.lock,self.db() as c:c.execute('DELETE FROM presence WHERE token=? AND room=? AND source=?',(token,room,source))
    def leave(self,token,source=None):
        with self.lock,self.db() as c:
            if source is None:
                c.execute('DELETE FROM sessions WHERE token=?',(token,));c.execute('DELETE FROM presence WHERE token=?',(token,))
            else:c.execute('DELETE FROM presence WHERE token=? AND source=?',(token,source))
    def read(self,token,since=0,room='general',source='browser'):
        room=room_id(room);nick=self.enter(token,room,source)
        self.expire()
        with self.db() as c:
            rows=c.execute('SELECT id,nick,text,at FROM messages WHERE room=? AND id>? ORDER BY id DESC LIMIT 100',(room,since)).fetchall()
            online=[r[0] for r in c.execute('SELECT DISTINCT s.nick FROM sessions s JOIN presence p ON p.token=s.token WHERE p.room=? AND p.seen>? AND s.seen>? ORDER BY s.nick',(room,time.time()-180,time.time()-180))]
        return {'nick':nick,'room':room,'rooms':[{'id':k,'name':v} for k,v in ROOMS.items()],'messages':[dict(id=r[0],nick=r[1],text=r[2],at=r[3],room=room) for r in reversed(rows)],'online':online,'messageTtl':MESSAGE_TTL,'serverTime':time.time()}
    def send(self,token,text,room='general',source='browser'):
        room=room_id(room);nick=self.enter(token,room,source)
        if not isinstance(text,str) or not text.strip() or len(text)>500 or any(ord(x)<32 for x in text):raise ValueError('Write 1–500 characters on one line.')
        text=text.strip();now=time.time()
        with self.lock,self.db() as c:
            previous=self.rate.get(token,0)
            if now-previous<.8:raise ValueError('Please wait a moment between messages.')
            self.rate[token]=now
            if len(self.rate)>256:self.rate={k:v for k,v in self.rate.items() if now-v<60}
            ident=c.execute('INSERT INTO messages(nick,text,at,room) VALUES(?,?,?,?)',(nick,text,now,room)).lastrowid
            c.execute('DELETE FROM messages WHERE at<=? OR (room=? AND id NOT IN (SELECT id FROM messages WHERE room=? ORDER BY id DESC LIMIT 1000))',(now-MESSAGE_TTL,room,room))
            peers=list(self.peers)
        for peer in peers:peer.deliver(nick,text,room)
        return {'sent':ident,'room':room}
class IRC(socketserver.StreamRequestHandler):
    def setup(self):
        super().setup();self.request.settimeout(170);self.token=None;self.account_token=None;self.code=None;self.pending_nick=None;self.nick='*';self.ready=False;self.rooms={};self.source='irc-'+secrets.token_hex(16);self.outlock=threading.Lock()
    def account_check(self):
        return call({'op':'session','token':self.account_token or '', 'ip':self.client_address[0]})
    def line(self,text):
        try:
            with self.outlock:self.wfile.write((text+'\r\n').encode());self.wfile.flush()
        except OSError:pass
    def deliver(self,nick,text,room='general'):
        channel=self.rooms.get(room)
        if channel and nick.casefold()!=self.nick.casefold():
            try:self.account_check()
            except PermissionError:
                self.rooms.clear()
                try:self.request.shutdown(2)
                except OSError:pass
                return
            self.line(f':{nick}!lan@lisp PRIVMSG {channel} :{text}')
    def handle(self):
        chat=self.server.chat
        try:
            address=ipaddress.ip_address(self.client_address[0])
            networks=[ipaddress.ip_network(x) for x in os.environ.get('LISP_IRC_NETWORKS','127.0.0.0/8,192.168.8.0/24,10.42.0.0/24').split(',')]
            if not any(address in n for n in networks):return
            self.line(':lisp NOTICE * :Use your account name and a one-time IRC code from Home as server password. Rooms: #general, #shooter, #strategy.')
            while True:
                raw=self.rfile.readline(1025)
                if not raw or len(raw)>1024:break
                text=raw.decode('utf8','replace').strip('\r\n');head,_,tail=text.partition(' :');pieces=head.split()
                if not pieces:continue
                cmd=pieces[0].upper();args=pieces[1:]
                if self.account_token:self.account_check()
                if cmd=='PASS':self.code=tail or (args[0] if args else '')
                elif cmd=='NICK' and args:
                    if self.token:self.line(f':lisp 462 {self.nick} :Account names cannot be changed');continue
                    self.pending_nick=args[0]
                elif cmd=='USER':self.ready=True
                elif cmd=='PONG':
                    if self.token:chat.identity(self.token)
                elif cmd=='PING':
                    if self.token:chat.identity(self.token)
                    self.line(':lisp PONG lisp :'+(tail or (args[0] if args else 'lan')))
                elif cmd=='CAP':self.line(':lisp CAP * LS :')
                elif cmd=='QUIT':break
                elif cmd=='JOIN' and self.token and args:
                    for channel in args[0].split(','):
                        try:room=irc_room(channel)
                        except ValueError:self.line(f':lisp 403 {self.nick} {channel} :Use #general, #shooter or #strategy');continue
                        channel=channel.casefold();self.rooms[room]=channel
                        with chat.lock:chat.peers.add(self)
                        self.line(f':{self.nick}!lan@lisp JOIN {channel}');self.line(f':lisp 332 {self.nick} {channel} :{ROOMS[room]} LAN Party chat')
                        self.line(f':lisp 353 {self.nick} = {channel} :'+ ' '.join(chat.read(self.token,room=room,source=self.source)['online']));self.line(f':lisp 366 {self.nick} {channel} :End of names')
                elif cmd=='PRIVMSG' and self.token and args:
                    try:
                        room=irc_room(args[0])
                        if room not in self.rooms:self.line(f':lisp 442 {self.nick} {args[0]} :Join this room first');continue
                        chat.send(self.token,tail,room,self.source)
                    except ValueError as e:self.line(f':lisp NOTICE {self.nick} :{e}')
                elif cmd=='PART' and self.token and args:
                    for channel in args[0].split(','):
                        try:room=irc_room(channel)
                        except ValueError:continue
                        previous=self.rooms.pop(room,None)
                        if previous:self.line(f':{self.nick}!lan@lisp PART {previous}');chat.part(self.token,room,self.source)
                    if not self.rooms:
                        with chat.lock:chat.peers.discard(self)
                if self.ready and self.pending_nick and not self.account_token:
                    try:
                        user=call({'op':'irc-login','name':self.pending_nick,'code':self.code or '', 'ip':self.client_address[0]})
                        self.account_token=user['token'];self.nick=user['name'];self.token=chat.account(user);self.code=None
                    except PermissionError as e:self.line(':lisp 464 * :'+str(e));break
                if self.ready and self.token:self.line(f':lisp 001 {self.nick} :Welcome to LISP, {self.nick}');self.ready=False
                if self.token:
                    for room in self.rooms:chat.enter(self.token,room,self.source)
        except (OSError,PermissionError):pass
        finally:
            with chat.lock:chat.peers.discard(self)
            if self.token:chat.leave(self.token,self.source)
class IRCServer(socketserver.ThreadingTCPServer):
    allow_reuse_address=True;daemon_threads=True

def start_irc(chat):
    server=IRCServer(('0.0.0.0',6667),IRC);server.chat=chat
    def ping():
        while True:
            time.sleep(45)
            with chat.lock:peers=list(chat.peers)
            for peer in peers:peer.line('PING :lisp')
    threading.Thread(target=ping,daemon=True).start()
    threading.Thread(target=server.serve_forever,daemon=True).start();return server
