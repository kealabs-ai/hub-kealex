@echo off
setlocal
cd /d "%~dp0\.."
echo Configure the tenant and user placeholders in migrations\insert_test_ia_config.sql first.
echo The runner reads KEALEX_DATABASE_URL from the backend .env.
pause
python run_sql_file.py migrations\insert_test_ia_config.sql
if errorlevel 1 exit /b %errorlevel%
pause