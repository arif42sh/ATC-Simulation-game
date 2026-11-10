@echo off
title SkyATC AI - Air Traffic Control Simulation
echo =====================================================================
echo  Starting SkyATC AI Game Simulation (CSE 3202) ...
echo =====================================================================
set "PATH=C:\Users\HP\AppData\Local\Python\bin;C:\Users\HP\AppData\Local\Python\pythoncore-3.14-64\Scripts;%PATH%"
python main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Game encountered an issue. Press any key to view details...
    pause
)

