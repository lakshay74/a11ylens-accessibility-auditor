@echo off
setlocal

set "ROOT=%~dp0"
set "PYTHON=%ROOT%backend\.venv\Scripts\python.exe"

if not exist "%PYTHON%" (
  echo Backend virtual environment not found: %PYTHON%
  echo Follow docs\LOCAL_BACKEND_SETUP.md to install the backend first.
  pause
  exit /b 1
)

powershell -NoProfile -Command "try { $health = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/health' -TimeoutSec 2; if ($health.service -eq 'A11yLens API') { exit 0 } } catch { }; exit 1" >nul 2>&1
if not errorlevel 1 (
  echo A11yLens API is already running at http://127.0.0.1:8000
  exit /b 0
)

set "APP_ENV=development"
start "A11yLens API - keep open" /D "%ROOT%backend" cmd /k ""%PYTHON%" -m uvicorn main:app --app-dir . --host 127.0.0.1 --port 8000"
echo Opened the local guidance API console. Keep it open while using the extension.
echo Wait for the API startup-complete message before requesting guidance.
echo The API is bound to 127.0.0.1 and is not exposed publicly.
