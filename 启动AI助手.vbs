Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")

' 获取当前目录
strPath = FSO.GetParentFolderName(WScript.ScriptFullName)

' 关闭占用8005端口的进程
WshShell.Run "cmd /c for /f ""tokens=5"" %a in ('netstat -ano ^| findstr ""8005""') do taskkill /F /PID %a 2>nul", 0, True

' 启动服务器（隐藏窗口）
WshShell.Run "cmd /c cd /d """ & strPath & """ && python main.py --port 8005", 0, False

' 等待服务器启动
WScript.Sleep 10000

' 打开浏览器（只打开一次）
WshShell.Run "http://localhost:8005", 1, False

' 提示
MsgBox "b1t-AI Server Started!" & vbCrLf & vbCrLf & "http://localhost:8005", 64, "b1t-AI"

Set WshShell = Nothing
Set FSO = Nothing
