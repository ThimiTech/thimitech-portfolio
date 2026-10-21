@echo off
rem Thimi Tech OS - one-click dev launcher for Windows (double-click this file).
rem Sets up on first run, then opens Backend, Frontend and Celery in their own windows.
setlocal
title Thimi Tech OS launcher
cd /d "%~dp0"
rem UTF-8 for Python output (console email backend prints Nepali / em-dash text)
set PYTHONUTF8=1

echo.
echo  ==============================================
echo    Thimi Tech OS - starting backend + frontend
echo  ==============================================
echo.

rem ---------------- Backend setup ----------------
cd backend

if not exist .env (
  copy .env.example .env >nul
  echo [setup] Created backend\.env from .env.example - edit DB_* there if the database step fails.
)

if exist .venv\Scripts\python.exe goto venv_ready
echo [setup] Creating Python virtual environment ^(needs Python 3.12+^)...
where uv >nul 2>nul
if errorlevel 1 goto venv_with_py
uv venv --python 3.13 .venv || goto fail
goto venv_ready
:venv_with_py
py -3.13 -m venv .venv 2>nul || py -3.12 -m venv .venv 2>nul || python -m venv .venv || goto fail
:venv_ready

echo [setup] Syncing Python packages...
where uv >nul 2>nul
if errorlevel 1 (
  .venv\Scripts\python.exe -m pip install -q -r requirements.txt || goto fail
) else (
  uv pip install -q --python .venv -r requirements.txt || goto fail
)

.venv\Scripts\python.exe dev_check.py db
set DBSTATE=%errorlevel%
if "%DBSTATE%"=="1" goto fail

echo [setup] Applying database migrations...
.venv\Scripts\python.exe manage.py migrate --noinput || goto fail

if not "%DBSTATE%"=="3" goto db_ready
echo [setup] Fresh database - creating admin and loading demo data...
set DJANGO_SUPERUSER_PASSWORD=admin12345
.venv\Scripts\python.exe manage.py createsuperuser --noinput --username admin --email admin@thimitech.com
.venv\Scripts\python.exe seed_dev.py || goto fail
:db_ready

rem ---------------- Redis (Celery broker) ----------------
where docker >nul 2>nul
if errorlevel 1 goto redis_check
docker start thimi-redis >nul 2>nul || docker run -d --name thimi-redis --restart unless-stopped -p 6379:6379 redis:7-alpine >nul 2>nul
:redis_check
set CELERY=0
.venv\Scripts\python.exe dev_check.py redis && set CELERY=1
if "%CELERY%"=="0" (
  echo [info] Redis not reachable - background jobs will run inline instead of in Celery.
  set CELERY_TASK_ALWAYS_EAGER=True
)

rem ---------------- Start backend + Celery ----------------
call :port_busy 8000
if not errorlevel 1 (
  echo [ok] Backend already running on :8000 - leaving it as is.
  goto frontend
)
start "Thimi Backend :8000" /D "%CD%" cmd /k .venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
if "%CELERY%"=="1" (
  start "Thimi Celery worker" /D "%CD%" cmd /k .venv\Scripts\python.exe -m celery -A config worker --pool=solo -l info
  start "Thimi Celery beat" /D "%CD%" cmd /k .venv\Scripts\python.exe -m celery -A config beat -l info
)

rem ---------------- Frontend ----------------
:frontend
cd ..\frontend
where npm >nul 2>nul
if errorlevel 1 (
  echo [error] Node.js / npm not found. Install Node 20.19+ from https://nodejs.org and run again.
  goto fail
)
if not exist node_modules (
  echo [setup] Installing frontend packages - first run only...
  call npm install || goto fail
)
call :port_busy 5173
if not errorlevel 1 (
  echo [ok] Frontend already running on :5173 - leaving it as is.
) else (
  start "Thimi Frontend :5173" /D "%CD%" cmd /k npm run dev
)

echo.
echo [wait] Opening the browser in a few seconds...
timeout /t 6 /nobreak >nul
start "" http://localhost:5173

echo.
echo  Website     http://localhost:5173
echo  Workspace   http://localhost:5173/app
echo  API docs    http://127.0.0.1:8000/api/docs/
echo  Django admin http://127.0.0.1:8000/admin/
echo.
echo  Admin login  admin@thimitech.com / admin12345
echo  Demo logins  hr@ / manager@ / sita@thimitech.com  -  password Thimi@12345
echo.
echo  Servers run in their own windows - close those windows to stop them.
echo.
pause
exit /b 0

:port_busy
rem errorlevel 0 when something is LISTENING on port %1
netstat -ano | findstr /R /C:":%1 .*LISTENING" >nul
exit /b %errorlevel%

:fail
echo.
echo [error] Startup failed - see the message above.
pause
exit /b 1
