@echo off
echo Starting SEFS System...

:: Start Backend in a new window
start "SEFS Backend" cmd /k "cd backend && python main.py"

:: Start Frontend in a new window
start "SEFS Frontend" cmd /k "cd frontend && npm run dev"

echo System starting...
echo Backend: http://localhost:8000
echo Frontend: http://localhost:5173
pause
