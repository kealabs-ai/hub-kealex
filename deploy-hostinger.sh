#!/bin/bash

# Script de deploy manual para Hostinger
# Uso: ./deploy-hostinger.sh

set -e

echo "=== DEPLOY MANUAL KEALEX HOSTINGER ==="

# Configurações
PROJECT_NAME="kealex"
COMPOSE_FILE="docker-compose.hostinger.yml"

# Verificar se arquivo existe
if [ ! -f "$COMPOSE_FILE" ]; then
    echo "Arquivo $COMPOSE_FILE não encontrado!"
    echo "Usando docker-compose.yml como fallback..."
    COMPOSE_FILE="docker-compose.yml"
fi

# Verificar .env
if [ ! -f ".env" ]; then
    echo "Arquivo .env não encontrado!"
    echo "Copiando .env.example..."
    cp .env.example .env
    echo "ATENÇÃO: Configure SECRET_KEY no arquivo .env"
fi

# Parar containers antigos
echo "Parando containers antigos..."
docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME down --remove-orphans 2>/dev/null || true

# Remover containers órfãos
echo "Removendo containers órfãos..."
docker ps -aq --filter "name=kealex" --filter "name=svc-" --filter "name=api-gateway" | xargs -r docker rm -f 2>/dev/null || true

# Limpeza de imagens antigas
echo "Limpando imagens antigas..."
docker image prune -f --filter "until=24h" || true

# Build e deploy
echo "Fazendo build e deploy..."
docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME up -d --build --remove-orphans

# Aguardar inicialização
echo "Aguardando inicialização (45s)..."
sleep 45

# Verificar status
echo "=== STATUS DOS CONTAINERS ==="
docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME ps

echo ""
echo "=== CONTAINERS EM EXECUÇÃO ==="
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" --filter "name=kealex"

# Teste de conectividade
echo ""
echo "=== TESTE DE CONECTIVIDADE ==="
for i in {1..10}; do
    echo "Tentativa $i/10..."
    
    if curl -s --connect-timeout 3 --max-time 5 http://localhost:8000 >/dev/null 2>&1; then
        echo "✅ Porta 8000 respondendo!"
        break
    elif [ $i -eq 10 ]; then
        echo "❌ Porta não respondeu após 10 tentativas"
        echo "Verificando logs do API Gateway:"
        docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME logs --tail=20 api-gateway
        exit 1
    else
        sleep 3
    fi
done

# Teste de login
echo ""
echo "=== TESTE DE LOGIN ==="
RESPONSE=$(curl -s -w "%{http_code}" --connect-timeout 5 --max-time 10 \
    -X POST http://localhost:8000/v1/lex/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email": "admin@kealex.com", "senha": "admin123"}' 2>/dev/null || echo "000")

HTTP_CODE="${RESPONSE: -3}"

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Login funcionando!"
else
    echo "⚠️  Login retornou código: $HTTP_CODE"
fi

echo ""
echo "=== DEPLOY CONCLUÍDO ==="
echo "🌐 API: http://localhost:8000/v1/lex/"
echo "📚 Docs: http://localhost:8000/docs"
echo "👤 Login: admin@kealex.com / admin123"
echo ""
echo "Para ver logs: docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME logs -f [serviço]"
echo "Para parar: docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME down"