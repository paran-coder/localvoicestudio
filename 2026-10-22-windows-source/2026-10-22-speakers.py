"""Speaker metadata stays separate from legacy three-column subtitle rows."""
import re,json
def validate(data,count):
 profiles=data.get('speakers',[])
 if not profiles:return {'default':{'id':'default','name':'기본 목소리'}},['default']*count
 if not isinstance(profiles,list) or len(profiles)>20:raise ValueError('화자는 최대 20명입니다.')
 result={}
 for p in profiles:
  ident=p.get('id','');name=p.get('name','').strip()
  if not isinstance(ident,str) or not re.fullmatch('[a-zA-Z0-9_-]{1,40}',ident) or ident in result or not name or len(name)>80:raise ValueError('화자 ID 또는 이름 오류')
  result[ident]={'id':ident,'name':name,'voice_path':p.get('voice_path'),'voice':p.get('voice')}
 ids=data.get('row_speakers',[])
 if not isinstance(ids,list) or len(ids)!=count or any(not isinstance(i,str) or i not in result for i in ids):raise ValueError('모든 자막에 등록된 화자를 지정하세요.')
 return result,ids

def tracks(folder,mix,profiles,ids,segments):
 import soundfile as sf,numpy as np
 files=[]
 # Stream each timeline track to avoid holding an entire long recording in memory.
 for ident in dict.fromkeys(ids):
  name=f'2026-10-22-speaker-{ident}.wav';files.append(name)
  with sf.SoundFile(mix) as source,sf.SoundFile(folder/name,'w',samplerate=source.samplerate,channels=1,subtype='PCM_16') as dest:
   ranges=[(round(s['start']*source.samplerate),round(s['speech_end']*source.samplerate)) for i,s in enumerate(segments) if ids[i]==ident]
   offset=0
   while True:
    block=source.read(65536,dtype='int16')
    if not len(block):break
    out=np.zeros_like(block)
    for a,b in ranges:
     lo=max(a,offset)-offset;hi=min(b,offset+len(block))-offset
     if hi>lo:out[lo:hi]=block[lo:hi]
    dest.write(out);offset+=len(block)
 return files
