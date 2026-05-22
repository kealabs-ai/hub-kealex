@echo off
REM Script de deploy manual para Hostinger (Windows)
REM Uso: deploy-hostinger.bat

echo === DEPLOY MANUAL KEALEX HOSTINGER ===

REM Configurações
set PROJECT_NAME=kealex
set COMPOSE_FILE=docker-compose.hostinger.yml

REM Verificar se arquivo existe
if not exist "%COMPOSE_FILE%" (
    echo Arquivo %COMPOSE_FILE% não encontrado!
    echo Usando docker-compose.yml como fallback...
    set COMPOSE_FILE=docker-compose.yml
)

REM Verificar .env
if not exist ".env" (
    echo Arquivo .env não encontrado!
    echo Copiando .env.example...
    copy .env.example .env
    echo ATENÇÃO: Configure SECRET_KEY no arquivo .env
)

REM Parar containers antigos
echo Parando containers antigos...
docker-compose -f %COMPOSE_FILE% -p %PROJECT_NAME% down --remove-orphans 2>nul

REM Remover containers órfãos
echo Removendo containers órfãos...
for /f %%i in ('docker ps -aq --filter "name=kealex" --filter "name=svc-" --filter "name=api-gateway" 2^>nul') do docker rm -f %%i 2>nul

REM Limpeza de imagens antigas
echo Limpando imagens antigas...
docker image prune -f --filter "until=24h"

REM Build e deploy
echo Fazendo build e deploy...
docker-compose -f %COMPOSE_FILE% -p %PROJECT_NAME% up -d --build --remove-orphans

REM Aguardar inicialização
echo Aguardando inicialização (45s)...
timeout /t 45 /nobreak >nul

REM Verificar status
echo === STATUS DOS CONTAINERS ===
docker-compose -f %COMPOSE_FILE% -p %PROJECT_NAME% ps

echo.
echo === CONTAINERS EM EXECUÇÃO ===
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" --filter "name=kealex"

REM Teste de conectividade
echo.
echo === TESTE DE CONECTIVIDADE ===
for /l %%i in (1,1,10) do (
    echo Tentativa %%i/10...
    curl -s --connect-timeout 3 --max-time 5 http://localhost:8000 >nul 2>&1
    if !errorlevel! equ 0 (
        echo ✅ Porta 8000 respondendo!
        goto :login_test
    )
    if %%i equ 10 (
        echo ❌ Porta não respondeu após 10 tentativas
        echo Verificando logs do API Gateway:
        docker-compose -f %COMPOSE_FILE% -p %PROJECT_NAME% logs --tail=20 api-gateway
        exit /b 1
    )
    timeout /t 3 /nobreak >nul
)

:login_test
REM Teste de login
echo.
echo === TESTE DE LOGIN ===
curl -s -w "%%{http_code}" --connect-timeout 5 --max-time 10 -X POST http://localhost:8000/v1/lex/auth/login -H "Content-Type: application/json" -d "{\"email\": \"admin@kealex.com\", \"senha\": \"admin123\"}" >temp_response.txt 2>nul

set /p RESPONSE=<temp_response.txt
set HTTP_CODE=%RESPONSE:~-3%
del temp_response.txt 2>nul

if "%HTTP_CODE%"=="200" (
    echo ✅ Login funcionando!
) else (
    echo ⚠️  Login retornou código: %HTTP_CODE%
)

echo.
echo === DEPLOY CONCLUÍDO ===
echo 🌐 API: http://localhost:8000/v1/lex/
echo 📚 Docs: http://localhost:8000/docs
echo 👤 Login: admin@kealex.com / admin123
echo.
echo Para ver logs: docker-compose -f %COMPOSE_FILE% -p %PROJECT_NAME% logs -f [serviço]
echo Para parar: docker-compose -f %COMPOSE_FILE% -p %PROJECT_NAME% down

pause