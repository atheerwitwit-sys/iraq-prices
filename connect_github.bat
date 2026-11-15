@echo off
cd /d "%~dp0"
echo Connecting to GitHub... a browser window may open to sign in to GitHub.
call :main > git_log.txt 2>&1
type git_log.txt
echo.
echo ===== DONE. Send a screenshot of this window =====
pause
exit /b

:main
where git
if errorlevel 1 (
  echo ERROR: Git not found. Install it from git-scm.com
  exit /b 1
)
if not exist .git git init
git checkout -B main
git config user.name "iraq-prices"
git config user.email "iraq-prices@users.noreply.github.com"
git remote remove origin 2>nul
git remote add origin https://github.com/atheerwitwit-sys/iraq-prices.git
git add -A
git commit -m "Iraq phone and router prices"
git pull --rebase --allow-unrelated-histories -X ours origin main
git push -u origin main
exit /b 0
