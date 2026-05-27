#!/bin/bash
# Script para verificar se o Traefik está funcionando corretamente

echo "=== VERIFICAÇÃO DO TRAEFIK EXISTENTE ==="

# Verificar se a rede easypanel existe
echo "1. Verificando rede easypanel..."
if docker network ls | grep -q easypanel; then
    echo "✓ Rede easypanel encontrada"
    docker network inspect easypanel --format '{{.Name}}: {{.Driver}}'
else
    echo "✗ Rede easypanel não encontrada"
    echo "Criando rede easypanel..."
    docker network create easypanel
fi

# Verificar se o Traefik está rodando
echo ""
echo "2. Verificando container Traefik..."
if docker ps | grep -q traefik; then
    echo "✓ Traefik está rodando"
    docker ps --filter "name=traefik" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
else
    echo "✗ Traefik não está rodando"
    echo "Verificando containers parados..."
    docker ps -a --filter "name=traefik" --format "table {{.Names}}\t{{.Status}}"
fi

# Verificar portas do Traefik
echo ""
echo "3. Verificando portas do Traefik..."
netstat -tlnp | grep -E ":(80|443|8080)" || echo "Nenhuma porta padrão do Traefik encontrada"

# Verificar logs do Traefik (se estiver rodando)
echo ""
echo "4. Últimos logs do Traefik..."
if docker ps | grep -q traefik; then
    TRAEFIK_CONTAINER=$(docker ps --filter "name=traefik" --format "{{.Names}}" | head -1)
    echo "Container: $TRAEFIK_CONTAINER"
    docker logs --tail=10 "$TRAEFIK_CONTAINER" 2>/dev/null || echo "Não foi possível acessar os logs"
else
    echo "Traefik não está rodando"
fi

echo ""
echo "=== CONFIGURAÇÃO RECOMENDADA ==="
echo "Se o Traefik não estiver rodando, execute:"
echo "docker run -d \\"
echo "  --name traefik \\"
echo "  --restart unless-stopped \\"
echo "  -p 80:80 -p 443:443 -p 8080:8080 \\"
echo "  -v /var/run/docker.sock:/var/run/docker.sock \\"
echo "  --network easypanel \\"
echo "  traefik:v2.10 \\"
echo "  --api.dashboard=true \\"
echo "  --api.insecure=true \\"
echo "  --providers.docker=true \\"
echo "  --providers.docker.exposedbydefault=false \\"
echo "  --entrypoints.web.address=:80 \\"
echo "  --entrypoints.websecure.address=:443"

echo ""
echo "=== TESTE DO KEALEX ==="
echo "Após o deploy do Kealex, teste:"
echo "curl -I https://srv1023256.hstgr.cloud/kealex/health"
echo "curl https://srv1023256.hstgr.cloud/kealex/v1/lex/"