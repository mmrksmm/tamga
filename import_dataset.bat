@echo off
chcp 65001 >nul
cd /d %~dp0
call .venv\Scripts\activate.bat || (echo Run start.bat once first. & pause & exit /b)
cd app
set /p L=Language of the dataset (kk, alt, ar, sah, zh): 
python ..\import_hf.py --lang %L%
pause
