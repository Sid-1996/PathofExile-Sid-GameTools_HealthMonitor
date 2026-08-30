@echo off
rem Wrapper: call cleanup.ps1 with same args (e.g. cleanup.bat -All)
pwsh -NoProfile -ExecutionPolicy Bypass -File "%~dp0cleanup.ps1" %*