"""Local engine adapters. Imports are lazy; never generate substitute audio."""
import re,os,json,subprocess,urllib.request,importlib.util,sys,gc,zipfile,copy
from pathlib import Path
ROOT=Path(__file__).resolve().parent
CACHE=ROOT/'2026-10-22-cache'
CACHE.mkdir(exist_ok=True)
(CACHE/'temp').mkdir(exist_ok=True)
os.environ['PKUSEG_HOME']=str(CACHE/'pkuseg')
os.environ['TEMP']=str(CACHE/'temp')
os.environ['TMP']=str(CACHE/'temp')
import tempfile
tempfile.tempdir=str(CACHE/'temp')
for k,v in {'HF_HOME':CACHE/'huggingface','TORCH_HOME':CACHE/'torch','XDG_CACHE_HOME':CACHE,'NUMBA_CACHE_DIR':CACHE/'numba'}.items():os.environ[k]=str(v)
spec=importlib.util.spec_from_file_location('core',ROOT/'2026-10-22-core.py');core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core)
LANGUAGES=core.LANGUAGES
qs=importlib.util.spec_from_file_location('quality',ROOT/'2026-10-22-language-check.py');quality=importlib.util.module_from_spec(qs);qs.loader.exec_module(quality)
ss=importlib.util.spec_from_file_location('speakers',ROOT/'2026-10-22-speakers.py');speakers=importlib.util.module_from_spec(ss);ss.loader.exec_module(speakers)
model=None
cs=importlib.util.spec_from_file_location('captions',ROOT/'2026-10-22-captions.py');captions=importlib.util.module_from_spec(cs);cs.loader.exec_module(captions)

def run(args):
 p=subprocess.run([str(x) for x in args],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=3600)
 if p.returncode:raise RuntimeError(p.stderr[-3000:] or p.stdout[-3000:])
 return p.stdout

def status():
 modules={m:bool(importlib.util.find_spec(m)) for m in ['torch','chatterbox','whisper','yt_dlp','soundfile']}
 return {'python':sys.executable,'modules':modules,'languages':LANGUAGES,'version':'1.1.0'}

def read_segments(path,report_path=None):
 data=json.loads(Path(path).read_text(encoding='utf-8-sig'))
 if isinstance(data,list):return core.validate(data)
 rows,report=captions.parse_json3(data,core.clean_speech)
 if report_path:Path(report_path).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 return core.validate(rows)

def extract(data,folder,log):
 global model
 lang=data.get('source_language','ko');size=data.get('whisper','base')
 if lang not in LANGUAGES or size not in ['tiny','base','small','medium']:raise ValueError('언어/Whisper 설정 오류')
 if data.get('url'):
  url=data['url'].strip()
  if not core.youtube_url(url):raise ValueError('HTTPS YouTube 링크만 사용할 수 있습니다.')
  log('YouTube 자막을 먼저 확인합니다.')
  import yt_dlp
  opts={'noplaylist':True,'outtmpl':str(folder/'source.%(ext)s'),'writesubtitles':True,'writeautomaticsub':True,'subtitleslangs':[lang],'subtitlesformat':'json3','skip_download':True,'quiet':True,'socket_timeout':30,'cachedir':str(CACHE/'yt-dlp')}
  with yt_dlp.YoutubeDL(opts) as y:y.download([url])
  caption_files=list(folder.glob('*.json3'))
  if caption_files:
   rows=read_segments(caption_files[0],folder/'2026-10-22-caption-report.json')
   log(f'YouTube 자막을 문장 단위로 정리했습니다 · {len(rows)}개. 자동 인식 원문의 오타와 발화 경계는 검토가 필요합니다.')
   return {'rows':rows,'source':'YouTube captions · sentence grouping','caption_notice':'원본 단어 시간으로 문장을 정리했습니다. 자동 인식 원문과 표시 종료 시각에는 오류가 있을 수 있습니다.'}
  log('자막이 없어 음성을 다운로드합니다.')
  opts.update(skip_download=False,format='bestaudio/best',writesubtitles=False,writeautomaticsub=False,match_filter=yt_dlp.utils.match_filter_func('duration <= 14400'))
  with yt_dlp.YoutubeDL(opts) as y:y.download([url])
  paths=[x for x in folder.glob('source.*') if x.suffix!='.json3']
  if not paths:raise ValueError('오디오 다운로드 실패')
  src=paths[0]
 else:src=Path(data['media_path'])
 log('Whisper 음성 인식 중. 첫 실행은 모델을 다운로드합니다.')
 import whisper,torch
 if model is not None:model=None;gc.collect();torch.cuda.empty_cache()
 audio=folder/'stt.wav';run(['ffmpeg','-v','error','-i',src,'-t','14400','-ac','1','-ar','16000',audio])
 stt=whisper.load_model(size,device='cpu',download_root=str(CACHE/'whisper'))
 result=stt.transcribe(str(audio),language=lang,fp16=False,verbose=False)
 rows=[[s['start'],s['end'],s['text'].strip()] for s in result['segments'] if s['text'].strip()]
 del stt;gc.collect()
 return {'rows':core.validate(rows),'source':'Whisper '+size}

def request_json(url,payload,headers=None):
 req=urllib.request.Request(url,json.dumps(payload).encode(),{'Content-Type':'application/json',**(headers or {})})
 with urllib.request.urlopen(req,timeout=300) as r:return json.load(r)

def translate(data,folder,log):
 global model
 rows=core.validate(data['rows']);lang=data['language'];mode=data.get('translator','ollama')
 if lang not in LANGUAGES:raise ValueError('지원하지 않는 언어')
 if model is not None:
  import torch
  model=None;gc.collect();torch.cuda.empty_cache()
 profiles,speaker_ids=speakers.validate(data,len(rows))
 out=[list(r) for r in rows];items=[{'id':i+1,'speaker':profiles[speaker_ids[i]]['name'],'text':core.clean_speech(r[2])} for i,r in enumerate(rows) if core.clean_speech(r[2])]
 report=[]
 try:
  for batch in captions.batches(items):
   first,last=batch[0]['id']-1,batch[-1]['id']-1
   context={'before':[r[2] for r in rows[max(0,first-2):first]],'after':[r[2] for r in rows[last+1:last+3]]}
   prompt=f'Translate each current subtitle into {LANGUAGES[lang]} ({lang}). Return ONLY a JSON object with a translations array; each element has id (integer) and text (string). Return exactly one entry for every supplied id. Never invent IDs, duplicate dialogue or translate context-only rows. Preserve meaning, negation, speaker perspective, questions, names and consistent honorifics. These may be automatic speech captions: resolve likely spelling mistakes from dialogue context, do not translate apparent homophones literally when context contradicts them. If unclear, do not invent missing facts. If already in the target language, preserve wording. Output only spoken dialogue, no labels or explanations. Context only: '+json.dumps(context,ensure_ascii=False)[:500]+'\nCurrent batch JSON:\n'+json.dumps(batch,ensure_ascii=False)
   log(f'문맥 묶음 번역 · {batch[0]["id"]}~{batch[-1]["id"]}/{len(rows)}')
   if mode=='ollama':
    result=request_json('http://127.0.0.1:11435/api/generate',{'model':data.get('translation_model') or 'gemma4:latest','prompt':prompt,'format':'json','stream':False,'keep_alive':'2m','think':False,'options':{'num_ctx':4096,'num_predict':1536,'temperature':.1}})['response']
   elif mode=='api':
    key=os.environ.get('TTS_API_KEY');base=os.environ.get('TTS_API_BASE');name=os.environ.get('TTS_API_MODEL')
    if not all([key,base,name]):raise ValueError('서버의 번역 API 환경 변수를 설정하세요.')
    result=request_json(base.rstrip('/')+'/chat/completions',{'model':name,'messages':[{'role':'user','content':prompt}]},{'Authorization':'Bearer '+key})['choices'][0]['message']['content']
   else:raise ValueError('번역 방식을 선택하세요.')
   mapped=captions.translations(result,batch)
   for number,text in mapped.items():
    i=number-1;out[i]=[rows[i][0],rows[i][1],text]
    report.append({'segment':number,'start':rows[i][0],'end':rows[i][1],'source':rows[i][2],'translation':text,'speaker':speaker_ids[i],'speaker_name':profiles[speaker_ids[i]]['name']})
   (folder/'2026-10-22-translation-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 finally:
  if mode=='ollama' and items:
   try:request_json('http://127.0.0.1:11435/api/generate',{'model':data.get('translation_model') or 'gemma4:latest','keep_alive':0})
   except Exception as exc:log(f'번역 모델 해제 확인 필요: {exc}')
 out=core.validate(out)
 (folder/'2026-10-22-translated-rows.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 return {'rows':out,'source_rows':rows,'row_speakers':speaker_ids,'files':['2026-10-22-translated-rows.json','2026-10-22-translation-report.json'] if items else ['2026-10-22-translated-rows.json']}


def assemble(rows,raw_paths,folder,lang,sr,timed,log,issues=None):
 import soundfile as sf,numpy as np
 rows=core.validate(rows)
 if len(rows)!=len(raw_paths):raise ValueError('구간과 음성 파일 수가 다릅니다.')
 # A valid speech clip is never shortened, stretched, or replaced by silence.
 segments=[];actual=[];cursor=0
 output=folder/f'{lang}-natural.wav'
 with sf.SoundFile(output,'w',samplerate=sr,channels=1,subtype='PCM_16') as dest:
  def silence(frames):
   while frames:
    n=min(frames,sr*10);dest.write(np.zeros(n,dtype=np.int16));frames-=n
  for i,((a,b,text),raw) in enumerate(zip(rows,raw_paths)):
   spoken=core.clean_speech(text)
   if spoken and raw is None:raise ValueError(f'{i+1}번 대사 음성이 없습니다. 무음으로 대체하지 않았습니다.')
   samples=np.zeros(0,dtype=np.int16)
   if spoken:
    samples,rate=sf.read(raw,dtype='int16')
    if rate!=sr or samples.ndim!=1 or not len(samples):raise ValueError(f'{i+1}번 음성 형식 오류')
   start=max(round(a*sr),cursor) if timed else cursor
   silence(start-cursor)
   dest.write(samples);speech_end=start+len(samples)
   end=max(round(b*sr),speech_end) if timed else speech_end
   silence(end-speech_end);cursor=end
   shift=max(0,start/sr-a) if timed else 0
   entry={'segment':i+1,'source_start':a,'source_end':b,'original_text':text,'text':spoken,'raw_duration':len(samples)/sr,'note_only':not bool(spoken),'unresolved':False,'start':start/sr,'end':end/sr,'speech_end':speech_end/sr,'speed':1.0,'shift':shift,'padding':(end-speech_end)/sr,'overrun':max(0,speech_end/sr-b) if timed and spoken else 0}
   segments.append(entry)
   if spoken:actual.append([start/sr,speech_end/sr,spoken])
 report={'version':'1.0.7','policy':'unaltered_speech','speed_min':1.0,'speed_max':1.0,'duration':cursor/sr,'source_end':rows[-1][1],'note_only_count':sum(x['note_only'] for x in segments),'shifted_count':sum(x['shift']>.001 for x in segments),'max_shift':max(x['shift'] for x in segments),'sync_required':any(x['overrun']>.001 or x['shift']>.001 for x in segments),'segments':segments,'unresolved':[],'preview':False}
 subtitles=folder/f'{lang}-natural.srt';subtitles.write_text(core.srt(actual) if actual else '',encoding='utf-8-sig')
 reportpath=folder/'timing-report.json';reportpath.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 archive=folder/f'{lang}-natural-dubbing.zip'
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
  for path in [output,subtitles,reportpath]:z.write(path,path.name)
 log(f'원음 보존 생성 · 대사 {len(actual)}개 · 배속 변경 없음 · 최대 시작 이동 {report["max_shift"]:.2f}초')
 return {'files':[output.name,subtitles.name,archive.name,reportpath.name],'rows':rows,'preview':False,'unresolved':[],'sync_required':report['sync_required'],'device':str(getattr(model,'device','cpu')),'timing':{k:report[k] for k in ['duration','note_only_count','shifted_count','max_shift']}}


def generate(data,folder,log):
 global model
 rows=core.validate(data['rows']);lang=data['language']
 profiles,speaker_ids=speakers.validate(data,len(rows))
 if lang not in LANGUAGES:raise ValueError('지원하지 않는 언어')
 if data.get('translate_first',True):
  log('효과음 표기를 제외하고 대상 언어로 번역합니다.')
  if model is not None:
   import torch
   model=None;gc.collect();torch.cuda.empty_cache()
  rows=translate(dict(data,rows=rows),folder,log)['rows']
  (folder/'translated-rows.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
 for number,(_,_,text) in enumerate(rows,1):
  text=core.clean_speech(text)
  if lang=='en' and re.search('[가-힣]',text):raise ValueError(f'{number}/{len(rows)} 구간에 한국어가 남아 있습니다. 영어 번역문을 확인하세요: {text}')
 (folder/'generation-input.json').write_text(json.dumps(dict(rows=rows,language=lang),ensure_ascii=False,indent=2),encoding='utf-8')
 emotion=float(data.get('emotion',.5));cfg=float(data.get('cfg',.5))
 if not 0<=emotion<=1 or not 0<=cfg<=1:raise ValueError('감정/CFG는 0~1 범위')
 import torch,soundfile as sf
 spoken=any(core.clean_speech(r[2]) for r in rows)
 device='cuda' if torch.cuda.is_available() else 'cpu'
 def ensure_model():
  global model
  if model is None:
   quality.configure_chinese()
   from chatterbox.mtl_tts import ChatterboxMultilingualTTS
   log(f'Chatterbox 로드 ({device})');model=ChatterboxMultilingualTTS.from_pretrained(device=device)
   model._builtin_conds=copy.deepcopy(model.conds)
 if spoken:ensure_model()
 prompts={}
 for ident,profile in profiles.items():
  voice=profile.get('voice_path') if data.get('speakers') else data.get('voice_path')
  prompts[ident]=None
  if spoken and voice:
   if not data.get('consent'):raise ValueError('본인 또는 허락받은 목소리인지 확인하세요.')
   prompt=folder/f'2026-10-22-reference-{ident}.wav'
   run(['ffmpeg','-v','error','-i',voice,'-ac','1','-ar','24000','-t','30',prompt])
   if sf.info(prompt).duration<3:raise ValueError('음성 샘플은 최소 3초입니다.')
   prompts[ident]=prompt
 sr=model.sr if spoken else 24000;raw_paths=[];reviews=[];issues={};changes=[]
 timed=bool(data.get('timed',True))
 for i,(_,_,original) in enumerate(rows):
  text=core.clean_speech(original)
  if not text:
   log(f'효과음 전용 구간 발음 제외 · {i+1}/{len(rows)}');raw_paths.append(None);continue
  try:
   log(f'{LANGUAGES[lang]} 음성 생성 {i+1}/{len(rows)}')
   prompt=prompts[speaker_ids[i]]
   model.conds=copy.deepcopy(model._builtin_conds)
   quality.check_text(model.tokenizer,text,lang)
   raw,review=quality.synthesize(model,text,lang,prompt,emotion,cfg,folder,i,CACHE,log)
   review['segment']=i+1;reviews.append(review)
   (folder/'2026-10-22-quality-report.json').write_text(json.dumps(reviews,ensure_ascii=False,indent=2),encoding='utf-8')
   if review['review_required']:log(f'검수 필요 · {i+1}/{len(rows)} · 대본/재인식 차이 또는 추가 발화 의심')
   if sf.info(raw).duration<=0:raise ValueError('빈 음성이 생성되었습니다.')
   raw_paths.append(raw)
  except Exception as exc:
   issues[i+1]={'segment':i+1,'text':text,'start':rows[i][0],'end':rows[i][1],'reason':f'음성 생성 실패: {type(exc).__name__}: {exc}'}
   if len(raw_paths)<=i:raw_paths.append(None)
   log(f'합성 실패 기록 · {i+1}/{len(rows)} · {exc}')
 if issues:
  (folder/'2026-10-22-synthesis-errors.json').write_text(json.dumps(list(issues.values()),ensure_ascii=False,indent=2),encoding='utf-8')
  raise RuntimeError('실제 음성 합성 실패 구간: '+', '.join(map(str,issues))+'. 생성된 다른 구간 음성은 보존했습니다. 누락 대사를 무음으로 대체한 완성 파일은 만들지 않았습니다.')
 (folder/'2026-10-22-quality-report.json').write_text(json.dumps(sorted(reviews,key=lambda r:r['segment']),ensure_ascii=False,indent=2),encoding='utf-8')
 result=assemble(rows,raw_paths,folder,lang,sr,timed,log,issues=issues)
 finalrows=folder/'2026-10-22-final-rows.json';finalrows.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
 result['speakers']=[{'id':k,'name':v['name']} for k,v in profiles.items()]
 result['row_speakers']=speaker_ids
 manifest={'version':'1.1.0','rows':rows,'row_speakers':speaker_ids,'speakers':[{'id':k,'name':v['name']} for k,v in profiles.items()]}
 manifestpath=folder/'2026-10-22-speaker-script.json';manifestpath.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
 result['files'].append(manifestpath.name)
 if data.get('speakers'):
  timing=json.loads((folder/'timing-report.json').read_text(encoding='utf-8'))
  result['files']+=speakers.tracks(folder,folder/f'{lang}-natural.wav',profiles,speaker_ids,timing['segments'])
 result['files'].append(finalrows.name)
 result['files'].append('2026-10-22-quality-report.json') if reviews else None
 result['review_required']=sum(r['review_required'] for r in reviews)
 if data.get('translate_first',True):
  result['source_rows']=data['rows']
  result['files'].append('2026-10-22-translation-report.json') if (folder/'2026-10-22-translation-report.json').exists() else None
 if result['review_required']:log(f'자동 검수에서 {result["review_required"]}개 구간 확인 필요. 음성 검수 보고서에서 대본과 재인식을 비교하세요.')
 with zipfile.ZipFile(folder/next(name for name in result['files'] if name.endswith('.zip')),'a',zipfile.ZIP_DEFLATED) as archive:
  for name in result['files']:
   if name not in archive.namelist() and not name.endswith('.zip'):archive.write(folder/name,name)
 return result
