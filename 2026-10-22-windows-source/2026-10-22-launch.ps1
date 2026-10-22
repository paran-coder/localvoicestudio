$ErrorActionPreference='Stop'
Set-Location -LiteralPath $PSScriptRoot
if(!(Test-Path -LiteralPath (Join-Path $PSScriptRoot '2026-10-22-installed.txt')) -or (Get-Content -LiteralPath (Join-Path $PSScriptRoot '2026-10-22-installed.txt') -Raw).Trim() -ne 'bootstrap-web-v1.1.0'){& (Join-Path $PSScriptRoot '2026-10-22-install.ps1');if(!(Test-Path -LiteralPath (Join-Path $PSScriptRoot '2026-10-22-installed.txt')) -or (Get-Content -LiteralPath (Join-Path $PSScriptRoot '2026-10-22-installed.txt') -Raw).Trim() -ne 'bootstrap-web-v1.1.0'){return}}
Start-Process -FilePath (Join-Path $PSScriptRoot '2026-10-22-runtime\Scripts\pythonw.exe') -ArgumentList '-B',('"'+(Join-Path $PSScriptRoot '2026-10-22-tray.pyw')+'"') -WorkingDirectory $PSScriptRoot -WindowStyle Hidden
