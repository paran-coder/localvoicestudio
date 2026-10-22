"""Local script and waveform gates; these do not certify native pronunciation."""
import re
from pathlib import Path
_recognizer = None

def synthesize(model, text, language, prompt, emotion, cfg, folder, index, cache, log,tag=''):
    import soundfile as sf
    # Use the installed model's default sampler; diagnostics never select/rewrite audio.
    wave=model.generate(text,language_id=language,audio_prompt_path=str(prompt) if prompt else None,exaggeration=emotion,cfg_weight=cfg)
    samples=wave.squeeze().cpu().numpy()
    check_audio(samples,model.sr)
    raw=folder/f'clip-{index:04}.wav';sf.write(raw,samples,model.sr)
    try:review=recognize(raw,text,language,cache)
    except Exception as exc:review={'expected':text,'review_required':True,'recognition_error':str(exc)}
    review['policy']='single_default_synthesis_no_audio_selection'
    return raw,review


def recognize(path, text, language, cache):
    import whisper, unicodedata, difflib
    global _recognizer
    if _recognizer is None:
        weights = Path(cache) / 'whisper' / 'tiny.pt'
        if not weights.is_file():
            raise RuntimeError('음성 검수용 tiny.pt가 없습니다. 설치 상태를 확인하세요.')
        _recognizer = whisper.load_model(str(weights), device='cpu')
    result = _recognizer.transcribe(str(path), language=language, fp16=False,
        verbose=None, condition_on_previous_text=False)
    def norm(value):
        return ''.join(c for c in unicodedata.normalize('NFKC', value).lower() if c.isalnum())
    expected, actual = norm(text), norm(result['text'])
    score = difflib.SequenceMatcher(None, expected, actual).ratio()
    return {'expected':text, 'recognized':result['text'], 'similarity':score,
        'review_required':score < .75 or len(actual)>max(12,len(expected)*1.5),
        'limitation':'Whisper tiny 자동 비교이며 원어민 발음 인증이 아닙니다.'}

def check_text(tokenizer, text, language):
    if language != 'ko' and re.search('[가-힣]', text):
        raise ValueError('대상 언어 대본에 한국어가 남아 있습니다.')
    ids = tokenizer.encode(text, language_id=language)
    unknown = tokenizer.tokenizer.token_to_id('[UNK]')
    if unknown is not None and unknown in ids:
        raise ValueError('발음 사전에 없는 문자가 있습니다. 대본 또는 언어 설정을 확인하세요.')

def check_audio(samples, sr, text=None):
    import numpy as np
    samples = np.asarray(samples)
    if not samples.size or not np.isfinite(samples).all():
        raise ValueError('빈 음성 또는 잘못된 샘플이 생성되었습니다.')
    if float(np.sqrt(np.mean(samples.astype(float)**2))) < 0.0001:
        raise ValueError('무음에 가까운 음성이 생성되었습니다.')

def configure_chinese():
    # Upstream passes a snapshot directory as cache_dir, creating a nested cache
    # path that exceeds Windows path limits. Use the file beside the vocabulary.
    from chatterbox.models.tokenizers import tokenizer as module
    original = module.ChineseCangjieConverter._load_cangjie_mapping
    if getattr(original, '_local_fix', False):
        return
    def load(self, model_dir=None):
        import json
        path = Path(model_dir) / 'Cangjie5_TC.json' if model_dir else None
        if path is None or not path.is_file():
            raise RuntimeError('중국어 발음 사전 Cangjie5_TC.json을 찾을 수 없습니다.')
        for entry in json.loads(path.read_text(encoding='utf-8')):
            word, code = entry.split('\t')[:2]
            self.word2cj[word] = code
            self.cj2word.setdefault(code, []).append(word)
        if not self.word2cj:
            raise RuntimeError('중국어 발음 사전이 비어 있습니다.')
    load._local_fix = True
    module.ChineseCangjieConverter._load_cangjie_mapping = load
