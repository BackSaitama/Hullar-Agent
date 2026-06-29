@echo off
chcp 65001 >nul
title HULLAR Kapat
echo HULLAR botu kapatiliyor...
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -in 'python.exe','pythonw.exe' -and $_.CommandLine -like '*hullar*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
echo HULLAR kapatildi.
timeout /t 2 >nul
