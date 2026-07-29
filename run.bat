@echo off
title SnapCam Launcher
echo Launching SnapCam Virtual Camera App...
python main.py
if errorlevel 1 (
    echo.
    echo Press any key to exit...
    pause > nul
)
