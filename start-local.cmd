@echo off
setlocal

set "ROOT=%~dp0"
set "PYTHON=%ROOT%backend\.venv\Scripts\python.exe"

if not exist "%PYTHON%" (
  echo Backend virtual environment not found: %PYTHON%
  echo Create it and install backend\requirements.txt first.
  pause
  exit /b 1
)

where node >nul 2>&1
if errorlevel 1 (
  echo Node.js is not installed or is not on PATH.
  pause
  exit /b 1
)

set "APP_ENV=development"
set "FRONTEND_ORIGIN=http://localhost:4173"
set "API_BASE_URL=http://127.0.0.1:8000"

start "A11yLens API - keep open" cmd /k "cd /d ""%ROOT%backend"" && ""%PYTHON%"" -m uvicorn main:app --app-dir . --host 127.0.0.1 --port 8000"
start "A11yLens Web - keep open" cmd /k "cd /d ""%ROOT%web"" && node server.js"

timeout /t 5 /nobreak >nul
start "" "http://localhost:4173/"
