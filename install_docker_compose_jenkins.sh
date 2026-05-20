#!/bin/bash

# Script para instalar docker-compose no Jenkins
# Execute no servidor Jenkins como root ou com sudo

echo "=== INSTALANDO DOCKER-COMPOSE PARA JENKINS ==="
echo "Data: $(date)"
echo ""

# Verificar se já existe
if command -v docker-compose &> /dev/null; then
    echo "✅ docker-compose já instalado:"
    docker-compose --version
    echo "Localização: $(which docker-compose)"
    exit 0
fi

echo "📦 Instalando docker-compose..."

# Detectar arquitetura
ARCH=$(uname -m)
case $ARCH in
    x86_64)
        COMPOSE_ARCH="x86_64"
        ;;
    aarch64|arm64)
        COMPOSE_ARCH="aarch64"
        ;;
    *)
        echo "❌ Arquitetura não suportada: $ARCH"
        exit 1
        ;;
esac

# Versão do docker-compose
COMPOSE_VERSION="v2.24.0"
COMPOSE_URL="https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-linux-${COMPOSE_ARCH}"

echo "Baixando docker-compose ${COMPOSE_VERSION} para ${COMPOSE_ARCH}..."
echo "URL: $COMPOSE_URL"

# Baixar
if curl -L "$COMPOSE_URL" -o /tmp/docker-compose; then
    echo "✅ Download concluído"
else
    echo "❌ Falha no download"
    exit 1
fi

# Instalar
sudo mv /tmp/docker-compose /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Criar links simbólicos
sudo ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose

# Verificar instalação
if command -v docker-compose &> /dev/null; then
    echo "✅ docker-compose instalado com sucesso!"
    docker-compose --version
    echo "Localização: $(which docker-compose)"
else
    echo "❌ Falha na instalação"
    exit 1
fi

# Testar com usuário jenkins
if id jenkins &> /dev/null; then
    echo ""
    echo "🧪 Testando com usuário jenkins..."
    
    if sudo -u jenkins docker-compose --version; then
        echo "✅ Usuário jenkins pode usar docker-compose"
    else
        echo "❌ Usuário jenkins não pode usar docker-compose"
    fi
    
    if sudo -u jenkins docker ps &> /dev/null; then
        echo "✅ Usuário jenkins tem acesso ao Docker"
    else
        echo "⚠️  Usuário jenkins não tem acesso ao Docker"
        echo "Execute: sudo usermod -aG docker jenkins"
    fi
fi

echo ""
echo "🎉 Instalação concluída!"
echo ""
echo "Para usar no Jenkins, adicione ao PATH ou use o caminho completo:"
echo "  /usr/local/bin/docker-compose"
echo ""
echo "Se necessário, reinicie o Jenkins:"
echo "  sudo systemctl restart jenkins"