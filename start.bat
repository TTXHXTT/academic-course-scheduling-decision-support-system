@echo off
echo Starting ACS - Academic Course Scheduling Decision Support System...
cd /d "%~dp0"
"D:\PythonEnt\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
pause
