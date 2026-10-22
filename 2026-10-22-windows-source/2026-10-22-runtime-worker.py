"""Configured reuse adapter; never edits reused environments."""
import os,sys,json,importlib.util,threading,ast,inspect,textwrap
from pathlib import Path
ROOT=Path(__file__).resolve().parent
config=json.loads((ROOT/'2026-10-22-environment.json').read_text(encoding='utf-8-sig'))
data=ROOT/'2026-10-22-results';data.mkdir(exist_ok=True)
temp=ROOT/'2026-10-22-cache/temp';temp.mkdir(parents=True,exist_ok=True)
os.environ.update(PYTHONUTF8='1',HF_HOME=config['hf_home'],TORCH_HOME=config['torch_home'],XDG_CACHE_HOME=str(ROOT/'2026-10-22-cache'),PKUSEG_HOME=str(ROOT/'2026-10-22-cache/pkuseg'),TEMP=str(temp),TMP=str(temp),HF_HUB_DISABLE_TELEMETRY='1')
os.environ['PATH']=str(Path(config['ffmpeg']).parent)+os.pathsep+os.environ['PATH']
import tempfile
tempfile.tempdir=str(temp)
spec=importlib.util.spec_from_file_location('bridge',ROOT/'2026-10-22-bridge.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
# Original engine pins package-local caches during import. Restore the selected stores.
for key in ['HF_HOME','TORCH_HOME']:os.environ[key]=config[key.lower()]
os.environ['TEMP']=os.environ['TMP']=str(temp);tempfile.tempdir=str(temp)
original_request=b.app.engine.request_json
def request(url,payload,headers=None):
 if isinstance(payload,dict) and '/api/' in url:payload={**payload,'keep_alive':0}
 return original_request(url.replace('http://127.0.0.1:11435',config['ollama_url']),payload,headers)
b.app.engine.request_json=request
import whisper
load_model=whisper.load_model
def load(name,*args,**kwargs):
 candidate=Path(config['whisper_home'])/(str(name)+'.pt')
 if candidate.is_file():name=str(candidate)
 return load_model(name,*args,**kwargs)
whisper.load_model=load
original_recognize=b.app.engine.quality.recognize
def recognize(path,text,language,cache):return original_recognize(path,text,language,Path(config['whisper_home']).parent)
b.app.engine.quality.recognize=recognize

# Compatibility guard is applied only in this process, never to site-packages on disk.
from chatterbox.models.t3.inference.alignment_stream_analyzer import AlignmentStreamAnalyzer
method=AlignmentStreamAnalyzer.step
tree=ast.parse(textwrap.dedent(inspect.getsource(method)))
for node in ast.walk(tree):
 if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='alignment_repetition' for t in node.targets):
  node.value=ast.BoolOp(op=ast.And(),values=[ast.Compare(left=ast.Name(id='S',ctx=ast.Load()),ops=[ast.Gt()],comparators=[ast.Constant(5)]),node.value])
ast.fix_missing_locations(tree);scope={};exec(compile(tree,'<local-compatibility-guard>','exec'),method.__globals__,scope);AlignmentStreamAnalyzer.step=scope['step']
server=b.serve()
try:server.serve_forever()
finally:server.server_close()
