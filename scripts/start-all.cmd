@echo off
powershell -ExecutionPolicy Bypass -NoProfile -File "%~dp0start-all.ps1" -WithFrontend
if errorlevel 1 pause
