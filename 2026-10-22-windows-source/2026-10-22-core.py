"""Validation and timeline helpers; no model dependencies."""
import math
from urllib.parse import urlparse
LANGUAGES={"ko":"한국어","en":"영어","es":"스페인어","de":"독일어","ja":"일본어","fr":"프랑스어","zh":"중국어","ar":"아랍어","da":"덴마크어","el":"그리스어","fi":"핀란드어","he":"히브리어","hi":"힌디어","it":"이탈리아어","ms":"말레이어","nl":"네덜란드어","no":"노르웨이어","pl":"폴란드어","pt":"포르투갈어","ru":"러시아어","sv":"스웨덴어","sw":"스와힐리어","tr":"튀르키예어"}
def validate(rows):
 if not rows or len(rows)>1000:raise ValueError("1~1000개 구간을 입력하세요.")
 result=[];previous=0
 for row in rows:
  if len(row)!=3:raise ValueError("시작, 종료, 문장 형식이 필요합니다.")
  a,b=float(row[0]),float(row[1]);t=str(row[2]).strip()
  if not all(map(math.isfinite,[a,b])) or a<previous or b<=a or b>14400:raise ValueError("구간은 겹치지 않는 0~14400초 범위여야 합니다.")
  if not t or len(t)>500:raise ValueError("구간별 문장은 1~500자여야 합니다. 긴 문장은 나누세요.")
  result.append([a,b,t]);previous=b
 return result
def stamp(t):
 ms=round(t*1000);s,ms=divmod(ms,1000);m,s=divmod(s,60);h,m=divmod(m,60)
 return f"{h:02}:{m:02}:{s:02},{ms:03}"
def srt(rows):
 return "\n\n".join(f"{i}\n{stamp(a)} --> {stamp(b)}\n{t}" for i,(a,b,t) in enumerate(validate(rows),1))+"\n"
def youtube_url(url):
 u=urlparse(url)
 return u.scheme=="https" and u.hostname in {"youtube.com","www.youtube.com","m.youtube.com","youtu.be"} and not u.username and not u.password and u.port in (None,443)
def tempo(ratio):
 parts=[]
 while ratio>2:parts.append("atempo=2");ratio/=2
 while ratio<0.5:parts.append("atempo=0.5");ratio/=0.5
 parts.append(f"atempo={ratio:g}")
 return ",".join(parts)


# Only remove recognized sound/stage labels; names and ordinary bracketed words survive.
def clean_speech(text):
 import re
 notes=r'music|bgm|sniff|snort|sneeze|sneez|nostril|laugh|chuckl|sigh|sob|cough|applause|음악|콧방귀|훌쩍|기침|웃음|한숨|재채기|박수|흐느낌'
 def replace(match):
  label=match.group(0)[1:-1]
  return ' ' if re.search(notes,label,re.I) else match.group(0)
 result=re.sub(r'\[[^\[\]]{1,120}\]|\([^()]{1,120}\)|【[^【】]{1,120}】',replace,str(text))
 result=re.sub(r'\s+',' ',result).strip()
 return result if any(ch.isalnum() for ch in result) else ''

def plan_span(a,b,duration,previous_end,timed=True):
 if duration<0 or not math.isfinite(duration):raise ValueError('잘못된 음성 길이')
 slot=b-a
 if slot<=0:raise ValueError('구간 종료는 시작보다 커야 합니다.')
 if timed:
  if duration>slot*1.15+.001:raise ValueError('음성이 자막 시간보다 깁니다. 문장을 줄이거나 구간을 늘려 주세요. 시간 맞춤을 해제하면 연속 음성으로 생성할 수 있습니다.')
  start=a;speed=min(1.15,max(1.0,duration/slot))
  speech_end=start+duration/speed;end=start+max(slot,duration/speed)
 else:
  start=previous_end;speed=1.0;speech_end=start+duration;end=speech_end
 return {'start':start,'end':end,'speech_end':speech_end,'speed':speed,'shift':max(0,start-a) if timed else 0,'padding':max(0,end-speech_end)}
