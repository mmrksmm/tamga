@echo off
chcp 65001 >nul
cd /d %~dp0
set PY=python
where py >nul 2>nul && set PY=py
%PY% --version >nul 2>nul || (echo Python not found. Install it from python.org and tick "Add python.exe to PATH". & pause & exit /b)
if not exist .venv\Scripts\python.exe %PY% -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install -q -r requirements.txt || (echo. & echo Could not install packages - send a screenshot of this window. & pause & exit /b)
cd app
echo.
echo Site: http://127.0.0.1:8000   (stop: Ctrl+C)
start "" http://127.0.0.1:8000
python -m uvicorn main:app
pause
