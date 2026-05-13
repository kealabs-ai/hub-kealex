@echo off
echo ========================================
echo Atualizando modelos Groq descontinuados
echo ========================================
echo.

echo Executando script SQL para atualizar modelos...
echo.

REM Substitua as credenciais abaixo pelas suas
set DB_HOST=srv1078.hstgr.io
set DB_PORT=3306
set DB_USER=u549746795_kealex
set DB_PASS=Sally2026@!@
set DB_NAME=u549746795_kealex

REM Executar o script SQL
mysql -h %DB_HOST% -P %DB_PORT% -u %DB_USER% -p%DB_PASS% %DB_NAME% < update_groq_models.sql

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✓ Modelos atualizados com sucesso!
    echo.
    echo Modelos Groq atualizados:
    echo - mixtral-8x7b-32768 → llama-3.1-70b-versatile
    echo - llama2-70b-4096 → llama-3.1-70b-versatile  
    echo - gemma-7b-it → gemma2-9b-it
) else (
    echo.
    echo ✗ Erro ao executar a atualização
    echo Verifique as credenciais do banco de dados
)

echo.
pause