@echo off
setlocal
title EduNova Launcher

set "ROOT_DIR=%~dp0"
set "FRONTEND_SCRIPT=%ROOT_DIR%start_frontend.bat"
set "BACKEND_SCRIPT=%ROOT_DIR%start_backend.bat"
set "LOCAL_ENV_FILE=%ROOT_DIR%.env.local"

if exist "%LOCAL_ENV_FILE%" call :load_env_file "%LOCAL_ENV_FILE%"

if not exist "%FRONTEND_SCRIPT%" (
  echo [ERROR] Frontend launcher not found: %FRONTEND_SCRIPT%
  exit /b 1
)

if not exist "%BACKEND_SCRIPT%" (
  echo [ERROR] Backend launcher not found: %BACKEND_SCRIPT%
  exit /b 1
)

if defined PYTHON_EXE_OVERRIDE (
  echo [INFO] Using PYTHON_EXE_OVERRIDE=%PYTHON_EXE_OVERRIDE%
)

start "EduNova Frontend" /d "%ROOT_DIR%" cmd /k call "%FRONTEND_SCRIPT%"
start "EduNova Backend" /d "%ROOT_DIR%" cmd /k call "%BACKEND_SCRIPT%"

endlocal
exit /b 0

:load_env_file
for /f "usebackq tokens=1,* delims==" %%A in ("%~1") do (
  set "ENV_KEY=%%A"
  set "ENV_VALUE=%%B"
  call :set_env_value
)
goto :eof

:set_env_value
if not defined ENV_KEY goto :eof
if "%ENV_KEY:~0,1%"=="#" goto :eof
set "%ENV_KEY%=%ENV_VALUE%"
goto :eof
