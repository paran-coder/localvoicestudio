param([switch]$CheckOnly)
$ErrorActionPreference='Stop'
$config=Get-Content -LiteralPath (Join-Path $PSScriptRoot '2026-10-22-environment.json') -Raw|ConvertFrom-Json
if(!(Test-Path -LiteralPath $config.python) -or !(Test-Path -LiteralPath $config.ffmpeg)){throw 'Configured Python or FFmpeg is missing. Run connection repair or initial setup.'}
$key='HKCU:\Software\Classes\localvoicestudio'
$expected='"'+(Join-Path $env:WINDIR 'System32\wscript.exe')+'" "'+(Join-Path $PSScriptRoot '2026-10-22-protocol.vbs')+'" "%1"'
if(!(Test-Path -LiteralPath ($key+'\shell\open\command')) -or (Get-Item -LiteralPath ($key+'\shell\open\command')).GetValue('') -cne $expected){throw 'Website launch association is missing or points to another folder. Run connection repair.'}
if((Get-Item -LiteralPath $key).GetValue('URL Protocol',$null) -eq $null){throw 'URL Protocol flag is missing. Run connection repair.'}
if($CheckOnly){Write-Output 'PASS: configuration paths and exact URI command. No process started.';return}
& (Join-Path $PSScriptRoot '2026-10-22-verify-engine.ps1') -EngineRoot $PSScriptRoot
Write-Host 'URI association and local engine checks passed. Browser connection still requires Studio Start.'
