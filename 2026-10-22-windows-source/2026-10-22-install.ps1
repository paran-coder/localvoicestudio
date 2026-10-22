param([switch]$CheckOnly,[string]$PythonPath='')
$ErrorActionPreference='Stop'
Set-Location -LiteralPath $PSScriptRoot
if(![Environment]::Is64BitOperatingSystem){throw 'Windows x64 required'}
$env:PYTHONUTF8='1'
$cache=Join-Path $PSScriptRoot '2026-10-22-cache'
$tools=Join-Path $PSScriptRoot '2026-10-22-tools'
$probe=Join-Path $PSScriptRoot '2026-10-22-detect.py'
$candidates=@($PythonPath,(Join-Path $PSScriptRoot '2026-10-22-runtime\Scripts\python.exe'),(Join-Path (Split-Path $PSScriptRoot -Parent) '2026-10-22-Local-AI-TTS-v1.0.0\2026-10-22-runtime\Scripts\python.exe'))
$candidates+=Join-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) '2026-10-22-Local-AI-TTS-v1.0.0\2026-10-22-runtime\Scripts\python.exe'
$command=Get-Command python -ErrorAction SilentlyContinue;if($command){$candidates+=$command.Source}
$candidates+=Join-Path $env:LOCALAPPDATA 'Programs\Python\Python311\python.exe'
foreach($key in @('HKCU:\Software\Python\PythonCore\3.11\InstallPath','HKLM:\Software\Python\PythonCore\3.11\InstallPath')){if(Test-Path $key){try{$installPath=(Get-Item $key).GetValue('');if($installPath){$candidates+=Join-Path $installPath 'python.exe'}}catch{}}}

$python=$null;$base=$null;$inherit=@();$probeResults=@()
foreach($candidate in ($candidates|Where-Object{$_ -and $_ -notlike '*\WindowsApps\*' -and (Test-Path -LiteralPath $_)}|Select-Object -Unique)){
 try{$raw=& $candidate -B $probe 2>$null;if($LASTEXITCODE){continue};$found=$raw|ConvertFrom-Json;$probeResults+=$found;if($found.python311 -and !$base){$base=$found.base;$inherit=@($found.sites)};if($found.compatible){$python=$found.python;break}}catch{}
}
$ffmpeg=$null;$ff=Get-Command ffmpeg -ErrorAction SilentlyContinue;if($ff){$ffmpeg=$ff.Source}
if(!$ffmpeg -and (Test-Path -LiteralPath (Join-Path $tools 'ffmpeg.exe'))){$ffmpeg=Join-Path $tools 'ffmpeg.exe'}
if($ffmpeg){& $ffmpeg -version *> $null;if($LASTEXITCODE){$ffmpeg=$null}}
$ollamaExe=$null;$o=Get-Command ollama -ErrorAction SilentlyContinue;if($o){$ollamaExe=$o.Source}
if(!$ollamaExe -and (Test-Path -LiteralPath (Join-Path $tools 'ollama\ollama.exe'))){$ollamaExe=Join-Path $tools 'ollama\ollama.exe'}
$ollamaUrl='http://127.0.0.1:11435';$external=$false;$hasModel=$false
foreach($url in @('http://127.0.0.1:11434','http://127.0.0.1:11435')){
 try{$tags=Invoke-RestMethod "$url/api/tags" -TimeoutSec 2;if(@($tags.models.name) -contains 'gemma4:latest'){$ollamaUrl=$url;$external=$true;$hasModel=$true;break}}catch{}
}
$models=Join-Path $cache 'ollama-models'
$stores=@($env:OLLAMA_MODELS,(Join-Path $HOME '.ollama\models'),$models)|Where-Object{$_}|Select-Object -Unique
if(!$external){foreach($store in $stores){if(Test-Path -LiteralPath (Join-Path $store 'manifests\registry.ollama.ai\library\gemma4\latest')){$models=$store;$hasModel=$true;break}}}
$hf=Join-Path $cache 'huggingface';$whisper=Join-Path $cache 'whisper';$torch=Join-Path $cache 'torch'
$oldCache=Join-Path (Split-Path $PSScriptRoot -Parent) '2026-10-22-Local-AI-TTS-v1.0.0\2026-10-22-cache'
if(!(Test-Path -LiteralPath $oldCache)){$nestedCache=Join-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) '2026-10-22-Local-AI-TTS-v1.0.0\2026-10-22-cache';if(Test-Path -LiteralPath $nestedCache){$oldCache=$nestedCache}}
$hfStores=@($env:HF_HOME,(Join-Path $oldCache 'huggingface'),(Join-Path $HOME '.cache\huggingface'),$hf)|Where-Object{$_}|Select-Object -Unique
foreach($store in $hfStores){$snapshots=Join-Path $store 'hub\models--ResembleAI--chatterbox\snapshots';if(Test-Path -LiteralPath $snapshots){$complete=Get-ChildItem -LiteralPath $snapshots -Directory|Where-Object{(Test-Path -LiteralPath (Join-Path $_.FullName 't3_mtl23ls_v2.safetensors')) -and (Test-Path -LiteralPath (Join-Path $_.FullName 's3gen.pt')) -and (Test-Path -LiteralPath (Join-Path $_.FullName 've.pt')) -and (Test-Path -LiteralPath (Join-Path $_.FullName 'grapheme_mtl_merged_expanded_v1.json'))};if($complete){$hf=$store;break}}}
foreach($store in @((Join-Path $oldCache 'whisper'),(Join-Path $HOME '.cache\whisper'),$whisper)){if(Test-Path -LiteralPath (Join-Path $store 'tiny.pt')){$whisper=$store;break}}
if(Test-Path -LiteralPath (Join-Path $oldCache 'torch')){$torch=Join-Path $oldCache 'torch'}
$plan=[ordered]@{python=$python;base_python=$base;runtime_action=$(if($python){'reuse compatible existing environment (no package changes)'}elseif($base){'reuse Python 3.11; isolated venv inherits packages; install only incompatible/missing pins'}else{'download Python 3.11; isolated runtime'});ffmpeg=$ffmpeg;ffmpeg_action=$(if($ffmpeg){'reuse'}else{'install app-local FFmpeg'});ollama_binary=$ollamaExe;ollama_url=$ollamaUrl;ollama_external=$external;ollama_model_present=$hasModel;ollama_models=$models;hf_home=$hf;whisper_home=$whisper;torch_home=$torch}
$plan|ConvertTo-Json -Depth 5|Write-Output
if($CheckOnly){return}
& (Join-Path $PSScriptRoot '2026-10-22-register.ps1') -CheckOnly
if((Read-Host 'Reuse items shown above; install ONLY missing items? Type YES') -cne 'YES'){return}
New-Item -ItemType Directory -Force -Path $cache,$tools,(Join-Path $cache 'temp')|Out-Null
$env:TEMP=Join-Path $cache 'temp';$env:TMP=$env:TEMP
$env:UV_CACHE_DIR=Join-Path $cache 'uv';$env:UV_PYTHON_INSTALL_DIR=Join-Path $tools 'python';$env:UV_PYTHON_BIN_DIR=Join-Path $tools 'python-bin'
function RunChecked($exe,$argsList){& $exe @argsList;if($LASTEXITCODE){throw "Command failed: $exe"}}
function Download($url,$target){if(!(Test-Path -LiteralPath $target)){Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $target};if((Get-Item -LiteralPath $target).Length -eq 0){throw 'Empty download'}}
$uv=Join-Path $tools 'uv\uv.exe'
function EnsureUv{if(!(Test-Path -LiteralPath $uv)){$zip=Join-Path $env:TEMP 'uv.zip';Download 'https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-pc-windows-msvc.zip' $zip;Expand-Archive -LiteralPath $zip -DestinationPath (Split-Path $uv -Parent) -Force}}
if(!$python){
 EnsureUv
 if(!$base){RunChecked $uv @('python','install','3.11');$base=(& $uv python find --managed-python 3.11).Trim();if($LASTEXITCODE){throw 'Python discovery failed'}}
 $owned=Join-Path $PSScriptRoot '2026-10-22-runtime'
 if(!(Test-Path -LiteralPath (Join-Path $owned 'Scripts\python.exe'))){RunChecked $uv @('venv','--python',$base,'--system-site-packages',$owned)}
 $python=Join-Path $owned 'Scripts\python.exe'
 if($inherit.Count){[IO.File]::WriteAllLines((Join-Path $owned 'Lib\site-packages\2026-10-22-reused-sites.pth'),[string[]]@($inherit|Where-Object{Test-Path -LiteralPath $_}),(New-Object Text.UTF8Encoding $false))}
 $probeResult=(& $python -B $probe)|ConvertFrom-Json
 if($probeResult.versions.torch.Split('+')[0] -ne '2.10.0' -or $probeResult.versions.torchaudio.Split('+')[0] -ne '2.10.0'){
  $index=if(Get-Command nvidia-smi -ErrorAction SilentlyContinue){'https://download.pytorch.org/whl/cu128'}else{'https://download.pytorch.org/whl/cpu'}
  RunChecked $uv @('pip','install','--python',$python,'torch==2.10.0','torchaudio==2.10.0','--index-url',$index)
 }
 $missing=@((& $python -B $probe --missing (Join-Path $PSScriptRoot '2026-10-22-requirements-lock.txt'))|ConvertFrom-Json)
 if($missing.Count){RunChecked $uv (@('pip','install','--python',$python,'--no-deps')+$missing)}
}
# Check actual imports with all caches confined to the selected stores.
$env:HF_HOME=$hf;$env:TORCH_HOME=$torch;$env:XDG_CACHE_HOME=$cache;$previousOffline=$env:HF_HUB_OFFLINE;$env:HF_HUB_OFFLINE='1'
try{RunChecked $python @('-B','-c','import torch,chatterbox,whisper,soundfile,yt_dlp;print("Runtime imports OK")')}finally{$env:HF_HUB_OFFLINE=$previousOffline}
if(!$ffmpeg){EnsureUv;RunChecked $uv @('pip','install','--python',$python,'--target',(Join-Path $tools 'ffmpeg-package'),'imageio-ffmpeg==0.6.0');$env:PYTHONPATH=Join-Path $tools 'ffmpeg-package';$ffmpegSource=(& $python -B -c 'import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())').Trim();$env:PYTHONPATH=$null;$ffmpeg=Join-Path $tools 'ffmpeg.exe';Copy-Item -LiteralPath $ffmpegSource -Destination $ffmpeg}
if(!$external -and !$ollamaExe){$zip=Join-Path $env:TEMP 'ollama.zip';Download 'https://github.com/ollama/ollama/releases/latest/download/ollama-windows-amd64.zip' $zip;Expand-Archive -LiteralPath $zip -DestinationPath (Join-Path $tools 'ollama') -Force;$ollamaExe=Join-Path $tools 'ollama\ollama.exe'}
$service=$null
if(!$external){
 $probeSocket=New-Object Net.Sockets.TcpClient;$used=$false;try{$used=$probeSocket.ConnectAsync('127.0.0.1',11435).Wait(400) -and $probeSocket.Connected}catch{}finally{$probeSocket.Dispose()};if($used){throw '11435 is occupied. No existing service was stopped.'}
 $env:OLLAMA_HOST='127.0.0.1:11435';$env:OLLAMA_MODELS=$models
 $service=Start-Process -FilePath $ollamaExe -ArgumentList 'serve' -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $env:TEMP 'ollama-install-output.log') -RedirectStandardError (Join-Path $env:TEMP 'ollama-install-error.log')
 try{$ready=$false;for($i=0;$i -lt 30;$i++){try{$tags=Invoke-RestMethod "$ollamaUrl/api/tags" -TimeoutSec 2;$ready=$true;break}catch{Start-Sleep -Seconds 1}};if(!$ready){throw 'Ollama did not start'};if(!(@($tags.models.name) -contains 'gemma4:latest')){RunChecked $ollamaExe @('pull','gemma4:latest')}}finally{if($service -and !$service.HasExited){Stop-Process -Id $service.Id}}
}
$config=[ordered]@{version='on-demand-v1.3.0';python=$python;ffmpeg=$ffmpeg;ollama_exe=$ollamaExe;ollama_url=$ollamaUrl;ollama_external=$external;ollama_models=$models;hf_home=$hf;whisper_home=$whisper;torch_home=$torch}
$config|ConvertTo-Json -Depth 5|Set-Content -LiteralPath (Join-Path $PSScriptRoot '2026-10-22-environment.json') -Encoding UTF8
Set-Content -LiteralPath (Join-Path $PSScriptRoot '2026-10-22-installed.txt') -Value 'on-demand-v1.3.0' -Encoding Ascii
Write-Host 'Ready. Existing environments were not overwritten.'

& (Join-Path $PSScriptRoot '2026-10-22-register.ps1')
Write-Host 'Setup complete. Return to the website and click Studio Start. No background engine was started.'
