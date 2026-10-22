"""Legacy entry point: no resident tray is created."""
import ctypes
ctypes.windll.user32.MessageBoxW(None,"Use Studio Start on the website. Run launch.cmd once for setup.","Local Voice Studio",64)
