@echo off
chcp 65001 >nul
cd /d "%~dp0"
call .venv\Scripts\activate.bat
set PYTHONIOENCODING=utf-8
python collector\run.py %*
echo %* | find "--scheduled" >nul || pause
