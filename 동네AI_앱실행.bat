@echo off
chcp 65001 >nul
cd /d "%~dp0"
if exist "%USERPROFILE%\anaconda3\envs\local_ai_demo\python.exe" (
  "%USERPROFILE%\anaconda3\envs\local_ai_demo\python.exe" launch_app.py
) else (
  python launch_app.py
)
pause
