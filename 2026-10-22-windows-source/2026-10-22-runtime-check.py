"""File-based setup checks; avoids Windows PowerShell native -c quote loss."""
import sys
if len(sys.argv)>1 and sys.argv[1]=='ffmpeg-path':
 import imageio_ffmpeg
 print(imageio_ffmpeg.get_ffmpeg_exe())
else:
 import torch,chatterbox,whisper,soundfile,yt_dlp
 print('Runtime imports OK')
