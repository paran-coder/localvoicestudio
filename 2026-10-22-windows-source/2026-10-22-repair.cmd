@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp02026-10-22-repair.ps1"
if errorlevel 1 echo Connection repair did not finish. Read the error above. No automatic installation was requested.
pause
