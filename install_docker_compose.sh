#!/bin/bash

# Script para instalar Docker Compose no servidor Jenkins
# Execute como root ou com sudo

echo "=== INSTALANDO DOCKER COMPOSE ==="
echo "Data: $(date)"
echo ""

# Verificar se já está instalado
echo "1. VERIFICANDO INSTALAÇÃO ATUAL"
echo "==============================="

if command -v docker-compose &> /dev/null; then
    echo "✅ docker-compose já instalado:"
    docker-compose --version
else
    echo "❌ docker-compose não encontrado"
fi

if docker compose version &> /dev/null 2>&1; then
    echo "✅ docker compose (integrado) disponível:"
    docker compose version
else
    echo "❌ docker compose (integrado) não disponível"
fi

echo ""

# Verificar sistema
echo "2. INFORMAÇÕES DO SISTEMA"
echo "========================="
echo "Sistema: $(uname -a)"
echo "Arquitetura: $(uname -m)"
echo "Usuário: $(whoami)"
echo ""

# Instalar Docker Compose standalone
echo "3. INSTALANDO DOCKER COMPOSE STANDALONE"
echo "======================================="

# Detectar arquitetura
ARCH=$(uname -m)
case $ARCH in
    x86_64)
        ARCH="x86_64"
        ;;
    aarch64|arm64)
        ARCH="aarch64"
        ;;
    *)
        echo "❌ Arquitetura não suportada: $ARCH"
        exit 1
        ;;
esac

# Baixar e instalar
COMPOSE_VERSION="v2.24.0"
COMPOSE_URL="https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-linux-${ARCH}"

echo "Baixando Docker Compose ${COMPOSE_VERSION} para ${ARCH}..."
echo "URL: $COMPOSE_URL"

if curl -L "$COMPOSE_URL" -o /usr/local/bin/docker-compose; then
    echo "✅ Download concluído"
else
    echo "❌ Falha no download"
    exit 1
fi

# Dar permissão de execução
chmod +x /usr/local/bin/docker-compose

# Criar link simbólico
ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose

echo ""

# Verificar instalação
echo "4. VERIFICANDO INSTALAÇÃO"
echo "========================"

if command -v docker-compose &> /dev/null; then
    echo "✅ docker-compose instalado com sucesso:"
    docker-compose --version
    echo "Localização: $(which docker-compose)"
else
    echo "❌ Falha na instalação"
    exit 1
fi

echo ""

# Testar com usuário jenkins
echo "5. TESTANDO COM USUÁRIO JENKINS"
echo "==============================="

if id jenkins &> /dev/null; then
    echo "Testando como usuário jenkins..."
    sudo -u jenkins docker-compose --version
    sudo -u jenkins docker --version
    
    # Verificar grupos
    echo "Grupos do usuário jenkins:"
    groups jenkins
    
    # Verificar acesso ao Docker
    if sudo -u jenkins docker ps &> /dev/null; then
        echo "✅ Usuário jenkins tem acesso ao Docker"
    else
        echo "❌ Usuário jenkins NÃO tem acesso ao Docker"
        echo "Execute: sudo usermod -aG docker jenkins"
        echo "Depois reinicie o Jenkins"
    fi
else
    echo "⚠️  Usuário jenkins não encontrado"
fi

echo ""

# Instalar plugin Docker Compose para Jenkins (opcional)
echo "6. INSTALAÇÃO ALTERNATIVA - PLUGIN JENKINS"
echo "=========================================="
echo "Se preferir, você pode instalar o plugin Docker Compose no Jenkins:"
echo "1. Vá em 'Manage Jenkins' → 'Manage Plugins'"
echo "2. Procure por 'Docker Compose Build Step'"
echo "3. Instale o plugin"
echo ""

echo "=== INSTALAÇÃO CONCLUÍDA ==="
echo ""
echo "Comandos para testar:"
echo "  docker-compose --version"
echo "  docker compose version"
echo ""
echo "Se ainda houver problemas, reinicie o Jenkins:"
echo "  sudo systemctl restart jenkins"