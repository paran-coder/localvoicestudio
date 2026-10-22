Set shell = CreateObject("WScript.Shell")
Set fs = CreateObject("Scripting.FileSystemObject")
folder = fs.GetParentFolderName(WScript.ScriptFullName)
marker = fs.BuildPath(folder, "2026-10-22-installed.txt")
ready = False
If fs.FileExists(marker) Then
 Set stream = fs.OpenTextFile(marker, 1, False, 0)
 ready = (Trim(stream.ReadAll) = "on-demand-v1.4.0")
 stream.Close
End If
If Not fs.FileExists(fs.BuildPath(folder, "2026-10-22-environment.json")) Then
 shell.Run Chr(34) & fs.BuildPath(folder, "2026-10-22-launch.cmd") & Chr(34), 1, False
ElseIf Not ready Then
 shell.Run Chr(34) & fs.BuildPath(folder, "2026-10-22-repair.cmd") & Chr(34), 1, False
Else
 MsgBox "Local checks passed. Return to the website and click Studio Start to finish browser connection.", 64, "Local Voice Studio"
End If
