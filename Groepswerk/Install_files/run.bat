:: Windows batch file to start the application.  Can be used with nssm.exe to create a Windows service
:: vindevoy - 2025-04-08
 
::@echo off
::set ENV_FILE=../../shinyboard/config/prysent.env
 
::
:: DO NOT TOUCH THE CODE BELOW
::::::::::::::::::::::::::::::
 
:: Load all the environment variables from the .env file
::for /f "usebackq tokens=1,2 delims== eol=#" %%A in ("%ENV_FILE%") do (
::    set "%%A=%%B"
::)
 
:: Create the logging directory if it does not exist.  You get an error from Python if it does not exist.
::IF NOT EXIST %SHINYBOARD_CONFIG% (
::    mkdir %SHINYBOARD_CONFIG%
::)
 
:: Check if the port is in use
setlocal enabledelayedexpansion
 
netstat -ano | find ":%SHINYBOARD_PORT%" >nul 2>&1
 
if not errorlevel 1 (
    echo Port %SHINYBOARD_PORT% is already in use.  Find another port to start this dashboard.
    pause
    exit /b 1
)
 
:: Activate python environment and start the server
CALL activate %SHINYBOARD_ENV%
 
:: Start the application with uvicorn, watching specify directories and files
uvicorn main:app ^
    --host 0.0.0.0 ^
    --port %SHINYBOARD_PORT% ^
    --app-dir=%SHINYBOARD_HOME% ^
    --reload ^
    --reload-delay=0 ^
    --reload-dir=%SHINYBOARD_ROOT% ^
    --reload-dir=%SHINYBOARD_CONFIG% ^
    --reload-dir=%SHINYBOARD_HOME% ^
    --reload-include=*.md ^
    --reload-include=*.py ^
    --reload-include=*.svg ^
    --reload-include=config.yaml ^
    --timeout-graceful-shutdown 0 ^
    --no-access-log
 
 
pause