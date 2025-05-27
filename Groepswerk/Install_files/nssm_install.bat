@echo You must run this as administrator.  If you forgot, press CTRL+C
pause
 
set DASHBOARD_NAME=demo_dashboard
 
nssm remove %DASHBOARD_NAME% confirm
pause
 
nssm install %DASHBOARD_NAME% "C:\shiny-board\_config\demo_dashboard\run.bat"
nssm set %DASHBOARD_NAME% DisplayName "Demo Dashboard"
nssm set %DASHBOARD_NAME% Description "This service runs the demo dashboard application."
nssm set %DASHBOARD_NAME% ObjectName "DOMAIN\USERNAME" "PASSWORD"
nssm set %DASHBOARD_NAME% AppExit 1 Restart
nssm start %DASHBOARD_NAME%
pause