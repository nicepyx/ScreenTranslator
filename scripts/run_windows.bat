@echo off
setlocal
cd /d "%~dp0\.."

if not exist .venv (
  py -3.12 -m venv .venv >nul 2>&1
  if errorlevel 1 py -3.11 -m venv .venv >nul 2>&1
  if errorlevel 1 python -m venv .venv
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
python main.py
pause
