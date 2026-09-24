@echo off
cd /d "%~dp0"
"%LOCALAPPDATA%\jeyvro-venv\Scripts\python.exe" smoke_phase4.py > smoke_phase4.out 2>&1
echo EXIT=%ERRORLEVEL% >> smoke_phase4.out
