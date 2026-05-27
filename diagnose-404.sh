#!/bin/bash
# Script de diagnóstico para problemas de 404 no Kealex

echo "=== DIAGNÓSTICO KEALEX - PROBLEMA 404 ==="

echo "1. Verificando containers..."
docker ps --filter "name=svc-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
docker ps --filter "name=api-gateway" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "2. Testando health check direto..."
curl -v http://localhost:8000/health 2>&1 | head -20

echo ""
echo "3. Testando debug endpoint direto..."
curl -s http://localhost:8000/debug | jq . 2>/dev/null || curl -s http://localhost:8000/debug

echo ""
echo "4. Testando via Traefik HTTPS..."
curl -k -v https://srv1023256.hstgr.cloud/kealex/health 2>&1 | head -20

echo ""
echo "5. Testando debug via Traefik HTTPS..."
curl -k -s https://srv1023256.hstgr.cloud/kealex/debug | jq . 2>/dev/null || curl -k -s https://srv1023256.hstgr.cloud/kealex/debug

echo ""
echo "6. Verificando logs do nginx..."
docker logs --tail=20 api-gateway 2>&1 | grep -E "(error|404|upstream)"

echo ""
echo "7. Testando conectividade interna..."
docker exec api-gateway curl -s http://svc-auth:8000/health && echo " [OK] svc-auth" || echo " [ERRO] svc-auth"
docker exec api-gateway curl -s http://svc-processos:8000/health && echo " [OK] svc-processos" || echo " [ERRO] svc-processos"

echo ""
echo "8. Verificando configuração do nginx..."
docker exec api-gateway nginx -t

echo ""
echo "9. Verificando redes Docker..."
docker network ls | grep kealex
docker network inspect kealex-internal --format '{{.Name}}: {{len .Containers}} containers'

echo ""
echo "10. Verificando Traefik..."
docker ps --filter "name=traefik" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "=== COMANDOS PARA TESTAR MANUALMENTE ==="
echo "# Health check direto:"
echo "curl http://localhost:8000/health"
echo ""
echo "# Health check via Traefik:"
echo "curl -k https://srv1023256.hstgr.cloud/kealex/health"
echo ""
echo "# Debug endpoint:"
echo "curl -k https://srv1023256.hstgr.cloud/kealex/debug"
echo ""
echo "# API endpoint:"
echo "curl -k https://srv1023256.hstgr.cloud/kealex/v1/lex/auth/me"
echo ""
echo "# Logs em tempo real:"
echo "docker logs -f api-gateway"