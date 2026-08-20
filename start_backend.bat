@echo off
setlocal

set "ROOT_DIR=%~dp0"
set "LOCAL_ENV_FILE=%ROOT_DIR%.env.local"
if exist "%LOCAL_ENV_FILE%" call :load_env_file "%LOCAL_ENV_FILE%"

set "PYTHON_EXE=python"
if defined PYTHON_EXE_OVERRIDE set "PYTHON_EXE=%PYTHON_EXE_OVERRIDE%"
call :trim_wrapping_quotes PYTHON_EXE
call :resolve_python_exe "%PYTHON_EXE%"
if errorlevel 1 goto :error_python
set "PYTHON_EXE=%RESOLVED_PYTHON_EXE%"
for %%I in ("%PYTHON_EXE%") do set "CONDA_ENV_DIR=%%~dpI"

set PYTHONNOUSERSITE=1
if defined CONDA_ENV_DIR set "PATH=%CONDA_ENV_DIR%;%CONDA_ENV_DIR%Scripts;%CONDA_ENV_DIR%Library\bin;%PATH%"

if not exist "%ROOT_DIR%backend\main.py" goto :error

for /f "usebackq delims=" %%P in (`powershell -NoProfile -Command "$pythonExe = $env:PYTHON_EXE; Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -and $_.CommandLine -match 'backend\\main\.py' -and $_.CommandLine.IndexOf($pythonExe, [System.StringComparison]::OrdinalIgnoreCase) -ge 0 } | Select-Object -ExpandProperty ProcessId"`) do (
  if not "%%P"=="" (
    echo Stopping existing backend process %%P...
    taskkill /PID %%P /F >nul 2>nul
  )
)
powershell -NoProfile -Command "Start-Sleep -Seconds 1" >nul 2>nul

pushd "%ROOT_DIR%"
"%PYTHON_EXE%" backend\main.py
set "EXIT_CODE=%errorlevel%"
popd
exit /b %EXIT_CODE%

:error_python
echo Failed to start backend. Python executable was not found: %PYTHON_EXE%
exit /b 1

:error
echo Failed to start backend. backend\main.py was not found under: %ROOT_DIR%
exit /b 1

:load_env_file
for /f "usebackq tokens=1,* delims==" %%A in ("%~1") do (
  set "ENV_KEY=%%A"
  set "ENV_VALUE=%%B"
  call :set_env_value
)
goto :eof

:trim_wrapping_quotes
setlocal EnableDelayedExpansion
set "RAW_VALUE=!%~1!"
if defined RAW_VALUE if "!RAW_VALUE:~0,1!"=="^"" if "!RAW_VALUE:~-1!"=="^"" set "RAW_VALUE=!RAW_VALUE:~1,-1!"
endlocal & set "%~1=%RAW_VALUE%"
goto :eof

:resolve_python_exe
set "RESOLVED_PYTHON_EXE="
set "PYTHON_CANDIDATE=%~1"
for /f "usebackq delims=" %%P in (`powershell -NoProfile -Command "$candidate = $env:PYTHON_CANDIDATE; if (-not $candidate) { exit 1 }; if (Test-Path -LiteralPath $candidate) { (Resolve-Path -LiteralPath $candidate).Path; exit 0 }; $command = Get-Command $candidate -ErrorAction SilentlyContinue | Select-Object -First 1; if ($command -and $command.Source) { $command.Source; exit 0 }; exit 1"`) do (
  set "RESOLVED_PYTHON_EXE=%%P"
)
if not defined RESOLVED_PYTHON_EXE exit /b 1
exit /b 0

:set_env_value
if not defined ENV_KEY goto :eof
if "%ENV_KEY:~0,1%"=="#" goto :eof
set "%ENV_KEY%=%ENV_VALUE%"
goto :eof
