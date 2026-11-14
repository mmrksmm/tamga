@echo off
chcp 65001 >nul
cd /d %~dp0
call .venv\Scripts\activate.bat || (echo Run start.bat once first. & pause & exit /b)
python -m pip install -q -r requirements.txt || (echo. & echo Could not install packages - send a screenshot of this window. & pause & exit /b)
cd app
echo Telegram bot is running (stop: Ctrl+C). The site must be started separately with start.bat.
python bot.py
pause
