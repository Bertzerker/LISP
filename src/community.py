"""LAN community state. Votes, publications and awards are transactional and retryable."""
import base64,hashlib,hmac,json,os,secrets,sqlite3,threading,time
from contextlib import contextmanager
from datetime import datetime,timezone
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError

def admin(user):
    if user.get('role')!='admin':raise PermissionError('Administrator access required.')
def text(value,limit):
    if not isinstance(value,str) or not value.strip() or len(value)>limit or any(ord(c)<32 for c in value):raise ValueError('Enter a valid name.')
    return value.strip()
def stamp(value):return datetime.fromtimestamp(value,timezone.utc).isoformat()
def bb(value):return str(value).replace('&','&amp;').replace('[','&#91;').replace(']','&#93;').replace('<','&lt;').replace('>','&gt;')

class Store:
    def __init__(self,folder,clock=time.time):
        self.path=Path(folder)/'community.sqlite3';self.path.parent.mkdir(parents=True,exist_ok=True);self.clock=clock;self.lock=threading.RLock()
        with self.db() as c:c.executescript('''
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS polls(id INTEGER PRIMARY KEY,name TEXT,deadline REAL,start REAL,status TEXT DEFAULT 'open',winner TEXT,bracket INTEGER,thread INTEGER,created REAL,creator INTEGER,finalized REAL);
CREATE TABLE IF NOT EXISTS options(poll INTEGER REFERENCES polls(id),game TEXT,label TEXT,PRIMARY KEY(poll,game));
CREATE TABLE IF NOT EXISTS votes(poll INTEGER REFERENCES polls(id),user INTEGER,game TEXT,updated REAL,PRIMARY KEY(poll,user),FOREIGN KEY(poll,game) REFERENCES options(poll,game));
CREATE TABLE IF NOT EXISTS participants(poll INTEGER REFERENCES polls(id),user INTEGER,name TEXT,player INTEGER,team INTEGER,PRIMARY KEY(poll,user));
CREATE TABLE IF NOT EXISTS awards(poll INTEGER REFERENCES polls(id),user INTEGER,rank INTEGER,team INTEGER,created REAL,PRIMARY KEY(poll,user));
CREATE TABLE IF NOT EXISTS outbox(id INTEGER PRIMARY KEY,key TEXT UNIQUE,op TEXT,poll INTEGER,payload TEXT,attempts INTEGER DEFAULT 0,next REAL DEFAULT 0);
CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,actor INTEGER,action TEXT,poll INTEGER,created REAL);
''')
        with self.db() as c:
            columns={row[1] for row in c.execute('PRAGMA table_info(polls)')}
            for name,kind in [('cancelled','REAL'),('cancel_reason','TEXT'),('cancel_status','TEXT')]:
                if name not in columns:c.execute(f'ALTER TABLE polls ADD COLUMN {name} {kind}')
        self.path.chmod(0o600)
    @contextmanager
    def db(self):
        c=sqlite3.connect(self.path,timeout=15);c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON')
        try:
            with c:yield c
        finally:c.close()
    def queue(self,c,key,op,poll,payload=None):
        value=dict(payload or {});value['_revision']=secrets.token_hex(8)
        c.execute('INSERT INTO outbox(key,op,poll,payload) VALUES(?,?,?,?) ON CONFLICT(key) DO UPDATE SET payload=excluded.payload,next=0',(key,op,poll,json.dumps(value)))
    def log(self,c,user,action,poll):c.execute('INSERT INTO audit(actor,action,poll,created) VALUES(?,?,?,?)',(user['id'],action,poll,self.clock()))
    def create(self,user,data,games):
        admin(user);name=text(data.get('name'),100);deadline=float(data.get('deadline',0));start=float(data.get('start',0));now=self.clock()
        if not now+30<=deadline<=now+366*86400 or not deadline<=start<=now+730*86400:raise ValueError('Voting must close at least 30 seconds from now, before the tournament starts.')
        ids=data.get('games')
        if not isinstance(ids,list) or not 2<=len(ids)<=20 or len(set(ids))!=len(ids) or any(i not in games for i in ids):raise ValueError('Choose 2–20 available games.')
        with self.lock,self.db() as c:
            if c.execute('SELECT count(*) FROM polls').fetchone()[0]>=1000:raise ValueError('Tournament limit reached.')
            ident=c.execute('INSERT INTO polls(name,deadline,start,created,creator) VALUES(?,?,?,?,?)',(name,deadline,start,now,user['id'])).lastrowid
            c.executemany('INSERT INTO options VALUES(?,?,?)',[(ident,i,games[i]) for i in ids]);self.queue(c,f'summary:{ident}','summary',ident);self.log(c,user,'open-vote',ident)
        return ident
    def poll(self,c,ident):
        row=c.execute('SELECT * FROM polls WHERE id=?',(ident,)).fetchone()
        if not row:raise ValueError('Tournament not found.')
        return dict(row)
    def view(self,user=None,ident=None,include_cancelled=False):
        with self.db() as c:
            rows=[self.poll(c,ident)] if ident else [dict(r) for r in c.execute('SELECT * FROM polls '+('' if include_cancelled else "WHERE status<>'cancelled' ")+'ORDER BY id DESC LIMIT 100')]
            for p in rows:
                p['options']=[dict(r) for r in c.execute('SELECT options.game,label,count(votes.user) AS votes FROM options LEFT JOIN votes USING(poll,game) WHERE poll=? GROUP BY options.game,label ORDER BY votes DESC,label',(p['id'],))]
                p['myVote']=c.execute('SELECT game FROM votes WHERE poll=? AND user=?',(p['id'],user['id'] if user else -1)).fetchone();p['myVote']=p['myVote'][0] if p['myVote'] else None
                p['participants']=[dict(r) for r in c.execute('SELECT user,name,player,team FROM participants WHERE poll=? ORDER BY name',(p['id'],))]
                p['awards']=[dict(r) for r in c.execute('SELECT awards.user,participants.name,rank,awards.team FROM awards JOIN participants USING(poll,user) WHERE poll=? ORDER BY rank,name',(p['id'],))]
            return rows
    def for_bracket(self,ident):
        with self.db() as c:
            row=c.execute('SELECT id FROM polls WHERE bracket=?',(ident,)).fetchone()
            return self.poll(c,row['id']) if row else None
    def vote(self,user,ident,game):
        with self.lock,self.db() as c:
            p=self.poll(c,ident)
            if p['status']!='open' or self.clock()>=p['deadline']:raise ValueError('Voting is closed.')
            if not c.execute('SELECT 1 FROM options WHERE poll=? AND game=?',(ident,game)).fetchone():raise ValueError('Choose a game in this vote.')
            c.execute('INSERT INTO votes VALUES(?,?,?,?) ON CONFLICT(poll,user) DO UPDATE SET game=excluded.game,updated=excluded.updated',(ident,user['id'],game,self.clock()))
            self.queue(c,f'summary:{ident}','summary',ident)
    def close(self,user,ident,winner=None):
        admin(user)
        with self.lock,self.db() as c:self._close(c,ident,user,winner)
    def _close(self,c,ident,user=None,winner=None):
        p=self.poll(c,ident)
        if p['status'] not in ('open','choice'):return
        rows=list(c.execute('SELECT game,count(votes.user) AS n FROM options LEFT JOIN votes USING(poll,game) WHERE poll=? GROUP BY game ORDER BY n DESC',(ident,)))
        top=rows[0]['n'];choices=[r['game'] for r in rows if r['n']==top]
        if winner is not None and winner not in choices:raise ValueError('Choose one of the tied games.')
        chosen=winner or (choices[0] if len(choices)==1 and top>0 else None)
        c.execute('UPDATE polls SET deadline=min(deadline,?),status=?,winner=? WHERE id=?',(self.clock(),'preparing' if chosen else 'choice',chosen,ident))
        self.queue(c,f'summary:{ident}','summary',ident)
        if chosen:self.queue(c,f'create:{ident}','create',ident)
        if user:self.log(c,user,'close-vote',ident)
    def due(self):
        with self.lock,self.db() as c:
            for row in list(c.execute("SELECT id FROM polls WHERE status='open' AND deadline<=?",(self.clock(),))):self._close(c,row['id'])
    def signup(self,user,ident):
        with self.lock,self.db() as c:
            p=self.poll(c,ident)
            if p['status']!='ready' or not p['bracket']:raise ValueError('Signups are not open.')
            if c.execute('SELECT count(*) FROM participants WHERE poll=?',(ident,)).fetchone()[0]>=64:raise ValueError('Tournament roster is full.')
            c.execute('INSERT OR IGNORE INTO participants(poll,user,name) VALUES(?,?,?)',(ident,user['id'],user['name']));self.queue(c,f'signup:{ident}:{user["id"]}','signup',ident,{'user':user['id']})
    def finalize(self,user,ident,podium,teams):
        """An admin confirms actual placings in Bracket. Never award preliminary standings."""
        admin(user)
        if not isinstance(podium,list) or not 1<=len(podium)<=3 or any(type(i) is not int for i in podium) or len(set(podium))!=len(podium):raise ValueError('Choose distinct podium teams, in finishing order.')
        by_id={t['id']:t for t in teams}
        if any(i not in by_id for i in podium):raise ValueError('A podium team no longer exists in Bracket.')
        with self.lock,self.db() as c:
            p=self.poll(c,ident)
            if p['status']=='final':return
            if p['status']!='ready':raise ValueError('Tournament is not ready to finalize.')
            members={r['player']:dict(r) for r in c.execute('SELECT * FROM participants WHERE poll=? AND player IS NOT NULL',(ident,))}
            result=[];seen=set()
            for rank,team in enumerate(podium,1):
                players=by_id[team].get('player_ids',[x['id'] for x in by_id[team].get('players',[])])
                if not players or any(i not in members for i in players):raise ValueError('Every podium player must have signed up through the LAN portal.')
                for player in players:
                    uid=members[player]['user']
                    if uid in seen:raise ValueError('A player cannot appear in two podium teams.')
                    seen.add(uid);result.append((ident,uid,rank,team,self.clock()))
            c.executemany('INSERT INTO awards VALUES(?,?,?,?,?)',result);c.execute("UPDATE polls SET status='final',finalized=? WHERE id=?",(self.clock(),ident))
            self.log(c,user,'confirm-results',ident);self.queue(c,f'summary:{ident}','summary',ident);self.queue(c,f'final:{ident}','final',ident)
    def cancel(self,user,ident,reason='Not enough players'):
        admin(user);reason=text(reason,200)
        with self.lock,self.db() as c:
            p=self.poll(c,ident)
            if p['status']=='cancelled':return
            if p['status']=='final':raise ValueError('Confirmed results already awarded trophies. This tournament cannot be deleted.')
            c.execute("UPDATE polls SET cancel_status=status,status='cancelled',cancelled=?,cancel_reason=? WHERE id=?",(self.clock(),reason,ident))
            c.execute('DELETE FROM outbox WHERE poll=?',(ident,))
            self.queue(c,f'summary:{ident}','summary',ident);self.queue(c,f'cancel:{ident}','cancel',ident);self.log(c,user,'delete-tournament',ident)
    def restore(self,user,ident,native_missing=False):
        admin(user)
        with self.lock,self.db() as c:
            p=self.poll(c,ident)
            if p['status']!='cancelled':raise ValueError('Tournament is not deleted.')
            status=p['cancel_status'] or ('ready' if p['bracket'] else 'open')
            if native_missing and p['bracket']:
                status='preparing';c.execute('UPDATE polls SET bracket=NULL WHERE id=?',(ident,));c.execute('UPDATE participants SET player=NULL,team=NULL WHERE poll=?',(ident,))
            c.execute('UPDATE polls SET status=?,cancelled=NULL,cancel_reason=NULL,cancel_status=NULL WHERE id=?',(status,ident))
            c.execute('DELETE FROM outbox WHERE poll=?',(ident,))
            self.queue(c,f'summary:{ident}','summary',ident)
            if status=='preparing':self.queue(c,f'create:{ident}','create',ident)
            for person in c.execute('SELECT user FROM participants WHERE poll=? AND (player IS NULL OR team IS NULL)',(ident,)):
                self.queue(c,f'signup:{ident}:{person["user"]}','signup',ident,{'user':person['user']})
            self.log(c,user,'restore-tournament',ident)
    def trophies(self,ident):
        with self.db() as c:return [dict(r) for r in c.execute("SELECT awards.poll,rank,team,awards.created,polls.name,polls.winner AS game,COALESCE(options.label,polls.winner,'Unknown game') AS gameName,polls.bracket,polls.thread FROM awards JOIN polls ON polls.id=awards.poll LEFT JOIN options ON options.poll=polls.id AND options.game=polls.winner WHERE user=? AND polls.status='final' ORDER BY awards.created DESC,awards.poll DESC",(ident,))]
    def medal_totals(self):
        with self.db() as c:
            rows=c.execute("SELECT awards.user,SUM(CASE WHEN rank=1 THEN 1 ELSE 0 END) AS gold,SUM(CASE WHEN rank=2 THEN 1 ELSE 0 END) AS silver,SUM(CASE WHEN rank=3 THEN 1 ELSE 0 END) AS bronze FROM awards JOIN polls ON polls.id=awards.poll WHERE polls.status='final' GROUP BY awards.user")
            return {r['user']:{k:r[k] for k in ('gold','silver','bronze')} for r in rows}
    def pending(self):
        with self.db() as c:
            r=c.execute('SELECT * FROM outbox WHERE next<=? ORDER BY id LIMIT 1',(self.clock(),)).fetchone();return dict(r) if r else None
    def completed(self,job):
        with self.db() as c:c.execute('DELETE FROM outbox WHERE id=? AND payload=?',(job['id'],job['payload']))
    def failed(self,job):
        with self.db() as c:c.execute('UPDATE outbox SET attempts=attempts+1,next=? WHERE id=?',(self.clock()+min(300,10*2**min(job['attempts'],5)),job['id']))

class Services:
    def __init__(self,config):self.config=config
    def token(self):
        encode=lambda x:base64.urlsafe_b64encode(x).decode().rstrip('=')
        head=encode(b'{"alg":"HS256","typ":"JWT"}');body=encode(json.dumps({'user':'organizer@lan.invalid','exp':int(time.time())+300}).encode());unsigned=head+'.'+body
        return unsigned+'.'+encode(hmac.new(self.config['jwtSecret'].encode(),unsigned.encode(),hashlib.sha256).digest())
    def api(self,path,data=None,method=None):
        body=json.dumps(data).encode() if data is not None else None
        req=Request(self.config.get('bracketUrl','http://127.0.0.1:8793/')+path,body,{'Authorization':'Bearer '+self.token(),'Content-Type':'application/json'},method=method or ('POST' if body else 'GET'))
        with urlopen(req,timeout=20) as r:return json.load(r)
    def forum(self,data):
        body=json.dumps(data).encode();req=Request(self.config.get('forumUrl','http://127.0.0.1:8792/bridge'),body,{'Content-Type':'application/json','X-LISP-Signature':hmac.new(self.config['forumSecret'].encode(),body,hashlib.sha256).hexdigest()})
        with urlopen(req,timeout=20) as r:return json.load(r)
    def tournament(self,p):
        endpoint='lisp-'+self.config.get('publicationNamespace','')+str(p['id']);rows=self.api('tournaments?filter_=ALL')['data']
        existing=next((r for r in rows if r['dashboard_endpoint']==endpoint),None)
        if existing:return existing['id']
        clubs=self.api('clubs')['data'];club=next((r for r in clubs if r['name']=='LISP LAN'),None)
        if not club:club=self.api('clubs',{'name':'LISP LAN'})['data']
        self.api('tournaments',{'club_id':club['id'],'name':p['name'],'start_time':stamp(p['start']),'dashboard_public':False,'dashboard_endpoint':endpoint,'players_can_be_in_multiple_teams':False,'auto_assign_courts':False,'duration_minutes':20,'margin_minutes':5})
        return next(r['id'] for r in self.api('tournaments?filter_=ALL')['data'] if r['dashboard_endpoint']==endpoint)
    def participant(self,p,person):
        prefix='tournaments/'+str(p['bracket']);name=person['name'];teamname=f'{name} [LISP:{person["user"]}]'
        players=self.api(prefix+'/players?limit=100')['data']['players'];player=next((x for x in players if x['name']==name),None)
        if not player:
            self.api(prefix+'/players',{'name':name,'active':True});player=next(x for x in self.api(prefix+'/players?limit=100')['data']['players'] if x['name']==name)
        teams=self.api(prefix+'/teams?limit=100')['data']['teams'];team=next((x for x in teams if x['name']==teamname),None)
        if not team:
            self.api(prefix+'/teams',{'name':teamname,'active':True,'player_ids':[player['id']]});team=next(x for x in self.api(prefix+'/teams?limit=100')['data']['teams'] if x['name']==teamname)
        return player['id'],team['id']

class Worker:
    def __init__(self,store,services):self.store=store;self.services=services;self.serial=threading.Lock()
    def body(self,p):
        lines=[f'[b]{bb(p["name"])}[/b]',f'Status: {p["status"]}',f'Vote closes: {stamp(p["deadline"])}',f'Tournament starts: {stamp(p["start"])}','',*[f'{bb(o["label"])}: {o["votes"]} vote(s)' for o in p['options']],f'[url=https://{self.services.config["host"]}/tournaments/?id={p["id"]}]Vote / join tournament[/url]']
        if p['status']=='cancelled':
            lines=[line.replace(']Vote / join tournament[/url]', '&archived=1]Tournament archive[/url]') if 'Vote / join tournament' in line else line for line in lines]
        if p['status']=='cancelled':lines+=['','[b]Tournament cancelled[/b]',bb(p['cancel_reason'] or 'Not enough players'),'No trophies were awarded.']
        if p['winner']:lines.append('Winning game: '+bb(next(o['label'] for o in p['options'] if o['game']==p['winner'])))
        if p['bracket'] and p['status']!='cancelled':lines.append(f'[url=https://{self.services.config["host"]}/bracket/tournaments/{p["bracket"]}/dashboard]Live bracket / schedule[/url]')
        if p['status']=='choice':lines.append('Tie or no votes: awaiting an administrator\'s game choice.')
        if p['participants']:lines.append('Players: '+', '.join(bb(x['name']) for x in p['participants']))
        if p['awards']:
            lines+=['','[b]Confirmed results[/b]']+[f'{a["rank"]}. [url=https://{self.services.config["host"]}/trophies/?user={a["user"]}]{bb(a["name"])}[/url]' for a in p['awards']]
        return '\n'.join(lines)
    def tick(self):
        if not self.serial.acquire(False):return
        try:
            self.store.due()
            for _ in range(12):
                job=self.store.pending()
                if not job:break
                try:self.process(job);self.store.completed(job)
                except Exception:
                    # Never log response bodies or private credentials.
                    self.store.failed(job);print('Community publication delayed: '+job['op'],flush=True)
        finally:self.serial.release()
    def process(self,job):
        ident=job['poll'];p=self.store.view(ident=ident)[0];op=job['op']
        if p['status']=='cancelled' and op not in ('summary','cancel'):return
        if op=='cancel' and p['status']!='cancelled':return
        if op=='create':
            bid=self.services.tournament(p)
            with self.store.db() as c:
                c.execute("UPDATE polls SET bracket=?,status='ready' WHERE id=? AND status='preparing'",(bid,ident));self.store.queue(c,f'summary:{ident}','summary',ident);self.store.queue(c,f'result:{ident}','result',ident)
        elif op=='signup':
            person=next(x for x in p['participants'] if x['user']==json.loads(job['payload'])['user']);pid,tid=self.services.participant(p,person)
            with self.store.db() as c:
                c.execute('UPDATE participants SET player=?,team=? WHERE poll=? AND user=?',(pid,tid,ident,person['user']));self.store.queue(c,f'summary:{ident}','summary',ident)
        elif op in ('summary','result','final','cancel'):
            result=self.services.forum({'key':self.services.config.get('publicationNamespace','')+f'poll:{ident}','event':None if op=='summary' else op,'subject':p['name'],'body':self.body(p)})
            with self.store.db() as c:c.execute('UPDATE polls SET thread=? WHERE id=?',(result['topic'],ident))
