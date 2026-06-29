@echo off
chcp 65001 >nul
title HULLAR
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8

if not exist "venv\Scripts\python.exe" (
    echo [HATA] venv bulunamadi.
    pause
    exit /b 1
)

where ollama >nul 2>&1 && (
    tasklist /fi "imagename eq ollama.exe" | find /i "ollama.exe" >nul || (
        echo Ollama baslatiliyor...
        start "" /b ollama serve >nul 2>&1
        timeout /t 3 >nul
    )
)

if /i "%~1"=="telegram" goto telegram
if /i "%~1"=="tg" goto telegram

echo.
echo  ====== HULLAR ======
echo  1 = CMD sohbet
echo  2 = Telegram botu
echo.
set "mod="
set /p "mod=Secim (1/2): "
if "%mod%"=="2" goto telegram

echo.
echo HULLAR sohbet baslatiliyor...
venv\Scripts\python.exe -m hullar
goto end

:telegram
echo.
echo HULLAR Telegram botu baslatiliyor...
venv\Scripts\python.exe -m hullar telegram

:end
echo.
pause
