"""Read-only Python/package probe; emits machine-readable reuse decisions."""
import sys,json,platform,importlib.metadata as md,importlib.util,re,site
from pathlib import Path
def version(name):
 try:return md.version(name)
 except md.PackageNotFoundError:return ''
def matches(line):
 match=re.fullmatch(r'([^<=>]+)(==|<)(.+)',line)
 if not match:return False
 name,op,want=match.groups();got=version(name)
 if not got:return False
 if op=='==':return got==want
 return tuple(int(x) for x in re.findall(r'\d+',got)[:2])<tuple(int(x) for x in re.findall(r'\d+',want)[:2])
def probe():
 core={'chatterbox-tts':'0.1.7','transformers':'4.46.3','numpy':'1.26.4','torch':'2.10.0','torchaudio':'2.10.0'}
 compatible=sys.version_info[:2]==(3,11) and sys.maxsize>2**32
 for name,want in core.items():compatible=compatible and version(name).split('+')[0]==want
 for name in ['whisper','soundfile','yt_dlp','librosa','PIL']:
  compatible=compatible and importlib.util.find_spec(name) is not None
 return {'python':sys.executable,'base':sys._base_executable,'sites':site.getsitepackages(),'python311':sys.version_info[:2]==(3,11) and sys.maxsize>2**32,'compatible':bool(compatible),'versions':{name:version(name) for name in core}}
if __name__=='__main__':
 if '--missing' in sys.argv:
  lines=Path(sys.argv[-1]).read_text(encoding='utf-8').splitlines()
  print(json.dumps([line for line in lines if line and not line.startswith(('torch==','torchaudio==','pystray==','six==','imageio-ffmpeg==')) and not matches(line)]))
 else:print(json.dumps(probe()))
