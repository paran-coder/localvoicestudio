"""Authenticated loopback bridge for the separately hosted editor."""
import importlib.util,json,secrets,time,threading,urllib.parse,os,hashlib
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from pathlib import Path
from http.server import ThreadingHTTPServer
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('local_app',ROOT/'2026-10-22-app.py')
app=importlib.util.module_from_spec(spec);spec.loader.exec_module(app)
PORT=int(os.environ.get('VOICE_BRIDGE_PORT','8766'))
code=f'{secrets.randbelow(100000000):08d}'
sessions={};attempts=[];guard=threading.RLock()
spec_l=importlib.util.spec_from_file_location('lifetime',ROOT/'2026-10-22-lifecycle.py')
lifetime=importlib.util.module_from_spec(spec_l);spec_l.loader.exec_module(lifetime)
leases=lifetime.Leases()
TICKETS=ROOT/'2026-10-22-cache/tickets'
accepting=True
def valid_origin(origin):
 try:
  u=urllib.parse.urlsplit(origin)
  return origin==f'{u.scheme}://{u.netloc}' and not u.username and not u.password and (u.scheme=='https' or u.scheme=='http' and u.hostname in ('127.0.0.1','localhost'))
 except Exception:return False
def rotate():
 global code
 with guard:code=f'{secrets.randbelow(100000000):08d}';sessions.clear()
class Handler(app.Handler):
 def trusted(self):return self.headers.get('Host') in (f'127.0.0.1:{PORT}',f'localhost:{PORT}')
 def reply(self,status,body,kind='application/json; charset=utf-8'):
  if isinstance(body,dict):body=json.dumps(body,ensure_ascii=False).encode()
  if isinstance(body,str):body=body.encode()
  self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(body)))
  self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','no-referrer');self.send_header('X-Frame-Options','DENY')
  origin=self.headers.get('Origin','')
  if valid_origin(origin) and (origin in sessions.values() or self.path in ('/connect','/health') or self.command=='OPTIONS'):
   self.send_header('Access-Control-Allow-Origin',origin);self.send_header('Vary','Origin')
   self.send_header('Access-Control-Allow-Methods','GET, POST, OPTIONS');self.send_header('Access-Control-Allow-Headers','Content-Type, X-App-Token');self.send_header('Access-Control-Allow-Private-Network','true')
  self.end_headers();self.wfile.write(body)
 def do_OPTIONS(self):
  if not self.trusted() or not valid_origin(self.headers.get('Origin','')):return self.reply(403,{'error':'허용되지 않는 웹 출처'})
  self.reply(204,b'')
 def authenticated(self):
  parsed=urllib.parse.urlsplit(self.path);self.path=urllib.parse.unquote(parsed.path)
  supplied=self.headers.get('X-App-Token') or urllib.parse.parse_qs(parsed.query).get('token',[''])[0]
  origin=self.headers.get('Origin','')
  with guard:
   self.session_token=supplied
   return bool(supplied) and any(secrets.compare_digest(supplied,token) and (not origin or origin==allowed) for token,allowed in sessions.items())
 def do_GET(self):
  if not self.trusted():return self.reply(403,{'error':'Host 오류'})
  if self.path=='/health':return self.reply(200,{'service':'local-voice-bridge','protocol':2,'lifetime':'tab-leases','version':'1.3.0','installation':hashlib.sha256(str(ROOT).lower().encode()).hexdigest(),'port':PORT})
  if not self.authenticated():return self.reply(401,{'error':'스튜디오 시작 버튼으로 엔진을 연결하세요.'})
  if self.path=='/':return self.reply(404,{'error':'웹 편집 화면에서 사용하세요.'})
  return super().do_GET()
 def do_POST(self):
  if not self.trusted():return self.reply(403,{'error':'Host 오류'})
  origin=self.headers.get('Origin','')
  if self.path=='/connect':
   if not valid_origin(origin):return self.reply(403,{'error':'허용되지 않는 출처'})
   try:
    length=int(self.headers.get('Content-Length',0))
    if not 0<length<4096:raise ValueError('요청 크기 오류')
    data=json.loads(self.rfile.read(length))
    with guard:
     if not accepting:return self.reply(503,{'error':'엔진 종료 중입니다. 다시 시작하세요.'})
     if not lifetime.consume_ticket(TICKETS,data.get('nonce'),origin):return self.reply(403,{'error':'로컬 실행 승인을 기다리고 있습니다.'})
     token=secrets.token_urlsafe(32);sessions[token]=origin;leases.touch(token)
    return self.reply(200,{'token':token,'lease_seconds':180})
   except (ValueError,TypeError):return self.reply(400,{'error':'연결 요청 형식 오류'})
  if not self.authenticated():return self.reply(401,{'error':'연결이 만료됐습니다. 로컬 엔진을 다시 연결하세요.'})
  if self.path in ('/lease','/release'):
   length=int(self.headers.get('Content-Length',0))
   if length>4096:return self.reply(413,{'error':'요청 크기 초과'})
   if length:self.rfile.read(length)
   with guard:
    if not accepting:return self.reply(503,{'error':'엔진 종료 중'})
    if self.path=='/lease':leases.touch(self.session_token)
    else:leases.release(self.session_token)
   return self.reply(200,{'ok':True})
  with guard:
   if not accepting:return self.reply(503,{'error':'엔진 종료 중'})
   leases.touch(self.session_token)
  # The original local worker accepts its private token; remote sessions never receive it.
  if 'X-App-Token' in self.headers:del self.headers['X-App-Token']
  self.headers['X-App-Token']=app.TOKEN
  with guard:return super().do_POST()
def serve():
 server=ThreadingHTTPServer(('127.0.0.1',PORT),Handler)
 def monitor():
  global accepting
  while True:
   time.sleep(1)
   with guard:
    active=any(j['state'] in ('queued','running') for j in app.jobs.values())
    if not leases.expired(active=active):continue
    accepting=False
   server.shutdown();return
 threading.Thread(target=monitor,daemon=True).start()
 return server
