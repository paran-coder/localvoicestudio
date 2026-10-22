Set shell = CreateObject("WScript.Shell")
Set fs = CreateObject("Scripting.FileSystemObject")
folder = fs.GetParentFolderName(WScript.ScriptFullName)
marker = fs.BuildPath(folder, "2026-10-22-installed.txt")
ready = False
If fs.FileExists(marker) Then
 Set text = fs.OpenTextFile(marker, 1, False, 0)
 ready = (Trim(text.ReadAll) = "bootstrap-web-v1.1.0")
 text.Close
End If
If Not ready Then
 shell.Run Chr(34) & fs.BuildPath(folder, "2026-10-22-launch.cmd") & Chr(34), 1, False
Else
 shell.Run "powershell.exe -NoProfile -ExecutionPolicy Bypass -File " & Chr(34) & fs.BuildPath(folder, "2026-10-22-launch.ps1") & Chr(34), 0, False
End If
