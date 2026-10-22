param([ValidateSet('install','repair')][string]$Mode='install')
$ErrorActionPreference='Stop'
[Console]::OutputEncoding=New-Object System.Text.UTF8Encoding($false)
$OutputEncoding=[Console]::OutputEncoding
Add-Type -AssemblyName System.Windows.Forms
function Read-Host([string]$Prompt){
 $message="설정 내용을 확인하고 진행하시겠습니까?`n기존 환경은 재사용하고, 필요한 변경은 동의 후 진행합니다."
 if($Prompt -match 'Reuse items'){$message="기존 환경 검사 결과에 따라 필요한 구성 요소만 준비합니다.`n변경되는 로컬 설정은 백업하고 웹 실행 연결을 등록합니다.`n다운로드가 필요한 경우 인터넷과 저장 공간을 사용합니다.`n`n이 내용으로 설치를 진행할까요?"}
 if($Prompt -match 'Apply these'){$message="기존 설치 환경을 재사용하여 웹 연결 설정을 복구합니다.`n필요한 연결 설정을 저장하고 실행 링크를 확인합니다.`n패키지와 모델은 다운로드하지 않습니다.`n`n복구를 진행할까요?"}
 if($Prompt -match 'Update the existing'){$message="웹 실행 연결을 다음과 같이 변경하시겠습니까?`n`n기존: $existing`n`n변경: $command`n`n이전 설정은 백업됩니다."}
 $answer=[System.Windows.Forms.MessageBox]::Show($message,'Local Voice Studio - 변경 확인','YesNo','Question')
 if($answer -eq 'Yes'){return 'YES'}
 throw '사용자가 변경을 취소했습니다. 확인하지 않은 작업은 진행하지 않습니다.'
}
try{
 if($Mode -eq 'repair'){& (Join-Path $PSScriptRoot '2026-10-22-repair.ps1')}
 else{& (Join-Path $PSScriptRoot '2026-10-22-install.ps1')}
 $marker=Join-Path $PSScriptRoot '2026-10-22-installed.txt'
 if(!(Test-Path -LiteralPath $marker) -or (Get-Content -LiteralPath $marker -Raw).Trim() -ne 'on-demand-v1.4.0'){throw '설치 또는 복구 검증을 완료하지 못했습니다.'}
 exit 0
}catch{Write-Output $_.Exception.Message;exit 1}
