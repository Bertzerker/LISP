"""Local fixed-precision credit ledger; no currency or real payment provider."""
import json,re,time,subprocess
from decimal import Decimal,InvalidOperation,ROUND_DOWN
MICRO=1000000
DEFAULT={'cpuMinutesPerToken':60,'networkGiBPerToken':1,'negativeLimit':0}
def number(value,minimum,maximum):
    if isinstance(value,bool) or not isinstance(value,(str,int,float)):raise ValueError('Enter a valid number.')
    try:x=Decimal(str(value))
    except InvalidOperation:raise ValueError('Enter a valid number.')
    if not x.is_finite() or x<minimum or x>maximum or x.as_tuple().exponent < -6:raise ValueError('Number is outside the allowed range or has more than six decimals.')
    return x
def tokens(micro):return float(Decimal(micro)/MICRO)
class Credits:
    def init_credits(self):
        with self.db() as c:
            c.executescript('''
CREATE TABLE IF NOT EXISTS credit_wallets(user_id INTEGER PRIMARY KEY REFERENCES users(id),balance_micro INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS credit_policy(id INTEGER PRIMARY KEY CHECK(id=1),value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS credit_runs(id TEXT PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id),server_id TEXT,cpu_us INTEGER NOT NULL DEFAULT 0,rx_bytes INTEGER NOT NULL DEFAULT 0,tx_bytes INTEGER NOT NULL DEFAULT 0,charged_micro INTEGER NOT NULL DEFAULT 0,remainder TEXT NOT NULL DEFAULT '0',updated REAL);
CREATE TABLE IF NOT EXISTS credit_topups(id TEXT PRIMARY KEY,actor INTEGER NOT NULL,user_id INTEGER NOT NULL REFERENCES users(id),amount_micro INTEGER NOT NULL,created REAL);
CREATE INDEX IF NOT EXISTS credit_runs_user ON credit_runs(user_id,updated);
''')
            c.execute('INSERT OR IGNORE INTO credit_policy VALUES(1,?)',(json.dumps(DEFAULT),))
    def credit_policy(self,c=None):
        if c is None:
            with self.db() as c:return self.credit_policy(c)
        return json.loads(c.execute('SELECT value FROM credit_policy WHERE id=1').fetchone()[0])
    def wallet(self,c,ident):
        if type(ident) is not int:raise ValueError('Choose an account.')
        user=c.execute('SELECT id,role,enabled FROM users WHERE id=?',(ident,)).fetchone()
        if not user:raise ValueError('Account not found.')
        c.execute('INSERT OR IGNORE INTO credit_wallets(user_id) VALUES(?)',(ident,))
        return user,c.execute('SELECT balance_micro FROM credit_wallets WHERE user_id=?',(ident,)).fetchone()[0]
    def credit_status(self,ident,history=False,c=None):
        if c is None:
            with self.lock,self.db() as c:return self.credit_status(ident,history,c)
        user,balance=self.wallet(c,ident);policy=self.credit_policy(c)
        value={'creditTokenBalance':tokens(balance),'creditExempt':user['role']=='admin','creditPolicy':policy,'canStartPaidServer':bool(user['enabled'] and (user['role']=='admin' or Decimal(balance)/MICRO>-Decimal(str(policy['negativeLimit']))))}
        if history:
            value['usage']=[{'runId':r['id'],'serverId':r['server_id'],'cpuSeconds':r['cpu_us']/MICRO,'networkBytes':r['rx_bytes']+r['tx_bytes'],'chargedTokens':tokens(r['charged_micro']),'updated':r['updated']} for r in c.execute('SELECT * FROM credit_runs WHERE user_id=? ORDER BY updated DESC LIMIT 20',(ident,))]
        return value
    def manage_credits(self,actor,data):
        if actor['role']!='admin':raise PermissionError('Administrator access required.')
        with self.lock,self.db() as c:
            if data.get('op')=='settings':
                policy={'cpuMinutesPerToken':float(number(data.get('cpuMinutesPerToken'),Decimal('.000001'),1000000)), 'networkGiBPerToken':float(number(data.get('networkGiBPerToken'),Decimal('.000001'),1000000)), 'negativeLimit':float(number(data.get('negativeLimit'),0,1000000))}
                c.execute('UPDATE credit_policy SET value=? WHERE id=1',(json.dumps(policy),));self.audit(c,actor['id'],'credit-settings',None)
                return {'creditPolicy':policy}
            if data.get('op')!='add':raise ValueError('Unsupported credit action.')
            ident=data.get('id');amount=int(number(data.get('amount'),Decimal('.000001'),1000000)*MICRO);key=data.get('requestId')
            if not isinstance(key,str) or not re.fullmatch('[a-f0-9]{32}',key):raise ValueError('Refresh the page and retry.')
            user,balance=self.wallet(c,ident);previous=c.execute('SELECT actor,user_id,amount_micro FROM credit_topups WHERE id=?',(key,)).fetchone()
            if previous:
                if tuple(previous)!=(actor['id'],ident,amount):raise ValueError('Credit request already used.')
            else:
                if balance+amount>1000000000*MICRO:raise ValueError('Account balance limit reached.')
                c.execute('UPDATE credit_wallets SET balance_micro=balance_micro+? WHERE user_id=?',(amount,ident));c.execute('INSERT INTO credit_topups VALUES(?,?,?,?,?)',(key,actor['id'],ident,amount,time.time()));self.audit(c,actor['id'],'credit-add',ident)
            return self.credit_status(ident,c=c)
    def credit_authorize(self,ident,run_id,server_id):
        if not isinstance(run_id,str) or not re.fullmatch('[a-f0-9]{32}',run_id):raise ValueError('Invalid billing run.')
        if server_id is not None and (not isinstance(server_id,str) or not re.fullmatch('[a-f0-9]{12}',server_id)):raise ValueError('Invalid server.')
        with self.lock,self.db() as c:
            status=self.credit_status(ident,c=c)
            if not status['canStartPaidServer']:raise PermissionError('Credit limit reached. Ask an admin to add Credit Tokens before starting a server.')
            previous=c.execute('SELECT user_id FROM credit_runs WHERE id=?',(run_id,)).fetchone()
            if previous and previous['user_id']!=ident:raise ValueError('Billing run already used.')
            c.execute('INSERT OR IGNORE INTO credit_runs(id,user_id,server_id,updated) VALUES(?,?,?,?)',(run_id,ident,server_id,time.time()))
            return status
    def credit_charge(self,data):
        values=[data.get(x) for x in ('cpuUs','rxBytes','txBytes')]
        if any(type(x) is not int or x<0 or x>10**18 for x in values):raise ValueError('Invalid usage counters.')
        with self.lock,self.db() as c:
            r=c.execute('SELECT * FROM credit_runs WHERE id=?',(data.get('runId'),)).fetchone()
            if not r:raise ValueError('Billing run not found.')
            old=[r[x] for x in ('cpu_us','rx_bytes','tx_bytes')]
            if any(new<prev for new,prev in zip(values,old)):raise ValueError('Usage counters moved backwards.')
            status=self.credit_status(r['user_id'],c=c);policy=status['creditPolicy'];delta=[new-prev for new,prev in zip(values,old)]
            raw=Decimal(r['remainder'])+Decimal(delta[0])/(Decimal(str(policy['cpuMinutesPerToken']))*60)+Decimal(delta[1]+delta[2])*MICRO/(Decimal(str(policy['networkGiBPerToken']))*1073741824)
            debit=int(raw.to_integral_value(rounding=ROUND_DOWN));remainder=raw-debit
            user,balance=self.wallet(c,r['user_id']);floor=-int(Decimal(str(policy['negativeLimit']))*MICRO)
            if status['creditExempt']:debit=0;remainder=Decimal(0)
            else:debit=min(debit,max(0,balance-floor))
            c.execute('UPDATE credit_wallets SET balance_micro=balance_micro-? WHERE user_id=?',(debit,r['user_id']))
            c.execute('UPDATE credit_runs SET cpu_us=?,rx_bytes=?,tx_bytes=?,charged_micro=charged_micro+?,remainder=?,server_id=COALESCE(server_id,?),updated=? WHERE id=?',(*values,debit,str(remainder),data.get('serverId'),time.time(),r['id']))
            status=self.credit_status(r['user_id'],c=c);status.update(chargedTokens=tokens(r['charged_micro']+debit),limitReached=not status['canStartPaidServer'])
            return status


_controller_pid=(0,0)
def controller_peer(uid,pid):
    """Game processes share a UID, but only the systemd main controller may bill."""
    global _controller_pid
    if uid==0:return True
    now=time.monotonic()
    if now-_controller_pid[1]>1:
        try:main=int(subprocess.check_output(['/usr/bin/systemctl','show','lan-portal.service','--property=MainPID','--value'],timeout=2).strip())
        except (OSError,ValueError,subprocess.SubprocessError):return False
        _controller_pid=(main,now)
    return pid==_controller_pid[0] and pid>0
