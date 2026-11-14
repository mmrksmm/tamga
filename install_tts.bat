@echo off
chcp 65001 >nul
cd /d %~dp0
call .venv\Scripts\activate.bat || (echo Run start.bat once first. & pause & exit /b)
echo Installing the Bashkir voice (about 1 GB of libraries, takes a few minutes)...
python -m pip install -r requirements-tts.txt || (echo. & echo Install failed - send a screenshot of this window. & pause & exit /b)
cd app
python tts_check.py
echo.
echo If you heard the phrase - restart start.bat, the site will now speak Bashkir.
pause
