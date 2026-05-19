@echo off
echo ========================================
echo Kealex API - Testes Automatizados
echo ========================================
echo.

REM Verificar se Newman está instalado
newman --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Newman não encontrado. Instalando...
    npm install -g newman
    if %ERRORLEVEL% NEQ 0 (
        echo ❌ Erro ao instalar Newman. Instale manualmente: npm install -g newman
        pause
        exit /b 1
    )
)

echo ✅ Newman encontrado
echo.

REM Verificar se o sistema está rodando
echo 🔍 Verificando se o sistema está rodando...
curl -s http://localhost:8000/auth/login >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Sistema não está rodando em http://localhost:8000
    echo 💡 Execute: docker compose up --build
    pause
    exit /b 1
)

echo ✅ Sistema está rodando
echo.

REM Executar testes básicos
echo 🧪 Executando testes básicos de processos...
newman run "Kealex-Processos-API.postman_collection.json" ^
    -e "Kealex-Environment.postman_environment.json" ^
    --delay-request 1000 ^
    --timeout-request 10000 ^
    --reporters cli,json ^
    --reporter-json-export "results-basic.json"

if %ERRORLEVEL% EQU 0 (
    echo ✅ Testes básicos concluídos com sucesso
) else (
    echo ❌ Alguns testes básicos falharam
)

echo.

REM Executar testes avançados
echo 🚀 Executando testes avançados...
newman run "Kealex-Testes-Avancados.postman_collection.json" ^
    -e "Kealex-Environment.postman_environment.json" ^
    --delay-request 500 ^
    --timeout-request 15000 ^
    --reporters cli,json ^
    --reporter-json-export "results-advanced.json"

if %ERRORLEVEL% EQU 0 (
    echo ✅ Testes avançados concluídos com sucesso
) else (
    echo ❌ Alguns testes avançados falharam
)

echo.
echo 📊 Relatórios gerados:
echo - results-basic.json
echo - results-advanced.json
echo.
echo 🎉 Testes concluídos!
pause