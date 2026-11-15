@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo === تنصيب البرنامج ===
where python >nul 2>nul || (echo لازم تنصب Python من python.org وتأشر على "Add Python to PATH" & pause & exit /b 1)
if not exist .venv python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
echo === تنصيب قارئ الصور (OCR) ===
pip install -r requirements-ocr.txt || echo !!! قارئ الصور ما تنصب، البرنامج يشتغل بدونه
python -c "import sys; sys.path.insert(0, 'collector'); import ocr; print('OCR:', 'OK' if ocr.available() else 'NOT WORKING')"
echo.
echo === تم التنصيب. الخطوة الجاية: شغّل schedule_daily.bat ===
pause
