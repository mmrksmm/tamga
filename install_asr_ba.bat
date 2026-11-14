@echo off
chcp 65001 >nul
cd /d %~dp0
call .venv\Scripts\activate.bat || (echo Run start.bat once first. & pause & exit /b)
echo.
echo This installs the Bashkir speech model (about 1.5 GB: PyTorch + the model).
echo It writes real Bashkir Cyrillic, unlike the general multilingual model.
echo.
pause
python -m pip install -r requirements-asr-ba.txt || (echo. & echo Install failed - send a screenshot of this window. & pause & exit /b)
cd app
python asr_check.py --model AigizK/bashkir-whisper-small
echo.
echo Now add this line to the .env file in the project folder:
echo     ASR_MODEL=AigizK/bashkir-whisper-small
echo Then restart start.bat.
pause
