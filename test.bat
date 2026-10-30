@echo off
echo Running ACS Test Suite...
cd /d "%~dp0backend"
"D:\PythonEnt\python.exe" -m pytest
pause
