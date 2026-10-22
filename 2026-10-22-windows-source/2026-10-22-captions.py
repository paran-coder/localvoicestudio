"""Caption boundaries from source word offsets; never from translated text."""
import re,json

def parse_json3(data,clean_speech):
    cues=[]
    for event in data.get('events',[]):
        segs=event.get('segs',[])
        if ''.join(s.get('utf8','') for s in segs).strip():cues.append(event)
    tokens=[]
    for ci,event in enumerate(cues):
        start=float(event['tStartMs'])/1000
        duration=event.get('dDurationMs')
        end=(float(event['tStartMs'])+float(duration if duration else 1000))/1000
        if ci+1<len(cues):end=min(end,float(cues[ci+1]['tStartMs'])/1000)
        precise=any('tOffsetMs' in s for s in event['segs'])
        for seg in event['segs']:
            raw=seg.get('utf8','');text=re.sub(r'^\s*>>\s*','',raw).strip()
            if not text:continue
            t=(float(event['tStartMs'])+float(seg.get('tOffsetMs',0)))/1000
            item={'start':t,'end':end,'text':text,'cue':ci,'precise':precise,
                  'speaker':bool(seg.get('isSpeakerChange')) or raw.lstrip().startswith('>>')}
            if tokens and tokens[-1]['cue']==ci and tokens[-1]['start']==t and not item['speaker']:
                tokens[-1]['text']+=' '+text
            else:tokens.append(item)
    for i,item in enumerate(tokens[:-1]):item['end']=min(item['end'],tokens[i+1]['start'])
    terminal=lambda text:bool(re.search(r'[.!?。！？][\"\u201d\u2019\)\]]*$',text))
    # Preserve complete source cues. Split only a complete prefix from a trailing
    # continuation; splitting every '?' creates unusably short interjections.
    for ci in range(len(cues)):
        lexical=[t for t in tokens if t['cue']==ci and clean_speech(t['text'])]
        if not lexical:continue
        boundaries=[t for t in lexical if terminal(t['text'])]
        if boundaries:boundaries[-1]['boundary']=True
    rows=[];pending=[];continuation_cue=None
    def flush():
        nonlocal continuation_cue
        if pending:
            a=pending[0]['start'];b=pending[-1]['end']
            if b>a:rows.append([a,b,' '.join(t['text'] for t in pending)])
            pending.clear()
        continuation_cue=None
    previous=None
    for item in tokens:
        gap=item['start']-(previous['start'] if previous and previous['precise'] else previous['end']) if previous else 0
        note=not clean_speech(item['text'])
        if pending and (item['speaker'] or note or (previous and item['cue']!=previous['cue'] and gap>1.6) or item['end']-pending[0]['start']>15):flush()
        if pending and previous and item['cue']!=previous['cue']:continuation_cue=item['cue']
        pending.append(item)
        if note or item.get('boundary') or (continuation_cue==item['cue'] and terminal(item['text'])):flush()
        previous=item
    flush()
    return rows,{'raw_cues':len(cues),'word_tokens':len(tokens),'sentence_rows':len(rows),
        'automatic_caption_hint':any('acAsrConf' in s for e in cues for s in e['segs']),
        'timing_basis':'YouTube cue starts and supplied word offsets; cue ends are display bounds, not forced-aligned speech ends',
        'limits':'Sentence grouping is heuristic. Source ASR spelling and speaker identity can still be wrong.'}

def batches(rows,limit=8,characters=1000):
    batch=[];size=0
    for item in rows:
        if batch and (len(batch)>=limit or size+len(item['text'])>characters):yield batch;batch=[];size=0
        batch.append(item);size+=len(item['text'])
    if batch:yield batch

def translations(response,expected):
    text=response.strip()
    if text.startswith('```'):text=re.sub(r'^```(?:json)?\s*|\s*```$','',text).strip()
    value=json.loads(text)
    items=value.get('translations') if isinstance(value,dict) else None
    if not isinstance(items,list):raise ValueError('번역 응답에 translations 배열이 없습니다.')
    wanted={r['id'] for r in expected};out={}
    for item in items:
        number=item.get('id');text=item.get('text')
        if type(number) is not int or number not in wanted or number in out or not isinstance(text,str) or not text.strip():raise ValueError('번역 구간 번호/문장이 잘못되었거나 중복됐습니다.')
        out[number]=text.strip()
    if set(out)!=wanted:raise ValueError('번역에서 빠진 구간이 있습니다.')
    return out
