"""Read-only personal forum and Bracket summary for an authenticated player."""
import threading,time
from datetime import datetime,timezone

def next_matches(polls,user_id,fetch,now=None):
    now=time.time() if now is None else now
    results=[]
    for poll in polls:
        if poll['status']!='ready' or not poll.get('bracket'):continue
        person=next((p for p in poll['participants'] if p['user']==user_id),None)
        if not person or not person.get('team'):continue
        stages=fetch(f'tournaments/{poll["bracket"]}/stages')['data']
        for stage in stages:
            for item in stage.get('stage_items',[]):
                for round_ in item.get('rounds',[]):
                    if round_.get('is_draft',True):continue
                    for match in round_.get('matches',[]):
                        if match.get('stage_item_input1_score',0) or match.get('stage_item_input2_score',0):continue
                        sides=[match.get('stage_item_input1') or {},match.get('stage_item_input2') or {}]
                        own=next((i for i,s in enumerate(sides) if s.get('team_id')==person['team']),None)
                        if own is None or not match.get('start_time'):continue
                        try:
                            date=datetime.fromisoformat(match['start_time'].replace('Z','+00:00'))
                            if date.tzinfo is None:continue
                            start=date.timestamp()
                        except (ValueError,TypeError):continue
                        if start<now:continue
                        opponent=(sides[1-own].get('team') or {}).get('name') or 'Opponent to be decided'
                        results.append({'tournament':poll['name'],'pollId':poll['id'],'bracketId':poll['bracket'],'matchId':match['id'],'start':start,'opponent':opponent,'url':f'/bracket/tournaments/{poll["bracket"]}/dashboard'})
    return sorted(results,key=lambda m:(m['start'],m['pollId'],m['matchId']))

class PersonalStatus:
    def __init__(self,store,services,clock=time.time):
        self.store=store;self.services=services;self.clock=clock;self.cache={};self.lock=threading.RLock()
    def get(self,user):
        # Keyed by verified identity, never by a client-supplied profile ID.
        key=(user['id'],user['name'],user['role']);now=self.clock()
        with self.lock:
            cached=self.cache.get(key)
            if cached and now-cached[0]<25:return cached[1]
        value={'forumAvailable':False,'avatar':None,'unreadTopics':None,'unreadMessages':None,'tournamentAvailable':False,'nextMatch':None}
        try:
            actor={k:user[k] for k in ('id','name','role')}
            forum=self.services.forum({'key':'personal:'+str(user['id']),'operation':'status','user':actor})
            value.update({k:forum[k] for k in ('avatar','unreadTopics','unreadMessages')});value['forumAvailable']=True
        except Exception:pass
        try:
            polls=self.store.view(user)
            matches=next_matches(polls,user['id'],self.services.api,now)
            value['nextMatch']=matches[0] if matches else None;value['tournamentAvailable']=True
        except Exception:pass
        with self.lock:
            if len(self.cache)>=512:self.cache.clear()
            self.cache[key]=(now,value)
        return value
