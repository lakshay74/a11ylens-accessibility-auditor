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

set "API_STATUS="
pushd "%ROOT%"
for /f "delims=" %%S in ('"%PYTHON%" -m backend.startup --host 127.0.0.1 --port 8000 --timeout 3') do set "API_STATUS=%%S"
popd

if "%API_STATUS%"=="running" (
  echo A11yLens API is already running at http://127.0.0.1:8000
  exit /b 0
)

if "%API_STATUS%"=="occupied" (
  echo Port 8000 is already in use by a service that did not identify itself as A11yLens API.
  echo Check http://127.0.0.1:8000/health in your browser. If it is not A11yLens, close the application using port 8000 and retry.
  echo To identify the listener, run: netstat -ano ^| findstr :8000
  echo Then check its PID with: tasklist /FI "PID eq PID_FROM_NETSTAT"
  pause
  exit /b 1
)

if not "%API_STATUS%"=="available" (
  echo Could not determine whether port 8000 is available. The API was not started.
  pause
  exit /b 1
)

set "APP_ENV=development"
start "A11yLens API - keep open" /D "%ROOT%backend" cmd /k ""%PYTHON%" -m uvicorn main:app --app-dir . --host 127.0.0.1 --port 8000"
echo Opened the local guidance API console. Keep it open while using the extension.
echo Wait for the API startup-complete message before requesting guidance.
echo The API is bound to 127.0.0.1 and is not exposed publicly.
