@echo off
chcp 65001 >nul
python -m pip install -r requirements.txt
if not exist .env copy .env.example .env >nul
echo Setup complete.
pause
