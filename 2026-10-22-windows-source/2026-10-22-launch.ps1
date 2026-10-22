$ErrorActionPreference='Stop'
Set-Location -LiteralPath $PSScriptRoot
$env:PYTHONUTF8='1'
$env:TEMP=Join-Path $PSScriptRoot '2026-10-22-cache\temp'
$env:TMP=$env:TEMP
$env:OLLAMA_MODELS=Join-Path $PSScriptRoot '2026-10-22-cache\ollama-models'
$env:OLLAMA_HOST='127.0.0.1:11435'
$env:PATH=(Join-Path $PSScriptRoot '2026-10-22-tools')+';'+$env:PATH
if(!(Test-Path -LiteralPath (Join-Path $PSScriptRoot '2026-10-22-installed.txt'))){& (Join-Path $PSScriptRoot '2026-10-22-install.ps1');if(!(Test-Path -LiteralPath (Join-Path $PSScriptRoot '2026-10-22-installed.txt'))){return}}
# Refuse occupied ports; do not stop unrelated local services.
foreach($port in @(8765,11435)){
 $client=New-Object Net.Sockets.TcpClient
 $occupied=$false
 try{$occupied=$client.ConnectAsync('127.0.0.1',$port).Wait(400) -and $client.Connected}catch{$occupied=$false}finally{$client.Dispose()}
 if($occupied){throw "Port $port is occupied. Close the existing app before launching this copy."}
}
$ollama=Start-Process -FilePath (Join-Path $PSScriptRoot '2026-10-22-tools\ollama\ollama.exe') -ArgumentList 'serve' -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $env:TEMP 'ollama-output.log') -RedirectStandardError (Join-Path $env:TEMP 'ollama-error.log')
try{
 $ready=$false
 for($i=0;$i -lt 30;$i++){try{Invoke-RestMethod 'http://127.0.0.1:11435/api/tags' -TimeoutSec 2|Out-Null;$ready=$true;break}catch{Start-Sleep -Seconds 1}}
 if(!$ready){throw 'Local translation service did not start. See cache/temp/ollama-error.log'}
 Write-Host 'Open http://127.0.0.1:8765 in your browser. Keep this window open; Ctrl+C to stop.'
 & (Join-Path $PSScriptRoot '2026-10-22-runtime\Scripts\python.exe') -B (Join-Path $PSScriptRoot '2026-10-22-app.py')
 if($LASTEXITCODE){throw 'Application exited with an error.'}
}finally{if(!$ollama.HasExited){Stop-Process -Id $ollama.Id}}
