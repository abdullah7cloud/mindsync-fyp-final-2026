@echo off
rem Stops any MindSync website (port 5173) or backend (port 8000) that is still running from an old folder.
rem It only closes the programs listening on those two ports. Your database and files are not touched.
echo Stopping old MindSync programs on ports 5173 and 8000...
for %%P in (5173 5174 8000) do (
  for /f "tokens=5" %%A in ('netstat -ano ^| findstr ":%%P " ^| findstr LISTENING') do (
    echo Closing process %%A on port %%P
    taskkill /F /PID %%A >nul 2>&1
  )
)
echo.
echo Done. Now double-click start-backend.bat, wait for "Application startup complete", then start-frontend.bat.
pause
