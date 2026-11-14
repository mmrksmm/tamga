@echo off
chcp 65001 >nul
cd /d %~dp0
:menu
cls
echo ============ TAMGA ============
echo  D. DEMO: site + bot + voice + public link (recommended)
echo  1. Start the site (on this computer)
echo  2. Start the site for phones in the same Wi-Fi
echo  3. Start the Telegram bot
echo  4. Import phrasebook datasets
echo  5. Import the school list
echo  6. Install speech recognition (multilingual, 0.5 GB)
echo  7. Install Bashkir speech recognition (1.5 GB)
echo  8. Install Bashkir voice (TTS, 1 GB)
echo  9. Hide bad fragments
echo 10. Send a test e-mail
echo  0. Exit
echo ===============================
set "C="
set /p "C=Choose a number: "
if /i "%C%"=="D" start "Tamga demo" cmd /c demo.bat
if "%C%"=="1" start "Tamga site" cmd /c start.bat
if "%C%"=="2" start "Tamga site LAN" cmd /c start_lan.bat
if "%C%"=="3" start "Tamga bot" cmd /c start_bot.bat
if "%C%"=="4" call import_dataset.bat
if "%C%"=="5" call import_schools.bat
if "%C%"=="6" call install_asr.bat
if "%C%"=="7" call install_asr_ba.bat
if "%C%"=="8" call install_tts.bat
if "%C%"=="9" call clean_fragments.bat
if "%C%"=="10" call test_mail.bat
if "%C%"=="0" exit /b
goto menu
