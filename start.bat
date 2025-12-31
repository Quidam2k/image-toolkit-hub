@echo off
title Image Toolkit
echo.
echo ====================================
echo   Image Toolkit
echo ====================================
echo.
echo Starting application...
echo.

REM Change to the script directory
cd /d "%~dp0"

REM Try to run with python, then python3, then py
python app_hub.py 2>nul
if %errorlevel% neq 0 (
    python3 app_hub.py 2>nul
    if %errorlevel% neq 0 (
        py app_hub.py 2>nul
        if %errorlevel% neq 0 (
            echo.
            echo ERROR: Could not find Python installation
            echo.
            echo Please make sure Python is installed and added to PATH
            echo Required: Python 3.7+ with tkinter and PIL/Pillow
            echo.
            echo You can install Python from: https://python.org
            echo Make sure to check "Add Python to PATH" during installation
            echo.
            pause
            exit /b 1
        )
    )
)

REM Only pause if there was an error (window closes immediately on success)
if %errorlevel% neq 0 (
    echo.
    echo Application exited with error code: %errorlevel%
    echo.
    pause
)
