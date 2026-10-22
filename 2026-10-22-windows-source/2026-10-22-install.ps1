param([switch]$CheckOnly)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (![Environment]::Is64BitOperatingSystem) { throw 'Windows x64 is required.' }
if ($PSScriptRoot.StartsWith('\\')) { throw 'Extract to a local writable folder first.' }
$env:PYTHONUTF8='1'
$env:UV_CACHE_DIR=Join-Path $PSScriptRoot '2026-10-22-cache\uv'
$env:UV_PYTHON_INSTALL_DIR=Join-Path $PSScriptRoot '2026-10-22-tools\python'
$env:UV_PYTHON_BIN_DIR=Join-Path $PSScriptRoot '2026-10-22-tools\python-bin'
$env:TEMP=Join-Path $PSScriptRoot '2026-10-22-cache\temp'
$env:TMP=$env:TEMP
$env:OLLAMA_MODELS=Join-Path $PSScriptRoot '2026-10-22-cache\ollama-models'
foreach($folder in @($env:TEMP,$env:UV_CACHE_DIR,$env:UV_PYTHON_INSTALL_DIR,$env:OLLAMA_MODELS)){New-Item -ItemType Directory -Force -Path $folder | Out-Null}
$tools=Join-Path $PSScriptRoot '2026-10-22-tools'
$python=Join-Path $PSScriptRoot '2026-10-22-runtime\Scripts\python.exe'
if($CheckOnly){Write-Host "Runtime present: $(Test-Path -LiteralPath $python)";return}
Write-Host 'Local Voice Studio - Windows beta bootstrap'
Write-Host 'Downloads Python, PyTorch, FFmpeg, Ollama and gemma4:latest into this folder.'
Write-Host 'Internet and substantial free disk space required (reserve 40 GB or more).'
Write-Host 'TTS/STT weights download on first use. Check upstream model licenses before use.'
Write-Host 'No global PATH changes. No GPU driver installation. Existing local app remains unchanged.'
if((Read-Host 'Continue downloads and setup? Type YES') -cne 'YES'){return}
function Download($url,$target){if(!(Test-Path -LiteralPath $target)){Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $target};if((Get-Item -LiteralPath $target).Length -eq 0){throw "Empty download: $target"}}
function RunChecked($exe,$arguments){& $exe @arguments;if($LASTEXITCODE -ne 0){throw "Command failed: $exe (exit $LASTEXITCODE)"}}
$uvDir=Join-Path $tools 'uv'
$uv=Join-Path $uvDir 'uv.exe'
if(!(Test-Path -LiteralPath $uv)){
 $zip=Join-Path $env:TEMP 'uv.zip'
 Download 'https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-pc-windows-msvc.zip' $zip
 Expand-Archive -LiteralPath $zip -DestinationPath $uvDir -Force
}
RunChecked $uv @('python','install','3.11')
# uv python install manages its own Python regardless of project venv state.
if(!(Test-Path -LiteralPath $python)){RunChecked $uv @('venv','--python','3.11','--managed-python',(Join-Path $PSScriptRoot '2026-10-22-runtime'))}
$cuda=$null -ne (Get-Command nvidia-smi -ErrorAction SilentlyContinue)
$index=if($cuda){'https://download.pytorch.org/whl/cu128'}else{'https://download.pytorch.org/whl/cpu'}
RunChecked $uv @('pip','install','--python',$python,'torch==2.10.0','torchaudio==2.10.0','--index-url',$index)
# Lock is the known local environment. --no-deps preserves the intentional Chatterbox/torch override.
RunChecked $uv @('pip','install','--python',$python,'--no-deps','-r',(Join-Path $PSScriptRoot '2026-10-22-requirements-lock.txt'))
RunChecked $python @('-B',(Join-Path $PSScriptRoot '2026-10-22-prepare.py'))
$ollamaDir=Join-Path $tools 'ollama'
$ollama=Join-Path $ollamaDir 'ollama.exe'
if(!(Test-Path -LiteralPath $ollama)){
 $zip=Join-Path $env:TEMP 'ollama.zip'
 Download 'https://github.com/ollama/ollama/releases/latest/download/ollama-windows-amd64.zip' $zip
 Expand-Archive -LiteralPath $zip -DestinationPath $ollamaDir -Force
}
$env:OLLAMA_HOST='127.0.0.1:11435'
try{Invoke-RestMethod 'http://127.0.0.1:11435/api/tags' -TimeoutSec 2 | Out-Null;throw 'Port 11435 already in use. Stop that service before installation.'}catch{if($_.Exception.Message -like 'Port 11435*'){throw}}
$service=Start-Process -FilePath $ollama -ArgumentList 'serve' -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $env:TEMP 'ollama-install-output.log') -RedirectStandardError (Join-Path $env:TEMP 'ollama-install-error.log')
try{
 $ready=$false
 for($i=0;$i -lt 30;$i++){try{Invoke-RestMethod 'http://127.0.0.1:11435/api/tags' -TimeoutSec 2|Out-Null;$ready=$true;break}catch{Start-Sleep -Seconds 1}}
 if(!$ready){throw 'Ollama did not start.'}
 RunChecked $ollama @('pull','gemma4:latest')
}finally{if(!$service.HasExited){Stop-Process -Id $service.Id}}
Set-Content -LiteralPath (Join-Path $PSScriptRoot '2026-10-22-installed.txt') -Value 'bootstrap-web-v1.1.0' -Encoding Ascii
Write-Host 'Setup complete. Run 2026-10-22-launch.cmd. CPU mode can be very slow.'
