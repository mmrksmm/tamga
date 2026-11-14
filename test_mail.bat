@echo off
chcp 65001 >nul
cd /d %~dp0
call .venv\Scripts\activate.bat || (echo Run start.bat once first. & pause & exit /b)
cd app
set /p M=Send a test letter to (your email): 
python test_mail.py %M%
pause
