@echo off
chcp 65001 >nul
cd /d %~dp0
set PYTHONUTF8=1
set PY=python
where py >nul 2>nul && set PY=py
%PY% --version >nul 2>nul || (echo Python not found. Install it from python.org and tick "Add python.exe to PATH". & pause & exit /b)
if not exist .venv\Scripts\python.exe %PY% -m venv .venv
call .venv\Scripts\activate.bat
python demo.py
pause
