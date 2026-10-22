$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.IO.Compression
$compiler=Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
if(!(Test-Path -LiteralPath $compiler)){throw 'Windows .NET Framework x64 compiler is required.'}
$tempFolder=Join-Path $PSScriptRoot ('2026-10-22-installer-build-'+[Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $tempFolder|Out-Null
$zip=Join-Path $tempFolder 'payload.zip'
$stream=[IO.File]::Open($zip,[IO.FileMode]::CreateNew)
$archive=New-Object IO.Compression.ZipArchive($stream,[IO.Compression.ZipArchiveMode]::Create)
try{
 foreach($file in (Get-ChildItem -LiteralPath (Join-Path $PSScriptRoot '2026-10-22-windows-source') -File)){
  if($file.Name -match 'environment\.json|installed\.txt|\.log$'){throw 'Private state cannot be packaged.'}
  $entry=$archive.CreateEntry($file.Name,[IO.Compression.CompressionLevel]::Optimal);$input=[IO.File]::OpenRead($file.FullName);$output=$entry.Open()
  try{$input.CopyTo($output)}finally{$output.Dispose();$input.Dispose()}
 }
}finally{$archive.Dispose();$stream.Dispose()}
$exe=Join-Path $PSScriptRoot 'downloads\2026-10-22-Local-Voice-Studio-Setup-v1.4.0.exe'
if(Test-Path -LiteralPath $exe){throw 'Installer already exists. Preserve it before explicitly rebuilding.'}
& $compiler '/nologo' '/target:winexe' '/platform:x64' ('/out:'+$exe) ('/resource:'+$zip+',payload.zip') '/r:System.Windows.Forms.dll' '/r:System.Drawing.dll' '/r:System.IO.Compression.dll' (Join-Path $PSScriptRoot '2026-10-22-installer.cs')
if($LASTEXITCODE){throw 'Installer compile failed.'}
Write-Output $exe
Write-Output ('Build resource folder (move to verification archive before upload): '+$tempFolder)
