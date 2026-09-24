@echo off
cd /d "%~dp0"
"%LOCALAPPDATA%\jeyvro-venv\Scripts\python.exe" smoke_phase5.py > smoke_phase5.out 2>&1
echo EXIT=%ERRORLEVEL% >> smoke_phase5.out
