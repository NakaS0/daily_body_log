@echo off
rem Watch and import OMRON CSV files
cd /d %~dp0

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

%PYEXE% manage.py watch_omron_csv
