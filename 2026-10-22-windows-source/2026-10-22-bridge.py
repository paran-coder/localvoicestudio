"""Authenticated loopback bridge for the separately hosted editor."""
import importlib.util,json,secrets,time,threading,urllib.parse,os
from pathlib import Path
from http.server import ThreadingHTTPServer
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('local_app',ROOT/'2026-10-22-app.py')
app=importlib.util.module_from_spec(spec);spec.loader.exec_module(app)
PORT=int(os.environ.get('VOICE_BRIDGE_PORT','8766'))
code=f'{secrets.randbelow(100000000):08d}'
sessions={};attempts=[];guard=threading.Lock()
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
  if valid_origin(origin) and (origin in sessions or self.path in ('/pair','/health') or self.command=='OPTIONS'):
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
   return bool(supplied) and any(secrets.compare_digest(supplied,token) and (not origin or origin==allowed) for allowed,token in sessions.items())
 def do_GET(self):
  if not self.trusted():return self.reply(403,{'error':'Host 오류'})
  if self.path=='/health':return self.reply(200,{'service':'local-voice-bridge','protocol':1,'port':PORT})
  if not self.authenticated():return self.reply(401,{'error':'트레이의 연결 코드를 입력해 다시 연결하세요.'})
  if self.path=='/':return self.reply(404,{'error':'웹 편집 화면에서 사용하세요.'})
  return super().do_GET()
 def do_POST(self):
  if not self.trusted():return self.reply(403,{'error':'Host 오류'})
  origin=self.headers.get('Origin','')
  if self.path=='/pair':
   if not valid_origin(origin):return self.reply(403,{'error':'HTTPS 웹 화면 또는 로컬 미리보기에서 연결하세요.'})
   with guard:
    now=time.monotonic();attempts[:]=[t for t in attempts if now-t<60]
    if len(attempts)>=5:return self.reply(429,{'error':'연결 시도가 많습니다. 1분 후 다시 시도하세요.'})
    attempts.append(now)
   try:
    length=int(self.headers.get('Content-Length',0))
    if not 0<length<4096:raise ValueError('요청 크기 오류')
    data=json.loads(self.rfile.read(length))
    if not secrets.compare_digest(str(data.get('code','')),code):return self.reply(403,{'error':'연결 코드가 다릅니다. 트레이에서 확인하세요.'})
    token=secrets.token_urlsafe(32)
    with guard:sessions[origin]=token
    return self.reply(200,{'token':token})
   except Exception as exc:return self.reply(400,{'error':str(exc)})
  if not self.authenticated():return self.reply(401,{'error':'연결이 만료됐습니다. 로컬 엔진을 다시 연결하세요.'})
  # The original local worker accepts its private token; remote sessions never receive it.
  if 'X-App-Token' in self.headers:del self.headers['X-App-Token']
  self.headers['X-App-Token']=app.TOKEN
  return super().do_POST()
def serve():return ThreadingHTTPServer(('127.0.0.1',PORT),Handler)
