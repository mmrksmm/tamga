@echo off
chcp 65001 >nul
cd /d %~dp0
call .venv\Scripts\activate.bat || (echo Run start.bat once first. & pause & exit /b)
cd app
python clean_fragments.py
echo.
set /p A=Hide these fragments? (y/n): 
if /i "%A%"=="y" python clean_fragments.py --apply
pause
