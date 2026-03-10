@echo off
rem Start Django dev server and open browser
cd /d %~dp0

set "URL=http://127.0.0.1:8000/"
set "PYEXE="

if exist ".venv\Scripts\python.exe" (
    set "PYEXE=.venv\Scripts\python.exe"
) else (
    where py >nul 2>nul
    if %errorlevel%==0 (
        set "PYEXE=py -3"
    ) else (
        set "PYEXE=python"
    )
)

for /f "tokens=2 delims==; " %%P in ('wmic process where "name='python.exe' and commandline like '%%manage.py runserver%%'" get processid /value 2^>nul') do (
    if not "%%P"=="" taskkill /PID %%P /F >nul 2>nul
)

start "" %URL%
%PYEXE% manage.py runserver
