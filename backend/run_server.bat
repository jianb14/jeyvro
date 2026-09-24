@echo off
cd /d "%~dp0"
"%LOCALAPPDATA%\jeyvro-venv\Scripts\python.exe" manage.py runserver 127.0.0.1:8000 > runserver.log 2>&1
