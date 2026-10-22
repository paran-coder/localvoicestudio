"""Loopback-only HTTP server; standard library UI, single inference worker."""
import base64,importlib.util,json,secrets,threading,traceback,uuid,os,mimetypes
from pathlib import Path
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('engine',ROOT/'2026-10-22-engine.py');engine=importlib.util.module_from_spec(spec);spec.loader.exec_module(engine)
DATA=ROOT/'2026-10-22-results';DATA.mkdir(exist_ok=True)
TOKEN=secrets.token_urlsafe(32);jobs={};lock=threading.Lock()
def execute(ident,action,data):
 job=jobs[ident]
 try:
  with lock:
   job['state']='running'
   result=getattr(engine,action)(data,DATA/ident,lambda s:job['logs'].append(s))
   job.update(state='done',result=result)
 except Exception as e:
  job.update(state='error',error=f'{type(e).__name__}: {e}')
  (DATA/ident/'error.txt').write_text(traceback.format_exc(),encoding='utf-8')
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def reply(self,code,body,kind='application/json; charset=utf-8'):
  if isinstance(body,dict):body=json.dumps(body,ensure_ascii=False).encode()
  if isinstance(body,str):body=body.encode()
  self.send_response(code);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(body)));self.send_header('X-Content-Type-Options','nosniff');self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(body)
 def trusted(self):return self.headers.get('Host') in ('127.0.0.1:8765','localhost:8765')
 def do_GET(self):
  if not self.trusted():return self.reply(403,{'error':'허용되지 않는 Host'})
  if self.path=='/':return self.reply(200,(ROOT/'2026-10-22-ui.html').read_text(encoding='utf-8').replace('__TOKEN__',TOKEN),'text/html; charset=utf-8')
  if self.path=='/status':return self.reply(200,engine.status())
  if self.path.startswith('/jobs/'):
   ident=self.path.split('/')[-1]
   return self.reply(200,jobs[ident]) if ident in jobs else self.reply(404,{'error':'작업 없음'})
  if self.path.startswith('/files/'):
   parts=self.path.split('/')
   if len(parts)!=4:return self.reply(404,{'error':'파일 없음'})
   ident,name=parts[2:];job=jobs.get(ident,{})
   if name not in job.get('result',{}).get('files',[]):return self.reply(404,{'error':'파일 없음'})
   p=DATA/ident/name
   return self.reply(200,p.read_bytes(),mimetypes.guess_type(name)[0] or 'application/octet-stream')
  return self.reply(404,{'error':'경로 없음'})
 def do_POST(self):
  if not self.trusted() or self.headers.get('X-App-Token')!=TOKEN:return self.reply(403,{'error':'인증 실패. 페이지를 새로고침하세요.'})
  try:
   length=int(self.headers.get('Content-Length','0'))
   if not 0<length<=280_000_000:raise ValueError('요청은 최대 200MB 파일까지 가능합니다.')
   data=json.loads(self.rfile.read(length))
   if self.path=='/upload':
    ext=Path(data['name']).suffix.lower()
    if ext not in {'.wav','.mp3','.m4a','.mp4','.webm','.ogg','.flac','.mov','.mkv'}:raise ValueError('지원하지 않는 파일 형식')
    content=base64.b64decode(data['content'],validate=True)
    if len(content)>200_000_000:raise ValueError('파일 최대 200MB')
    folder=DATA/'uploads';folder.mkdir(exist_ok=True);name=uuid.uuid4().hex+ext
    (folder/name).write_bytes(content)
    return self.reply(200,{'id':name})
   action=self.path.removeprefix('/')
   if action not in {'extract','translate','generate'}:return self.reply(404,{'error':'작업 없음'})
   if sum(j['state'] in {'queued','running'} for j in jobs.values())>=3:raise ValueError('대기열이 가득 찼습니다. 작업 완료 후 다시 시도하세요.')
   # Client paths are never trusted; only server-issued upload IDs are resolved.
   data.pop('media_path',None);data.pop('voice_path',None)
   for profile in data.get('speakers',[]):
    profile.pop('voice_path',None)
    voice_id=profile.get('voice')
    if voice_id:
     path=(DATA/'uploads'/voice_id).resolve()
     if path.parent!=(DATA/'uploads').resolve() or not path.is_file():raise ValueError('화자 업로드 파일 없음. 샘플을 다시 선택하세요.')
     profile['voice_path']=str(path)
   if action in {'generate','translate'}:engine.speakers.validate(data,len(data.get('rows',[])))
   for key in ['media','voice']:
    ident=data.pop(key,None)
    if ident:
     p=(DATA/'uploads'/ident).resolve()
     if p.parent!=(DATA/'uploads').resolve() or not p.is_file():raise ValueError('업로드 파일 없음')
     data[key+'_path']=str(p)
   if action=='extract' and not (data.get('url') or data.get('media_path')):raise ValueError('YouTube 링크 또는 미디어 파일을 선택하세요.')
   if action in {'generate','translate'}:engine.core.validate(data.get('rows',[]))
   ident=uuid.uuid4().hex;(DATA/ident).mkdir()
   jobs[ident]={'state':'queued','logs':[]}
   threading.Thread(target=execute,args=(ident,action,data),daemon=True).start()
   return self.reply(202,{'id':ident})
  except Exception as e:return self.reply(400,{'error':str(e)})
if __name__=='__main__':
 print('Local-AI-TTS v1.1.0 - http://127.0.0.1:8765',flush=True)
 ThreadingHTTPServer(('127.0.0.1',8765),Handler).serve_forever()
