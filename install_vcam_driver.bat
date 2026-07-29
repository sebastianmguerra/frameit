@echo off
title SnapCam - Virtual Camera Driver Installer
cd /d "%~dp0"

echo =======================================================
echo    SnapCam Virtual Camera Driver Registration Tool
echo =======================================================
echo.

:: Check for Administrative privileges
net session >nul 2>&1
if %errorLevel% NEQ 0 (
    echo Requesting Administrative Privileges...
    echo Set UAC = CreateObject^("Shell.Application"^) > "%temp%\getadmin.vbs"
    echo UAC.ShellExecute "cmd.exe", "/c ""%~f0""", "", "runas", 1 >> "%temp%\getadmin.vbs"
    "%temp%\getadmin.vbs"
    del "%temp%\getadmin.vbs"
    exit /B
)

echo [1/2] Registering Unity Capture Virtual Camera...
if exist "%~dp0UnityCapture-master\Install\UnityCaptureFilter64.dll" (
    regsvr32.exe /s "%~dp0UnityCapture-master\Install\UnityCaptureFilter32.dll"
    regsvr32.exe /s "%~dp0UnityCapture-master\Install\UnityCaptureFilter64.dll"
    echo     SUCCESS: Unity Capture DirectShow filter registered!
) else (
    echo     WARNING: UnityCapture filter files not found.
)

echo.
echo [2/2] Registering OBS Virtual Camera...
if exist "C:\Program Files\obs-studio\data\obs-plugins\win-dshow\obs-virtualcam-module64.dll" (
    regsvr32.exe /i /s "C:\Program Files\obs-studio\data\obs-plugins\win-dshow\obs-virtualcam-module32.dll"
    regsvr32.exe /i /s "C:\Program Files\obs-studio\data\obs-plugins\win-dshow\obs-virtualcam-module64.dll"
    echo     SUCCESS: OBS Virtual Camera registered!
)

echo.
echo =======================================================
echo    Virtual Camera Driver setup completed!
echo    You can now return to SnapCam and click "Re-check VCam".
echo =======================================================
echo.
pause
