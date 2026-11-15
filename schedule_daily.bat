@echo off
chcp 65001 >nul
cd /d "%~dp0"
rem يشغّل السحب كل يوم الساعة 10 الصبح (مع تأخير عشوائي لحد 45 دقيقة)
schtasks /Create /F /SC DAILY /ST 10:00 /TN "IraqPhonePrices" /TR "\"%~dp0run_now.bat\" --scheduled"
echo تم. البرنامج راح يشتغل كل يوم الساعة 10 الصبح والحاسبة لازم تكون شغالة.
pause
