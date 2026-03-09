@echo off
cd /d %~dp0

set URL=http://127.0.0.1:8000/

for /f "tokens=2 delims==; " %%P in ('wmic process where "name='python.exe' and commandline like '%%manage.py runserver%%'" get processid /value 2^>nul') do (
    if not "%%P"=="" taskkill /PID %%P /F >nul 2>nul
)

where py >nul 2>nul
if %errorlevel%==0 (
    start "" %URL%
    py -3 manage.py runserver
) else (
    start "" %URL%
    python manage.py runserver
)
