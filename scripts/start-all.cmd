@echo off
powershell -ExecutionPolicy Bypass -NoProfile -File "%~dp0start-all.ps1"
if errorlevel 1 pause
