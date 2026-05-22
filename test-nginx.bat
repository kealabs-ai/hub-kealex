@echo off
REM Test script for nginx configuration on Windows

echo Testing nginx configuration...
echo ==============================

REM Check if nginx is running
docker ps | findstr "kealex-api-gateway" > nul
if %errorlevel% equ 0 (
    echo ✓ nginx container is running
    
    REM Test health endpoint
    echo Testing health endpoint...
    curl -f http://localhost:8000/health
    if %errorlevel% equ 0 (
        echo ✓ Health endpoint is working
    ) else (
        echo ✗ Health endpoint failed
    )
    
    REM Test CORS headers
    echo Testing CORS headers...
    curl -I -X OPTIONS http://localhost:8000/v1/lex/auth 2>nul | findstr /i "access-control" > nul
    if %errorlevel% equ 0 (
        echo ✓ CORS headers are present
    ) else (
        echo ✗ CORS headers missing
    )
    
    REM Test redirect for backward compatibility
    echo Testing backward compatibility redirect...
    curl -I http://localhost:8000/auth 2>nul | findstr /i "301" > nul
    if %errorlevel% equ 0 (
        echo ✓ Backward compatibility redirect is working
    ) else (
        echo ✗ Backward compatibility redirect failed
    )
    
) else (
    echo ✗ nginx container is not running
    echo Starting containers...
    docker-compose up -d api-gateway
    timeout /t 5 /nobreak > nul
    echo Retrying tests...
    call test-nginx.bat
)

echo.
echo Nginx test completed
pause