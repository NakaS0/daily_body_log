@echo off
cd /d %~dp0

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 manage.py watch_omron_csv
) else (
    python manage.py watch_omron_csv
)
