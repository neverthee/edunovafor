@echo off
setlocal

set "ROOT_DIR=%~dp0"
set "FRONTEND_DIR=%ROOT_DIR%frontend"

if not exist "%FRONTEND_DIR%\package.json" goto :error

if defined NODE_EXE_OVERRIDE (
  set "NODE_EXE=%NODE_EXE_OVERRIDE%"
) else (
  call :resolve_command NODE_EXE node.exe
  if not defined NODE_EXE call :resolve_command NODE_EXE node
)

if defined NPM_CMD_OVERRIDE (
  set "NPM_CMD=%NPM_CMD_OVERRIDE%"
) else (
  call :resolve_command NPM_CMD npm.cmd
  if not defined NPM_CMD call :resolve_command NPM_CMD npm
)

if not defined NODE_EXE goto :error_node
if not defined NPM_CMD goto :error_npm_cmd

if not exist "%NODE_EXE%" (
  where "%NODE_EXE%" >nul 2>nul
  if errorlevel 1 goto :error_node
)

if not exist "%NPM_CMD%" (
  where "%NPM_CMD%" >nul 2>nul
  if errorlevel 1 goto :error_npm_cmd
)

set "PATH=%~dp0frontend\node_modules\.bin;%~dp0frontend\node_modules;%PATH%"

pushd "%FRONTEND_DIR%"

if not exist node_modules (
  echo node_modules not found, installing frontend dependencies...
  call "%NPM_CMD%" install
  if errorlevel 1 goto :frontend_failed
)

if not exist node_modules\.bin\vite.cmd (
  echo vite executable not found, reinstalling frontend dependencies...
  call "%NPM_CMD%" install
  if errorlevel 1 goto :frontend_failed
)

call "%NPM_CMD%" run dev
set "EXIT_CODE=%errorlevel%"
popd
exit /b %EXIT_CODE%

:frontend_failed
set "EXIT_CODE=%errorlevel%"
popd
exit /b %EXIT_CODE%

:resolve_command
set "%~1="
for /f "delims=" %%I in ('where %~2 2^>nul') do (
  set "%~1=%%I"
  goto :eof
)
goto :eof

:error_node
echo Node executable was not found: %NODE_EXE%
exit /b 1

:error_npm_cmd
echo npm command was not found: %NPM_CMD%
exit /b 1

:error
echo Failed to start frontend. frontend\package.json was not found under: %FRONTEND_DIR%
exit /b 1
