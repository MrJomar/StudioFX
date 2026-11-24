@echo off
cd /d "%~dp0"
where pythonw >nul 2>nul && (start "" pythonw StudioFX.pyw) || (python StudioFX.pyw)
