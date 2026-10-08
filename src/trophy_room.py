"""Public medal standings and cached forum avatars for authenticated viewers."""
import threading,time

class TrophyRoom:
    def __init__(self,store,services,clock=time.time):
        self.store=store;self.services=services;self.clock=clock;self.lock=threading.RLock();self.cached=None
    def avatars(self,users):
        ids=tuple(sorted(p['id'] for p in users));now=self.clock()
        with self.lock:
            if self.cached and self.cached[0]==ids and now-self.cached[1]<25:return self.cached[2]
            pictures={}
            try:
                for offset in range(0,len(ids),200):
                    data=self.services.forum({'key':'trophy-avatars','operation':'avatars','users':list(ids[offset:offset+200])})
                    pictures.update({int(k):v for k,v in data['avatars'].items() if v and v.startswith('/forum/')})
            except Exception:
                return {},False
            result=(pictures,True);self.cached=(ids,now,result);return result
    def listing(self,users):
        medals=self.store.medal_totals();pictures,available=self.avatars(users)
        rows=[{'id':p['id'],'name':p['name'],'avatar':pictures.get(p['id']),**medals.get(p['id'],{'gold':0,'silver':0,'bronze':0})} for p in users]
        rows.sort(key=lambda p:(-p['gold'],-p['silver'],-p['bronze'],p['name'].casefold(),p['id']))
        return {'users':rows,'avatarsAvailable':available}
