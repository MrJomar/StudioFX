@echo off
cd /d "%~dp0"
echo Instalando dependencias de StudioFX...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install faster-whisper
echo.
where ffmpeg >nul 2>nul || echo AVISO: no encuentro ffmpeg. Instalalo y agregalo al PATH.
echo Listo. Ya puedes abrir StudioFX.bat
pause
