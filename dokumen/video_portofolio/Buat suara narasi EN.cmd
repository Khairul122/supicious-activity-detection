@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0buat_suara.ps1" -BerkasNaskah naskah_en.json -FolderSuara suara_en %*
pause
