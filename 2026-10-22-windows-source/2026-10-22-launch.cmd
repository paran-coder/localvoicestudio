@echo off
set PYTHONUTF8=1
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp02026-10-22-launch.ps1"
pause
