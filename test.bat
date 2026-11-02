@echo off
echo Running ACS Test Suite...
cd /d "%~dp0"
"D:\PythonEnt\python.exe" -m pytest
pause
