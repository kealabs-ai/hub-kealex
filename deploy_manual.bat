@echo off
chcp 65001 >nul

echo === DEPLOY MANUAL KEALEX ===
echo Data: %date% %time%
echo.

REM Verificar se estamos no diretório correto
if not exist "docker-compose.yml" (
    echo [ERRO] docker-compose.yml não encontrado!
    echo Execute este script no diretório raiz do projeto
    pause
    exit /b 1
)

REM Definir variáveis
set SECRET_KEY=troque-por-uma-chave-segura-em-producao
set DATABASE_URL=mysql+pymysql://u549746795_kealex:Sally2026%%40%%21%%40@srv1078.hstgr.io:3306/u549746795_kealex
set TAG=latest

echo 1. LIMPANDO AMBIENTE
echo ====================
docker compose down 2>nul
docker system prune -f 2>nul
echo.

echo 2. CONSTRUINDO IMAGENS
echo ======================
docker compose build --no-cache
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao construir imagens
    pause
    exit /b 1
)
echo.

echo 3. SUBINDO SERVICOS
echo ===================
docker compose up -d --remove-orphans
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao subir serviços
    pause
    exit /b 1
)
echo.

echo 4. AGUARDANDO INICIALIZACAO
echo ===========================
echo Aguardando 45 segundos...
timeout /t 45 /nobreak >nul
echo.

echo 5. VERIFICANDO STATUS
echo =====================
docker compose ps
echo.

echo 6. VERIFICANDO LOGS
echo ===================
echo --- API Gateway ---
docker compose logs --tail=10 api-gateway
echo.
echo --- SVC Auth ---
docker compose logs --tail=10 svc-auth
echo.

echo 7. TESTE DE CONECTIVIDADE
echo =========================
set /a attempts=0
:test_loop
set /a attempts+=1
echo Tentativa %attempts%/10

curl -f -s http://localhost:8000/k1/lex/auth/me >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] API respondendo!
    goto test_success
)

if %attempts% geq 10 (
    echo [ERRO] API não respondeu após 10 tentativas
    echo Logs do API Gateway:
    docker compose logs api-gateway
    pause
    exit /b 1
)

timeout /t 5 /nobreak >nul
goto test_loop

:test_success
echo.

echo 8. TESTE DE LOGIN
echo =================
curl -s -X POST http://localhost:8000/k1/lex/auth/login ^
    -H "Content-Type: application/json" ^
    -d "{\"email\": \"admin@kealex.com\", \"senha\": \"admin123\"}" > temp_login.json

type temp_login.json
echo.

findstr "accessToken" temp_login.json >nul
if %errorlevel% equ 0 (
    echo [OK] Login funcionando!
) else (
    echo [ERRO] Problema no login
)

del temp_login.json 2>nul
echo.

echo 9. INFORMACOES FINAIS
echo =====================
echo API disponível em: http://localhost:8000/k1/lex/
echo Documentação: http://localhost:8000/docs
echo.
echo Containers rodando:
docker compose ps
echo.

echo === DEPLOY CONCLUIDO ===
echo.
echo Para parar os serviços:
echo   docker compose down
echo.
echo Para ver logs em tempo real:
echo   docker compose logs -f
echo.
echo Para reiniciar um serviço:
echo   docker compose restart ^<nome_do_servico^>

pause