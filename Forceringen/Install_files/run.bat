call activate am2412_tovy_server

:: Check if the port is in use
setlocal enabledelayedexpansion
 
netstat -ano | find ":8000" >nul 2>&1
 
if not errorlevel 1 (
    echo Port "8000" is already in use.  Find another port to start this dashboard.
    pause
    exit /b 1
)
 
:: Start the application with uvicorn, watching specify directories and files
uvicorn main:app ^
    --host 0.0.0.0 ^
    --port "8000" ^
    --app-dir="C:\PythonApp\Forceringen\ui" ^
    --no-access-log
  
pause