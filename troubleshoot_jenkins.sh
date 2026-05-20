#!/bin/bash

# Script de troubleshooting para deploy do Kealex no Jenkins
# Execute este script no servidor onde o Jenkins está rodando

echo "=== TROUBLESHOOTING DEPLOY KEALEX ==="
echo "Data: $(date)"
echo ""

# 1. Verificar Docker
echo "1. VERIFICANDO DOCKER"
echo "====================="
docker --version
docker info | grep -E "(Server Version|Storage Driver|Logging Driver)"
echo ""

# 2. Verificar Docker Compose
echo "2. VERIFICANDO DOCKER COMPOSE"
echo "============================="
docker-compose --version
echo ""

# 3. Verificar espaço em disco
echo "3. VERIFICANDO ESPAÇO EM DISCO"
echo "=============================="
df -h
echo ""

# 4. Verificar containers rodando
echo "4. CONTAINERS RODANDO"
echo "===================="
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""

# 5. Verificar containers parados
echo "5. CONTAINERS PARADOS"
echo "===================="
docker ps -a --filter "status=exited" --format "table {{.Names}}\t{{.Status}}\t{{.ExitCode}}"
echo ""

# 6. Verificar imagens
echo "6. IMAGENS DOCKER"
echo "================"
docker images | grep kealex
echo ""

# 7. Verificar logs dos containers Kealex
echo "7. LOGS DOS CONTAINERS KEALEX"
echo "============================="
for container in $(docker ps --filter "name=kealex" --format "{{.Names}}"); do
    echo "--- Logs do $container ---"
    docker logs --tail=10 $container
    echo ""
done

# 8. Verificar rede Docker
echo "8. REDES DOCKER"
echo "==============="
docker network ls
echo ""

# 9. Verificar portas em uso
echo "9. PORTAS EM USO"
echo "==============="
netstat -tlnp | grep :8000 || echo "Porta 8000 não está em uso"
echo ""

# 10. Verificar variáveis de ambiente
echo "10. VARIÁVEIS DE AMBIENTE"
echo "========================"
echo "SECRET_KEY: ${SECRET_KEY:0:10}..." 
echo "DATABASE_URL: ${DATABASE_URL:0:30}..."
echo "TAG: $TAG"
echo "REGISTRY: $REGISTRY"
echo ""

# 11. Testar conectividade com banco
echo "11. TESTANDO CONECTIVIDADE"
echo "========================="
if command -v curl &> /dev/null; then
    echo "Testando localhost:8000..."
    curl -I http://localhost:8000 2>/dev/null || echo "Falha ao conectar em localhost:8000"
else
    echo "curl não disponível"
fi
echo ""

# 12. Comandos úteis para debug
echo "12. COMANDOS ÚTEIS PARA DEBUG"
echo "============================"
echo "# Ver logs em tempo real:"
echo "docker-compose -f docker-compose.prod.yml logs -f"
echo ""
echo "# Parar todos os containers:"
echo "docker-compose -f docker-compose.prod.yml down"
echo ""
echo "# Rebuild completo:"
echo "docker-compose -f docker-compose.prod.yml up --build -d"
echo ""
echo "# Limpar sistema Docker:"
echo "docker system prune -a -f"
echo ""
echo "# Verificar saúde dos containers:"
echo "docker-compose -f docker-compose.prod.yml ps"
echo ""
echo "# Entrar em um container:"
echo "docker exec -it <container_name> /bin/bash"
echo ""

# 13. Verificar se Jenkins tem permissões Docker
echo "13. PERMISSÕES DOCKER DO JENKINS"
echo "================================"
groups jenkins 2>/dev/null || echo "Usuário jenkins não encontrado"
ls -la /var/run/docker.sock
echo ""

echo "=== FIM DO TROUBLESHOOTING ==="