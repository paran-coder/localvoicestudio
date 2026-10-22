$ErrorActionPreference='Stop'
trap{Add-Type -AssemblyName System.Windows.Forms;[System.Windows.Forms.MessageBox]::Show($_.Exception.Message,'Local Voice Studio')|Out-Null;break}
Set-Location -LiteralPath $PSScriptRoot
$configPath=Join-Path $PSScriptRoot '2026-10-22-environment.json'
$marker=Join-Path $PSScriptRoot '2026-10-22-installed.txt'
if(!(Test-Path -LiteralPath $marker) -or (Get-Content -LiteralPath $marker -Raw).Trim() -ne 'reuse-v1.2.0' -or !(Test-Path -LiteralPath $configPath)){& (Join-Path $PSScriptRoot '2026-10-22-install.ps1');if(!(Test-Path -LiteralPath $marker) -or (Get-Content -LiteralPath $marker -Raw).Trim() -ne 'reuse-v1.2.0'){return}}
$config=Get-Content -LiteralPath $configPath -Raw|ConvertFrom-Json
$python=$config.python;$worker=Join-Path $PSScriptRoot '2026-10-22-runtime-worker.py';$data=Join-Path $PSScriptRoot '2026-10-22-cache'
if(!(Test-Path -LiteralPath $python)){throw 'Configured Python was moved or removed. Run install.ps1 to rescan.'}
$env:PYTHONUTF8='1';$env:HF_HOME=$config.hf_home;$env:TORCH_HOME=$config.torch_home;$env:TEMP=Join-Path $data 'temp';$env:TMP=$env:TEMP
New-Item -ItemType Directory -Force -Path $env:TEMP|Out-Null
$probeSocket=New-Object Net.Sockets.TcpClient;$used=$false;try{$used=$probeSocket.ConnectAsync('127.0.0.1',8766).Wait(400) -and $probeSocket.Connected}catch{}finally{$probeSocket.Dispose()};if($used){throw 'Local engine already running on 8766. No process was stopped.'}
$ownedOllama=$null
if(!$config.ollama_external){
 $probeSocket=New-Object Net.Sockets.TcpClient;$used=$false;try{$used=$probeSocket.ConnectAsync('127.0.0.1',11435).Wait(400) -and $probeSocket.Connected}catch{}finally{$probeSocket.Dispose()};if($used){throw '11435 is occupied. No process was stopped.'}
 $env:OLLAMA_HOST='127.0.0.1:11435';$env:OLLAMA_MODELS=$config.ollama_models
 $ownedOllama=Start-Process -FilePath $config.ollama_exe -ArgumentList 'serve' -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $env:TEMP 'ollama-output.log') -RedirectStandardError (Join-Path $env:TEMP 'ollama-error.log')
}
$ready=$false
for($i=0;$i -lt 30;$i++){try{Invoke-RestMethod ($config.ollama_url+'/api/tags') -TimeoutSec 2|Out-Null;$ready=$true;break}catch{if($config.ollama_external){break};Start-Sleep -Seconds 1}}
if(!$ready){if($ownedOllama -and !$ownedOllama.HasExited){Stop-Process -Id $ownedOllama.Id};throw 'Configured Ollama is stopped. Start the existing service or rerun installer detection.'}
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$script:child=$null
$icon=New-Object System.Windows.Forms.NotifyIcon
$icon.Icon=[System.Drawing.SystemIcons]::Application
$icon.Text='Local Voice Studio'
$menu=New-Object System.Windows.Forms.ContextMenuStrip
$status=$menu.Items.Add('상태 확인')
$pair=$menu.Items.Add('웹 연결 코드')
$quit=$menu.Items.Add('테스트 엔진 종료')
$session=Join-Path $data '2026-10-22-session.json'
$status.add_Click({[System.Windows.Forms.MessageBox]::Show("Local engine: 127.0.0.1:8766`nOllama: configured service`nConfigured environment active.",'Local Voice Studio')|Out-Null})
$pair.add_Click({try{$value=Get-Content -LiteralPath $session -Raw|ConvertFrom-Json;if($value.pid -ne $script:child.Id){throw 'Session not ready'};[System.Windows.Forms.MessageBox]::Show("Connection code: $($value.code)`nEnter only in your trusted editor manual.",'Local Voice Studio')|Out-Null}catch{[System.Windows.Forms.MessageBox]::Show('Engine is starting. Try again.','Local Voice Studio')|Out-Null}})
$quit.add_Click({$answer=[System.Windows.Forms.MessageBox]::Show('Stop this test engine? Any active job will stop. Existing external Ollama stays running.','Local Voice Studio','YesNo');if($answer -eq 'Yes'){[System.Windows.Forms.Application]::ExitThread()}})
$icon.add_DoubleClick({$pair.PerformClick()})
$icon.ContextMenuStrip=$menu
$timer=New-Object System.Windows.Forms.Timer
$timer.Interval=1500
$timer.add_Tick({if($script:child.HasExited){$timer.Stop();[System.Windows.Forms.MessageBox]::Show('Test engine stopped. Check 2026-10-22-data logs.','Local Voice Studio')|Out-Null;[System.Windows.Forms.Application]::ExitThread()}})
try{
 $script:child=Start-Process -FilePath $python -ArgumentList '-B',('"'+$worker+'"') -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $data '2026-10-22-output.log') -RedirectStandardError (Join-Path $data '2026-10-22-error.log')
 $icon.Visible=$true;$timer.Start()
 [System.Windows.Forms.Application]::Run()
}finally{
 if($ownedOllama -and !$ownedOllama.HasExited){Stop-Process -Id $ownedOllama.Id}
 $timer.Stop();$timer.Dispose();$icon.Visible=$false;$icon.Dispose();$menu.Dispose()
 if($script:child -and !$script:child.HasExited){Stop-Process -Id $script:child.Id}
}
