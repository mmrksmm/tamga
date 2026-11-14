@echo off
chcp 65001 >nul
cd /d %~dp0
call .venv\Scripts\activate.bat || (echo Run start.bat once first. & pause & exit /b)
echo Installing speech recognition for automatic audio markup...
python -m pip install -r requirements-asr.txt || (echo. & echo Install failed - send a screenshot of this window. & pause & exit /b)
cd app
python asr_check.py
echo.
echo Restart start.bat - the "Automatic markup" buttons will appear on the materials page.
pause
