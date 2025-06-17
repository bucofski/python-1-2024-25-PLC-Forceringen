@echo You must run this as administrator.  If you forgot, press CTRL+C
pause
 
set APP_NAME=Forceringen
 
nssm remove %APP_NAME% confirm
pause
 
nssm install %APP_NAME% "C:\PythonApp\Forcerigen\Install_files\run.bat"
nssm set %APP_NAME% DisplayName "Forceringen"
nssm set %APP_NAME% Description "This service runs the Forceringen application."
nssm set %APP_NAME% ObjectName "DOSIM000\KWA.BT2.SERVERS" "Arcelor1"
nssm set %APP_NAME% AppExit 1 Restart
nssm start %APP_NAME%
pause