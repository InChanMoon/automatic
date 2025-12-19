@echo off
chcp 65001 >nul
cd /d "%~dp0"
python publisher_bot.py
pause
