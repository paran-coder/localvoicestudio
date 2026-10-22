Set shell = CreateObject("WScript.Shell")
Set fs = CreateObject("Scripting.FileSystemObject")
If WScript.Arguments.Count <> 1 Then WScript.Quit 1
uri = WScript.Arguments(0)
If Len(uri) > 2048 Or InStr(uri, Chr(34)) > 0 Or InStr(uri, vbCr) > 0 Or InStr(uri, vbLf) > 0 Then WScript.Quit 1
script = fs.BuildPath(fs.GetParentFolderName(WScript.ScriptFullName), "2026-10-22-launch.ps1")
shell.Run "powershell.exe -NoProfile -STA -ExecutionPolicy Bypass -File " & Chr(34) & script & Chr(34) & " -RequestUri " & Chr(34) & uri & Chr(34), 0, False
