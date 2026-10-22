from pathlib import Path
import importlib.util,shutil
import imageio_ffmpeg
root=Path(__file__).resolve().parent
tools=root/'2026-10-22-tools';tools.mkdir(exist_ok=True)
shutil.copy2(imageio_ffmpeg.get_ffmpeg_exe(),tools/'ffmpeg.exe')
import chatterbox
path=Path(chatterbox.__file__).parent/'models/t3/inference/alignment_stream_analyzer.py'
s=path.read_text(encoding='utf-8')
needle='alignment_repetition = self.complete and (A[self.completed_at:, :-5].max(dim=1).values.sum() > 5)'
fixed='alignment_repetition = self.complete and S > 5 and (A[self.completed_at:, :-5].max(dim=1).values.sum() > 5)'
if needle in s:path.write_text(s.replace(needle,fixed),encoding='utf-8')
elif fixed not in s:raise RuntimeError('Unexpected alignment analyzer source; setup stopped')
print('FFmpeg and known short-text compatibility fix prepared')
