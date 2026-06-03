@echo off
echo Starting Taste Toronto...
start cmd /k "cd /d "%~dp0" && uvicorn backend.main:app --reload --port 8001"
timeout /t 2 >nul
start cmd /k "cd /d "%~dp0frontend" && npm run dev"
echo Both servers starting. Backend: http://localhost:8000  Frontend: http://localhost:3000
