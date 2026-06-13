@echo off
echo Taste Toronto — local dev (no Docker)
echo.
echo Starting backend on http://localhost:8001
start cmd /k "cd /d "%~dp0" && uvicorn backend.main:app --reload --port 8001"
timeout /t 2 >nul
echo Starting frontend on http://localhost:3000
start cmd /k "cd /d "%~dp0frontend" && npm run dev"
echo.
echo Both servers starting.
echo   Frontend: http://localhost:3000
echo   Backend:  http://localhost:8001
echo.
echo To run with Docker instead: docker compose up --build
