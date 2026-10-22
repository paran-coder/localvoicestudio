param([string]$RequestUri='', [switch]$ValidateOnly)
$ErrorActionPreference='Stop'
function ParseLaunchUri([string]$value){
 if($value.Length -gt 2048 -or $value -match '["\r\n]'){throw 'Invalid launch URI'}
 $u=[Uri]$value
 if($u.Scheme -cne 'localvoicestudio' -or $u.Host -cne 'start' -or $u.UserInfo -or $u.Fragment -or $u.AbsolutePath -notin @('','/')){throw 'Invalid launch URI'}
 Add-Type -AssemblyName System.Web
 $q=[System.Web.HttpUtility]::ParseQueryString($u.Query)
 if($q.Count -ne 2 -or $q['nonce'] -cnotmatch '^[0-9a-f]{64}$'){throw 'Invalid launch nonce'}
 $origin=$q['origin'];$site=[Uri]$origin
 if($origin -cne $site.GetLeftPart([UriPartial]::Authority) -or $site.UserInfo -or ($site.Scheme -ne 'https' -and !($site.Scheme -eq 'http' -and $site.Host -in @('localhost','127.0.0.1')))){throw 'Invalid website origin'}
 return @{origin=$origin;nonce=$q['nonce']}
}
if($ValidateOnly){ParseLaunchUri $RequestUri|ConvertTo-Json -Compress;return}
try{
 if(!$RequestUri){throw 'Use Studio Start on the website. For initial setup run 2026-10-22-launch.cmd.'}
 $launch=ParseLaunchUri $RequestUri
 Add-Type -AssemblyName System.Windows.Forms
 $answer=[System.Windows.Forms.MessageBox]::Show("Allow this website to use the local dubbing engine?`n`n$($launch.origin)`n`nNo installation is performed. Engine exits when studio tabs are inactive and jobs finish.",'Local Voice Studio - Approve website','YesNo','Question')
 if($answer -ne 'Yes'){return}
 $configPath=Join-Path $PSScriptRoot '2026-10-22-environment.json'
 if(!(Test-Path -LiteralPath $configPath)){throw 'Initial setup is missing. 설치·복구 프로그램에서 연결 복구를 선택하세요. No package was installed by this launch.'}
 $config=Get-Content -LiteralPath $configPath -Raw|ConvertFrom-Json
 $cache=Join-Path $PSScriptRoot '2026-10-22-cache'
 $tickets=Join-Path $cache 'tickets'
 New-Item -ItemType Directory -Force -Path $tickets,(Join-Path $cache 'temp')|Out-Null
 $mutex=New-Object System.Threading.Mutex($false,'Local\LocalVoiceStudioOnDemand8766')
 $held=$false;$child=$null;$ownedOllama=$null
 try{
  try{$held=$mutex.WaitOne(30000)}catch [System.Threading.AbandonedMutexException]{$held=$true}
  if(!$held){throw 'Another engine launch is in progress. Try again.'}
  $running=$false
  try{$health=Invoke-RestMethod 'http://127.0.0.1:8766/health' -TimeoutSec 2;$running=$true}catch{}
  if($running -and ($health.service -ne 'local-voice-bridge' -or $health.protocol -ne 2)){throw 'An older engine is running on 8766. Close its tray engine first. It was not stopped.'}
  $sha=[System.Security.Cryptography.SHA256]::Create()
  try{$installId=([BitConverter]::ToString($sha.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($PSScriptRoot.ToLowerInvariant())))).Replace('-','').ToLowerInvariant()}finally{$sha.Dispose()}
  if($running -and $health.installation -ne $installId){throw 'Engine belongs to another install folder. Disconnect its studio tabs and wait for that engine to exit.'}
  # Grant is written only by the approved local launcher and consumed once by the matching origin.
  $ticket=Join-Path $tickets ($launch.nonce+'.json')
  @{origin=$launch.origin;created=[DateTimeOffset]::UtcNow.ToUnixTimeSeconds()}|ConvertTo-Json -Compress|Set-Content -LiteralPath $ticket -Encoding UTF8
  if($running){return}
  $env:PYTHONUTF8='1';$env:TEMP=Join-Path $cache 'temp';$env:TMP=$env:TEMP
  if(!$config.ollama_external){
   $socket=New-Object Net.Sockets.TcpClient
   try{$occupied=$socket.ConnectAsync('127.0.0.1',11435).Wait(400) -and $socket.Connected}catch{$occupied=$false}finally{$socket.Dispose()}
   if($occupied){throw '11435 is occupied. Existing process was preserved.'}
   $env:OLLAMA_HOST='127.0.0.1:11435';$env:OLLAMA_MODELS=$config.ollama_models
   $ownedOllama=Start-Process -FilePath $config.ollama_exe -ArgumentList 'serve' -WindowStyle Hidden -PassThru
  }
  $ready=$false
  for($i=0;$i -lt 30;$i++){
   try{Invoke-RestMethod ($config.ollama_url+'/api/tags') -TimeoutSec 2|Out-Null;$ready=$true;break}catch{if($config.ollama_external){break};Start-Sleep -Seconds 1}
  }
  if(!$ready -and $config.ollama_external -and (Test-Path -LiteralPath $config.ollama_exe)){
   $serviceUri=[Uri]$config.ollama_url
   if($serviceUri.Host -notin @('127.0.0.1','localhost')){throw 'Configured Ollama must be local.'}
   $env:OLLAMA_HOST=$serviceUri.Authority
   # Reuse the normal user model store. Do not replace it with this package's empty store.
   if(Test-Path Env:OLLAMA_MODELS){Remove-Item Env:OLLAMA_MODELS}
   $ownedOllama=Start-Process -FilePath $config.ollama_exe -ArgumentList 'serve' -WindowStyle Hidden -PassThru
   for($i=0;$i -lt 30;$i++){try{Invoke-RestMethod ($config.ollama_url+'/api/tags') -TimeoutSec 2|Out-Null;$ready=$true;break}catch{Start-Sleep -Seconds 1}}
  }
  if(!$ready){throw 'Configured Ollama could not be started. Check the local service. Nothing was reinstalled.'}
  $worker=Join-Path $PSScriptRoot '2026-10-22-runtime-worker.py'
  $child=Start-Process -FilePath $config.python -ArgumentList '-B',('"'+$worker+'"') -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $cache '2026-10-22-output.log') -RedirectStandardError (Join-Path $cache '2026-10-22-error.log')
  $ready=$false
  for($i=0;$i -lt 45;$i++){
   if($child.HasExited){throw 'Engine failed to start. Check cache/2026-10-22-error.log.'}
   try{$health=Invoke-RestMethod 'http://127.0.0.1:8766/health' -TimeoutSec 1;if($health.protocol -eq 2){$ready=$true;break}}catch{}
   Start-Sleep -Seconds 1
  }
  if(!$ready){throw 'Engine startup timed out.'}
  $mutex.ReleaseMutex();$held=$false
  # No UI event loop or resident tray. Wait solely to clean up the Ollama process owned by this launch.
  $child.WaitForExit()
 }finally{
  if($held){$mutex.ReleaseMutex()};$mutex.Dispose()
  if($child -and !$child.HasExited){Stop-Process -Id $child.Id}
  if($ownedOllama -and !$ownedOllama.HasExited){Stop-Process -Id $ownedOllama.Id}
 }
}catch{
 Add-Type -AssemblyName System.Windows.Forms
 [System.Windows.Forms.MessageBox]::Show($_.Exception.Message,'Local Voice Studio - Start failed')|Out-Null
}
