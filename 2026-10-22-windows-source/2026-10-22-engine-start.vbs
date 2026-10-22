Set shell = CreateObject("WScript.Shell")
Set fs = CreateObject("Scripting.FileSystemObject")
folder = fs.GetParentFolderName(WScript.ScriptFullName)
If Not fs.FileExists(fs.BuildPath(folder, "2026-10-22-environment.json")) Then
 shell.Run Chr(34) & fs.BuildPath(folder, "2026-10-22-launch.cmd") & Chr(34), 1, False
Else
 MsgBox "Return to the website and click Studio Start. No tray engine is needed.", 64, "Local Voice Studio"
End If
