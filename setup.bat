@echo off
cd /d "%~dp0"

echo === 1/4  GitHub workflow fayllarini joyiga qo'yish
if not exist ".github\workflows" mkdir ".github\workflows"
copy /Y "workflows\generate.yml" ".github\workflows\generate.yml" >nul
copy /Y "workflows\approve.yml"  ".github\workflows\approve.yml"  >nul

echo === 2/4  .env
if not exist .env copy .env.example .env >nul

echo === 3/4  Python muhiti
python -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip -q

echo === 4/4  Kutubxonalar
.venv\Scripts\python.exe -m pip install -q -r requirements.txt

echo.
echo ================================================================
echo  Tayyor. Endi:
echo    1) .env faylini ochib kalitlarni yozing
echo    2) .venv\Scripts\python.exe youtube_auth.py     (1 marta)
echo    3) .venv\Scripts\python.exe deploy.py           (onlayn chiqarish)
echo ================================================================
pause
