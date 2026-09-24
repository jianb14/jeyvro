@echo off
cd /d "%~dp0"
"%LOCALAPPDATA%\jeyvro-venv\Scripts\python.exe" -m pytest -q > pytest.log 2>&1
echo EXIT=%ERRORLEVEL% >> pytest.log
