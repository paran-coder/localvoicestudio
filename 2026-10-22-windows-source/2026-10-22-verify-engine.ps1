param([string]$EngineRoot=$PSScriptRoot)
$ErrorActionPreference='Stop'
$config=Get-Content -LiteralPath (Join-Path $EngineRoot '2026-10-22-environment.json') -Raw|ConvertFrom-Json
$cache=Join-Path $EngineRoot '2026-10-22-cache';$tickets=Join-Path $cache 'tickets'
New-Item -ItemType Directory -Path $tickets -Force|Out-Null
$listener=[Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback,0);$listener.Start();$port=$listener.LocalEndpoint.Port;$listener.Stop()
$previousPort=$env:VOICE_BRIDGE_PORT;$previousOffline=$env:HF_HUB_OFFLINE;$child=$null
try{
 $env:VOICE_BRIDGE_PORT=[string]$port;$env:PYTHONUTF8='1';$env:HF_HUB_OFFLINE='1'
 $child=Start-Process -FilePath $config.python -ArgumentList '-B',('"'+(Join-Path $EngineRoot '2026-10-22-runtime-worker.py')+'"') -WorkingDirectory $EngineRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $cache '2026-10-22-setup-output.log') -RedirectStandardError (Join-Path $cache '2026-10-22-setup-error.log')
 $base="http://127.0.0.1:$port";$ready=$false
 for($i=0;$i -lt 60;$i++){
  if($child.HasExited){throw 'Engine startup failed. Inspect cache/2026-10-22-setup-error.log.'}
  try{$health=Invoke-RestMethod ($base+'/health') -TimeoutSec 1;if($health.service -eq 'local-voice-bridge' -and $health.protocol -eq 2){$ready=$true;break}}catch{}
  Start-Sleep -Seconds 1
 }
 if(!$ready){throw 'Engine startup check timed out.'}
 $nonce=([Guid]::NewGuid().ToString('N')+[Guid]::NewGuid().ToString('N'))
 $origin='http://127.0.0.1:17891'
 @{origin=$origin;created=[DateTimeOffset]::UtcNow.ToUnixTimeSeconds();purpose='setup'}|ConvertTo-Json -Compress|Set-Content -LiteralPath (Join-Path $tickets ($nonce+'.json')) -Encoding UTF8
 $pair=Invoke-RestMethod ($base+'/connect') -Method Post -Headers @{Origin=$origin} -ContentType 'application/json' -Body (@{nonce=$nonce}|ConvertTo-Json -Compress) -TimeoutSec 5
 $headers=@{Origin=$origin;'X-App-Token'=$pair.token}
 $status=Invoke-RestMethod ($base+'/status') -Headers $headers -TimeoutSec 5
 if(!$status.python){throw 'Authenticated status response is invalid.'}
 Invoke-RestMethod ($base+'/lease') -Method Post -Headers $headers -ContentType 'application/json' -Body '{}' -TimeoutSec 5|Out-Null
 Invoke-RestMethod ($base+'/release') -Method Post -Headers $headers -ContentType 'application/json' -Body '{}' -TimeoutSec 5|Out-Null
 @{stage='local-ready';local_verified=$true;browser_verified=$false;checked_at=[DateTimeOffset]::UtcNow.ToString('o');version='1.4.0'}|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $cache '2026-10-22-readiness.json') -Encoding UTF8
 Write-Host 'Engine checks passed: startup and authenticated connection. This standalone diagnostic does not verify URI registration. Browser activation is NOT verified yet. Return to the website and click Studio Start.'
}finally{
 if($child -and !$child.HasExited){Stop-Process -Id $child.Id}
 $env:VOICE_BRIDGE_PORT=$previousPort;$env:HF_HUB_OFFLINE=$previousOffline
}
