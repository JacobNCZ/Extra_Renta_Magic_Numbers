@echo off
setlocal
cd /d "%~dp0"
python start_streamlit.py
if errorlevel 1 pause
endlocal
