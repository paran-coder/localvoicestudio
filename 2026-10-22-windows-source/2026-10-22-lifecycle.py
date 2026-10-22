"""Per-tab lifetime and single-use local launch approvals. Standard library only."""
import json,re,time,threading
from pathlib import Path

class Leases:
 def __init__(self,ttl=180,now=None):
  self.ttl=ttl;self.started=time.monotonic() if now is None else now;self.tabs={};self.lock=threading.RLock()
 def touch(self,token,now=None):
  with self.lock:self.tabs[token]=time.monotonic() if now is None else now
 def release(self,token):
  with self.lock:self.tabs.pop(token,None)
 def expired(self,now=None,active=False):
  now=time.monotonic() if now is None else now
  with self.lock:
   self.tabs={k:v for k,v in self.tabs.items() if now-v<self.ttl}
   return not active and not self.tabs and now-self.started>=self.ttl

ticket_lock=threading.Lock()
def consume_ticket(directory,nonce,origin):
 if not isinstance(nonce,str) or not re.fullmatch('[0-9a-f]{64}',nonce):return False
 with ticket_lock:
  p=Path(directory)/(nonce+'.json')
  try:
   data=json.loads(p.read_text(encoding='utf-8-sig'))
   if data.get('origin')!=origin or not 0<=time.time()-data['created']<=120:return False
   p.unlink();return True
  except (OSError,ValueError,KeyError,TypeError):return False
