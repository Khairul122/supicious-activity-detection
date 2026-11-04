@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" -c "import flask, pymysql, waitress" 2>nul || (
  echo Memasang kebutuhan web ke .venv ...
  ".venv\Scripts\python.exe" -m pip install -r web\requirements.txt
)
echo Pastikan Laragon sudah Start All (MySQL aktif).
echo Membuka web deteksi perilaku di http://127.0.0.1:5000
".venv\Scripts\python.exe" web\run.py --buka
pause
