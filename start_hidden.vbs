' HULLAR Telegram botunu pencere göstermeden başlatır.
' Windows başlangıcına kısayolu konunca PC açılınca otomatik çalışır.
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
' Betiğin bulunduğu klasörü kullan (her PC'de çalışır)
sh.CurrentDirectory = fso.GetParentFolderName(WScript.ScriptFullName)
sh.Run "venv\Scripts\pythonw.exe -m hullar telegram", 0, False
