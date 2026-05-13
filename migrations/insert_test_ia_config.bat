@echo off
echo ========================================
echo Inserindo Configuracao de IA de Teste
echo ========================================
echo.

REM Configuracoes do banco
set DB_HOST=srv1078.hstgr.io
set DB_PORT=3306
set DB_NAME=u549746795_kealex
set DB_USER=u549746795_kealex
set DB_PASS=Sally2026@!@

echo Conectando ao banco de dados...
echo.

REM Primeiro, buscar tenant_id e user_id do admin
echo Buscando tenant_id e user_id do admin...
mysql -h %DB_HOST% -P %DB_PORT% -u %DB_USER% -p%DB_PASS% %DB_NAME% -e "SELECT id as user_id, tenant_id FROM usuarios WHERE email = 'admin@kealex.com' LIMIT 1;"

echo.
echo IMPORTANTE: Copie o tenant_id e user_id acima e edite o arquivo insert_test_ia_config.sql
echo Substitua 'SEU_TENANT_ID' e 'SEU_USER_ID' pelos valores corretos
echo.
echo Pressione qualquer tecla para continuar apos editar o arquivo...
pause > nul

echo.
echo Executando script SQL...
mysql -h %DB_HOST% -P %DB_PORT% -u %DB_USER% -p%DB_PASS% %DB_NAME% < insert_test_ia_config.sql

echo.
echo ========================================
echo Script executado!
echo ========================================
pause
