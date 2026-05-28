#!/bin/bash
# Script para testar conexão com MySQL externo

echo "=== TESTE DE CONEXÃO MYSQL EXTERNO ==="

echo "Credenciais utilizadas:"
echo "Host: srv1078.hstgr.io"
echo "Port: 3306"
echo "Database: u549746795_kealex"
echo "User: u549746795_kealex"
echo "Password: Sally2026@!@"
echo ""

echo "1. Testando conectividade de rede..."
ping -c 3 srv1078.hstgr.io || echo "Ping falhou"

echo ""
echo "2. Testando porta MySQL..."
nc -zv srv1078.hstgr.io 3306 2>&1 || echo "Porta 3306 não acessível"

echo ""
echo "3. Testando conexão via container Python..."
if docker ps | grep -q svc-auth; then
    docker exec svc-auth python -c "
import pymysql
try:
    conn = pymysql.connect(
        host='srv1078.hstgr.io',
        port=3306,
        user='u549746795_kealex',
        password='Sally2026@!@',
        database='u549746795_kealex'
    )
    print('[OK] Conexão MySQL estabelecida com sucesso')
    cursor = conn.cursor()
    cursor.execute('SELECT VERSION()')
    version = cursor.fetchone()
    print(f'[INFO] Versão MySQL: {version[0]}')
    cursor.execute('SELECT DATABASE()')
    db = cursor.fetchone()
    print(f'[INFO] Database atual: {db[0]}')
    conn.close()
except Exception as e:
    print(f'[ERRO] Falha na conexão: {e}')
" 2>/dev/null
else
    echo "[ERRO] Container svc-auth não está rodando"
fi

echo ""
echo "4. Testando URL de conexão completa..."
echo "DATABASE_URL=mysql+pymysql://u549746795_kealex:Sally2026%40%21%40@srv1078.hstgr.io:3306/u549746795_kealex"

echo ""
echo "5. Verificando logs dos microserviços para erros de DB..."
for service in svc-auth svc-processos svc-documentos; do
    if docker ps | grep -q $service; then
        echo "--- Logs $service ---"
        docker logs --tail=5 $service 2>&1 | grep -i -E "(error|mysql|database|connection)" || echo "Sem erros relacionados ao DB"
    fi
done