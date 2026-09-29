@echo off
setlocal
cd /d "%~dp0\.."
python run_sql_file.py migrations\update_groq_models.sql
if errorlevel 1 exit /b %errorlevel%
pause