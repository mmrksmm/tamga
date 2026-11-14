@echo off
chcp 65001 >nul
cd /d %~dp0
set PY=python
where py >nul 2>nul && set PY=py
if not exist .venv\Scripts\python.exe %PY% -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install -q -r requirements.txt || (echo. & echo Could not install packages - send a screenshot of this window. & pause & exit /b)
cd app
echo.
echo Open on your phone (same Wi-Fi): http://YOUR-IPv4:8000  -- find IPv4 with the ipconfig command
ipconfig | findstr /i "IPv4"
python -m uvicorn main:app --host 0.0.0.0 --port 8000
pause
