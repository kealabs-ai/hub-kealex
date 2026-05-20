#!/bin/bash

# Script de deploy manual do Kealex
# Use este script para testar o deploy localmente antes do Jenkins

set -e  # Parar em caso de erro

echo "=== DEPLOY MANUAL KEALEX ==="
echo "Data: $(date)"
echo ""

# Verificar se estamos no diretório correto
if [ ! -f "docker-compose.yml" ]; then
    echo "[ERRO] docker-compose.yml não encontrado!"
    echo "Execute este script no diretório raiz do projeto"
    exit 1
fi

# Definir variáveis
export SECRET_KEY="${SECRET_KEY:-troque-por-uma-chave-segura-em-producao}"
export DATABASE_URL="${DATABASE_URL:-mysql+pymysql://u549746795_kealex:Sally2026%40%21%40@srv1078.hstgr.io:3306/u549746795_kealex}"
export TAG="${TAG:-latest}"

echo "1. LIMPANDO AMBIENTE"
echo "===================="
docker compose down || true
docker system prune -f || true
echo ""

echo "2. CONSTRUINDO IMAGENS"
echo "====================="
docker compose build --no-cache
echo ""

echo "3. SUBINDO SERVICOS"
echo "=================="
docker compose up -d --remove-orphans
echo ""

echo "4. AGUARDANDO INICIALIZACAO"
echo "=========================="
echo "Aguardando 45 segundos..."
sleep 45
echo ""

echo "5. VERIFICANDO STATUS"
echo "===================="
docker compose ps
echo ""

echo "6. VERIFICANDO LOGS"
echo "=================="
echo "--- API Gateway ---"
docker compose logs --tail=10 api-gateway
echo ""
echo "--- SVC Auth ---"
docker compose logs --tail=10 svc-auth
echo ""

echo "7. TESTE DE CONECTIVIDADE"
echo "========================"
for i in {1..10}; do
    echo "Tentativa $i/10"
    if curl -f -s http://localhost:8000/v1/lex/auth/me >/dev/null 2>&1; then
        echo "[OK] API respondendo!"
        break
    elif [ $i -eq 10 ]; then
        echo "[ERRO] API não respondeu após 10 tentativas"
        echo "Logs do API Gateway:"
        docker compose logs api-gateway
        exit 1
    else
        sleep 5
    fi
done
echo ""

echo "8. TESTE DE LOGIN"
echo "================"
RESPONSE=$(curl -s -w "%{http_code}" -X POST http://localhost:8000/v1/lex/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email": "admin@kealex.com", "senha": "admin123"}')

if echo "$RESPONSE" | grep -q "200"; then
    echo "[OK] Login funcionando!"
    echo "Resposta: $RESPONSE"
else
    echo "[ERRO] Problema no login:"
    echo "$RESPONSE"
fi
echo ""

echo "9. INFORMACOES FINAIS"
echo "===================="
echo "API disponível em: http://localhost:8000/v1/lex/"
echo "Documentação: http://localhost:8000/docs"
echo ""
echo "Containers rodando:"
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
echo ""

echo "=== DEPLOY CONCLUIDO ==="
echo ""
echo "Para parar os serviços:"
echo "  docker compose down"
echo ""
echo "Para ver logs em tempo real:"
echo "  docker compose logs -f"
echo ""
echo "Para reiniciar um serviço:"
echo "  docker compose restart <nome_do_servico>"