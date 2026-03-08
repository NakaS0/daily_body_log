@echo off
cd /d %~dp0

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 gui_app.py
) else (
    python gui_app.py
)
