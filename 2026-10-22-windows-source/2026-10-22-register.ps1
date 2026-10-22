param([switch]$CheckOnly)
$ErrorActionPreference='Stop'
$key='HKCU:\Software\Classes\localvoicestudio'
$handler=Join-Path $PSScriptRoot '2026-10-22-protocol.vbs'
$command='"'+(Join-Path $env:WINDIR 'System32\wscript.exe')+'" "'+$handler+'" "%1"'
if(Test-Path -LiteralPath $key){
 $existing=(Get-Item -LiteralPath ($key+'\shell\open\command') -ErrorAction Stop).GetValue('')
 if($existing -ne $command){throw 'Another localvoicestudio association exists. It was preserved. Review the old registration before installing this version.'}
}
if($CheckOnly){Write-Output 'Protocol registration check only. No registry changes.';return}
New-Item -Path ($key+'\shell\open\command') -Force|Out-Null
Set-Item -LiteralPath $key -Value 'URL:Local Voice Studio'
New-ItemProperty -LiteralPath $key -Name 'URL Protocol' -Value '' -PropertyType String -Force|Out-Null
Set-Item -LiteralPath ($key+'\shell\open\command') -Value $command
Write-Output 'Registered localvoicestudio for this Windows user. No startup task or resident service was created.'
