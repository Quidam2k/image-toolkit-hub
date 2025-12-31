@echo off
title Enhanced Image Grid Sorter - DEBUG MODE
echo.
echo ====================================
echo   Enhanced Image Grid Sorter
echo   DEBUG MODE - All output visible
echo ====================================
echo.
echo Starting application...
echo.

REM Change to the script directory
cd /d "%~dp0"

REM Run with python - show ALL output (no 2>nul)
python image_sorter_enhanced.py

echo.
echo Application closed
pause
