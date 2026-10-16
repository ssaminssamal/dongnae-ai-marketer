@echo off
chcp 65001 >nul
cd /d "%~dp0"
if exist "%USERPROFILE%\anaconda3\envs\local_ai_demo\python.exe" (
  "%USERPROFILE%\anaconda3\envs\local_ai_demo\python.exe" public_preview.py
) else (
  python public_preview.py
)
pause
