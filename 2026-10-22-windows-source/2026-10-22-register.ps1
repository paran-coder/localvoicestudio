param([switch]$CheckOnly,[switch]$Repair)
$ErrorActionPreference='Stop'
$key='HKCU:\Software\Classes\localvoicestudio'
$handler=Join-Path $PSScriptRoot '2026-10-22-protocol.vbs'
$command='"'+(Join-Path $env:WINDIR 'System32\wscript.exe')+'" "'+$handler+'" "%1"'
if(Test-Path -LiteralPath $key){
 $existing=(Get-Item -LiteralPath ($key+'\shell\open\command') -ErrorAction Stop).GetValue('')
 if($existing -ne $command){
  if(!$Repair -or $existing -notmatch '2026-10-22-protocol\.vbs'){throw 'A different launch association exists. It was preserved. Use connection repair to review a recognized older installation.'}
  if(!$CheckOnly){
   Write-Host "Existing launch command: $existing"
   Write-Host "Proposed launch command: $command"
   if((Read-Host 'Update the existing Local Voice Studio launch link? Type YES') -cne 'YES'){throw 'Launch link update canceled. Existing link preserved.'}
   $backup=Join-Path $PSScriptRoot '2026-10-22-cache';New-Item -ItemType Directory -Force -Path $backup|Out-Null
   @{command=$existing;url_protocol=(Get-Item -LiteralPath $key).GetValue('URL Protocol',$null)}|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $backup ('2026-10-22-protocol-backup-'+[DateTime]::Now.ToString('yyyyMMdd-HHmmss-fff')+'.json')) -Encoding UTF8
  }
 }
}
if($CheckOnly){Write-Output 'Protocol registration check only. No registry changes.';return}
New-Item -Path ($key+'\shell\open\command') -Force|Out-Null
Set-Item -LiteralPath $key -Value 'URL:Local Voice Studio'
New-ItemProperty -LiteralPath $key -Name 'URL Protocol' -Value '' -PropertyType String -Force|Out-Null
Set-Item -LiteralPath ($key+'\shell\open\command') -Value $command
Write-Output 'Registered localvoicestudio for this Windows user. No startup task or resident service was created.'
