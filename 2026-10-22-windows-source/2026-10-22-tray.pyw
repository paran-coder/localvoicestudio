"""Legacy entry point; use configured dependency-free Windows tray host."""
from pathlib import Path
import subprocess,ctypes,json
root=Path(__file__).resolve().parent
config=root/'2026-10-22-environment.json'
if not config.is_file():ctypes.windll.user32.MessageBoxW(0,'Start 2026-10-22-engine-start.vbs to inspect existing components first.','Local Voice Studio',0x40)
else:subprocess.Popen(['powershell.exe','-NoProfile','-STA','-ExecutionPolicy','Bypass','-File',str(root/'2026-10-22-launch.ps1')],creationflags=subprocess.CREATE_NO_WINDOW)
