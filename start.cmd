@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Please complete the first-time setup in README.md.
  pause
  exit /b 1
)
echo FINN will be available at http://127.0.0.1:8000
echo Keep this window open. Press Ctrl+C to stop.
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
