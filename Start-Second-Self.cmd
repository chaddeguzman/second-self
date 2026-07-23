@echo off
setlocal EnableExtensions EnableDelayedExpansion

title Second Self Home
cd /d "%~dp0"

set "SECOND_SELF_POWERSHELL=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
set "SECOND_SELF_BOOTSTRAP=%~dp090-system\automation\scripts\bootstrap.ps1"
set "SECOND_SELF_LAUNCHER=%~dp090-system\automation\scripts\second-self.ps1"

if not exist "%SECOND_SELF_POWERSHELL%" (
    echo Second Self could not find Windows PowerShell.
    goto :failed
)

if not exist "%SECOND_SELF_LAUNCHER%" (
    echo Second Self could not find its local launcher.
    echo Keep this file in the root of the Second Self repository.
    goto :failed
)

if not exist "%~dp0.second-self.local.json" (
    echo First-time Second Self setup is required.
    echo.
    "%SECOND_SELF_POWERSHELL%" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%SECOND_SELF_BOOTSTRAP%"
    set "SECOND_SELF_EXIT=!ERRORLEVEL!"
    if not "!SECOND_SELF_EXIT!"=="0" goto :failed
    echo.
)

echo Starting Second Self Home...
echo Your browser will open automatically. Close this window or press Ctrl+C to stop.
echo.

"%SECOND_SELF_POWERSHELL%" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%SECOND_SELF_LAUNCHER%" web %*
set "SECOND_SELF_EXIT=!ERRORLEVEL!"
if not "!SECOND_SELF_EXIT!"=="0" goto :failed

exit /b 0

:failed
if not defined SECOND_SELF_EXIT set "SECOND_SELF_EXIT=1"
echo.
echo Second Self could not start. Review the message above for details.
pause
exit /b !SECOND_SELF_EXIT!
