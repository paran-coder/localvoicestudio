"""Tray-owned engine process. No persistent console or global startup registration."""
import os,sys,subprocess,threading,importlib.util,ctypes,json,time,urllib.request,socket
from pathlib import Path
ROOT=Path(__file__).resolve().parent
LOG=ROOT/'2026-10-22-cache'/'temp';LOG.mkdir(parents=True,exist_ok=True)
sys.stdout=(LOG/'engine-output.log').open('a',encoding='utf-8',buffering=1);sys.stderr=(LOG/'engine-error.log').open('a',encoding='utf-8',buffering=1)
os.environ.update(PYTHONUTF8='1',TEMP=str(LOG),TMP=str(LOG),OLLAMA_HOST='127.0.0.1:11435',OLLAMA_MODELS=str(ROOT/'2026-10-22-cache/ollama-models'))
os.environ['PATH']=str(ROOT/'2026-10-22-tools')+os.pathsep+os.environ['PATH']
def alert(message):ctypes.windll.user32.MessageBoxW(0,message,'Local Voice Studio',0x40)
ollama=None;server=None
def main():
 global ollama,server
 for port in (8766,11435):
  with socket.socket() as sock:
   if sock.connect_ex(('127.0.0.1',port))==0:raise RuntimeError(f'{port} 포트가 사용 중입니다. 기존 배포용 엔진을 확인하세요.')
 spec=importlib.util.spec_from_file_location('bridge',ROOT/'2026-10-22-bridge.py');bridge=importlib.util.module_from_spec(spec);spec.loader.exec_module(bridge)
 import pystray
 from PIL import Image,ImageDraw
 stdout=(LOG/'ollama-output.log').open('ab');stderr=(LOG/'ollama-error.log').open('ab')
 ollama=subprocess.Popen([str(ROOT/'2026-10-22-tools/ollama/ollama.exe'),'serve'],stdout=stdout,stderr=stderr,creationflags=subprocess.CREATE_NO_WINDOW)
 ready=False
 for _ in range(30):
  try:
   with urllib.request.urlopen('http://127.0.0.1:11435/api/tags',timeout=2):ready=True
   break
  except Exception:time.sleep(1)
 if not ready:raise RuntimeError('번역 엔진을 시작하지 못했습니다. cache/temp 로그를 확인하세요.')
 server=bridge.serve();threading.Thread(target=server.serve_forever,daemon=True).start()
 image=Image.new('RGB',(64,64),'#181a20');draw=ImageDraw.Draw(image);draw.rounded_rectangle((8,8,56,56),radius=12,fill='#fcd535');draw.line((23,22,23,42,40,42),fill='#181a20',width=5)
 def status(icon,item):alert('엔진 실행 중 · 127.0.0.1:8766\n웹 연결: '+str(len(bridge.sessions))+'개\nOllama: '+('실행 중' if ollama.poll() is None else '중지됨'))
 def show_code(icon,item):alert('웹 편집 화면에서 연결할 사이트 주소를 확인한 뒤 아래 코드를 입력하세요.\n\n연결 코드: '+bridge.code+'\n\n새로고침·엔진 재시작 후 다시 연결해야 합니다.')
 def reset(icon,item):bridge.rotate();show_code(icon,item)
 def stop(icon,item):
  if any(j['state'] in ('queued','running') for j in bridge.app.jobs.values()):
   if ctypes.windll.user32.MessageBoxW(0,'진행 중인 작업이 중단됩니다. 엔진을 종료할까요?','Local Voice Studio',0x24)!=6:return
  server.shutdown();icon.stop()
 icon=pystray.Icon('LocalVoiceStudio',image,'Local Voice Studio · 엔진 실행 중',menu=pystray.Menu(pystray.MenuItem('상태 확인',status),pystray.MenuItem('웹 연결 코드',show_code,default=True),pystray.MenuItem('연결 해제·코드 변경',reset),pystray.MenuItem('종료',stop)))
 icon.run()
try:main()
except Exception as exc:
 (LOG/'engine-error.txt').write_text(str(exc),encoding='utf-8');alert('엔진 실행 오류: '+str(exc))
finally:
 if server:server.server_close()
 if ollama and ollama.poll() is None:ollama.terminate()
