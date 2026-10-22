$ErrorActionPreference='Stop'
Set-Location -LiteralPath $PSScriptRoot
$path=Join-Path $PSScriptRoot '2026-10-22-environment.json'
Write-Host 'Connection repair: no package installation or model downloads. Existing files and URI changes require confirmation.'
$newConfig=$null
if(Test-Path -LiteralPath $path){
 $config=Get-Content -LiteralPath $path -Raw|ConvertFrom-Json
 if(!(Test-Path -LiteralPath $config.python) -or !(Test-Path -LiteralPath $config.ffmpeg)){throw 'Configured runtime moved. Initial setup must rescan. Nothing was changed.'}
}else{
 $lines=& (Join-Path $PSScriptRoot '2026-10-22-install.ps1') -CheckOnly
 $plan=($lines -join "`n")|ConvertFrom-Json
 if(!$plan.python -or !$plan.ffmpeg -or !$plan.ollama_model_present -or !$plan.ollama_binary){throw 'A complete compatible environment was not found. 설치 프로그램에서 설치 시작을 선택하세요. Repair installed nothing.'}
 $newConfig=[ordered]@{version='on-demand-v1.4.0';python=$plan.python;ffmpeg=$plan.ffmpeg;ollama_exe=$plan.ollama_binary;ollama_url=$plan.ollama_url;ollama_external=$plan.ollama_external;ollama_models=$plan.ollama_models;hf_home=$plan.hf_home;whisper_home=$plan.whisper_home;torch_home=$plan.torch_home}
 $newConfig|ConvertTo-Json -Depth 5|Write-Host
}
Write-Host "Create missing local config if needed, register/repair this folder's website launch link, then test an isolated engine process. No existing running engine is stopped."
if((Read-Host 'Apply these connection settings? Type YES') -cne 'YES'){return}
Set-Content -LiteralPath (Join-Path $PSScriptRoot '2026-10-22-installed.txt') -Value 'pending-v1.4.0' -Encoding Ascii
if($newConfig){$newConfig|ConvertTo-Json -Depth 5|Set-Content -LiteralPath $path -Encoding UTF8}
& (Join-Path $PSScriptRoot '2026-10-22-register.ps1') -Repair
& (Join-Path $PSScriptRoot '2026-10-22-verify-setup.ps1')
Set-Content -LiteralPath (Join-Path $PSScriptRoot '2026-10-22-installed.txt') -Value 'on-demand-v1.4.0' -Encoding Ascii
Write-Host 'Local repair verified. Final step: approve Studio Start in your browser. No packages/models were reinstalled.'
