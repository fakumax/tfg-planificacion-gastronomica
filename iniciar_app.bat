@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Primero instala el entorno siguiendo docs\INSTALACION.md
  pause
  exit /b 2
)
".venv\Scripts\python.exe" -m streamlit run app.py --server.address 127.0.0.1 --server.headless true
