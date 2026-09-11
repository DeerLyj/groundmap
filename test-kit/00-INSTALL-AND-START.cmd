@echo off
setlocal
cd /d "%~dp0.."

if exist "%~dp0.setup-complete" goto start

echo GroundMap is preparing this computer for first use.
echo This requires an Internet connection and may request administrator approval.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1" -AutoInstallSystemTools
if errorlevel 1 goto failed

:start
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"
if errorlevel 1 goto failed
exit /b 0

:failed
echo.
echo GroundMap could not start. Review the message above, then run this file again.
pause
exit /b 1
