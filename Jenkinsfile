pipeline {
    agent any

    environment {
        IMAGE_PREFIX = "kealex"
        TAG = "latest"
        SECRET_KEY = "${env.SECRET_KEY ?: 'fallback-chave-segura'}"
        DATABASE_URL = "${env.DATABASE_URL ?: 'mysql+pymysql://user:pass@host/db'}"
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Verify Traefik') {
            steps {
                script {
                    echo "=== VERIFICAÇÃO DO TRAEFIK EXISTENTE ==="
                    
                    sh """
                        # Verificar se Traefik está rodando
                        if docker ps | grep -q traefik; then
                            echo "✓ Traefik encontrado e rodando"
                            TRAEFIK_CONTAINER=\$(docker ps --filter "name=traefik" --format "{{.Names}}" | head -1)
                            echo "Container Traefik: \$TRAEFIK_CONTAINER"
                            docker ps --filter "name=traefik" --format "table {{.Names}}\\t{{.Status}}\\t{{.Ports}}"
                        else
                            echo "✗ Traefik não encontrado rodando"
                            echo "Verificando containers parados..."
                            docker ps -a --filter "name=traefik" --format "table {{.Names}}\\t{{.Status}}" || echo "Nenhum container Traefik encontrado"
                            exit 1
                        fi
                        
                        # Verificar rede easypanel
                        if docker network ls | grep -q easypanel; then
                            echo "✓ Rede easypanel encontrada"
                            docker network inspect easypanel --format '{{.Name}}: {{.Driver}}' || true
                        else
                            echo "✗ Rede easypanel não encontrada"
                            echo "Criando rede easypanel..."
                            docker network create easypanel
                            echo "✓ Rede easypanel criada"
                        fi
                        
                        # Verificar portas do Traefik
                        echo ""
                        echo "Portas do Traefik:"
                        netstat -tlnp | grep -E ":(80|443|8080)" || echo "Nenhuma porta padrão encontrada"
                        
                        # Testar conectividade do Traefik
                        echo ""
                        echo "Testando Traefik dashboard..."
                        curl -f http://localhost:8080/api/rawdata 2>/dev/null && echo "✓ Traefik API acessível" || echo "⚠ Traefik API não acessível (normal se dashboard desabilitado)"
                    """
                }
            }
        }

        stage('Build Images') {
            steps {
                script {
                    echo "=== BUILD DE IMAGENS ==="
                    
                    def services = [
                        'svc-auth', 'svc-processos', 'svc-documentos',
                        'svc-financeiro', 'svc-prazos', 'svc-usuarios',
                        'svc-clientes', 'svc-configuracoes', 'svc-escritorios',
                        'api-gateway'
                    ]
                    
                    services.each { svc ->
                        sh "docker build -t kealex/${svc}:${TAG} ./${svc} || exit 1"
                    }
                }
            }
        }

        stage('Deploy Containers') {
            steps {
                script {
                    echo "=== DEPLOY COM DOCKER COMPOSE ==="
                    
                    sh """
                        export SECRET_KEY='${SECRET_KEY}'
                        export DATABASE_URL='${DATABASE_URL}'
                        
                        # Verificar se docker-compose existe, se não, baixar
                        if ! command -v docker-compose >/dev/null 2>&1; then
                            echo "Baixando docker-compose..."
                            curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-linux-x86_64" -o /tmp/docker-compose
                            chmod +x /tmp/docker-compose
                            # Usar diretamente do /tmp se não conseguir mover para /usr/local/bin
                            if sudo mv /tmp/docker-compose /usr/local/bin/docker-compose 2>/dev/null; then
                                echo "docker-compose instalado em /usr/local/bin"
                                COMPOSE_CMD="docker-compose"
                            else
                                echo "Usando docker-compose do /tmp"
                                COMPOSE_CMD="/tmp/docker-compose"
                            fi
                        else
                            echo "docker-compose já disponível"
                            COMPOSE_CMD="docker-compose"
                        fi
                        
                        echo "Usando comando: \$COMPOSE_CMD"
                        \$COMPOSE_CMD --version
                        
                        # Verificar novamente se Traefik está rodando antes do deploy
                        if ! docker ps | grep -q traefik; then
                            echo "ERRO: Traefik não está rodando. Deploy cancelado."
                            exit 1
                        fi
                        
                        # Deploy usando docker-compose principal (produção)
                        echo "Fazendo deploy em produção com Traefik..."
                        \$COMPOSE_CMD --project-name kealex down --remove-orphans || true
                        \$COMPOSE_CMD --project-name kealex up -d --build --remove-orphans
                    """

                    echo "Aguardando inicialização dos microserviços..."
                    sleep 30
                }
            }
        }

        stage('Health Check') {
            steps {
                script {
                    echo "=== VERIFICAÇÃO DE SAÚDE ==="
                    
                    sh """
                        echo "=== STATUS DOS CONTAINERS ==="
                        docker ps --filter "name=kealex-" --format "table {{.Names}}\\t{{.Status}}\\t{{.Ports}}"
                        
                        echo ""
                        echo "=== VERIFICAÇÃO DO TRAEFIK ==="
                        docker ps --filter "name=traefik" --format "table {{.Names}}\\t{{.Status}}\\t{{.Ports}}"
                        
                        echo ""
                        echo "Testando health check interno do nginx..."
                        for i in 1 2 3 4 5 6 7 8 9 10; do
                            if docker exec kealex-api-gateway curl -f http://localhost/health 2>/dev/null; then
                                echo "[OK] Nginx health check interno funcionando"
                                break
                            fi
                            echo "Tentativa \$i/10 falhou, aguardando..."
                            sleep 3
                        done
                        
                        echo ""
                        echo "Testando endpoint via Traefik..."
                        for i in 1 2 3 4 5; do
                            if curl -f https://srv1023256.hstgr.cloud/kealex/health 2>/dev/null; then
                                echo "[OK] Endpoint HTTPS via Traefik funcionando"
                                break
                            elif curl -f http://srv1023256.hstgr.cloud/kealex/health 2>/dev/null; then
                                echo "[OK] Endpoint HTTP via Traefik funcionando"
                                break
                            fi
                            echo "Tentativa \$i/5 falhou, aguardando..."
                            sleep 5
                        done
                        
                        echo ""
                        echo "Verificando logs do nginx..."
                        docker logs --tail=10 kealex-api-gateway 2>&1 | grep -i error || echo "Sem erros no nginx"
                        
                        echo ""
                        echo "Testando conectividade interna entre microserviços..."
                        docker exec kealex-api-gateway wget -q -O- http://kealex-svc-auth:8000/health 2>/dev/null && echo "[OK] svc-auth" || echo "[ERRO] svc-auth"
                        docker exec kealex-api-gateway wget -q -O- http://kealex-svc-processos:8000/health 2>/dev/null && echo "[OK] svc-processos" || echo "[ERRO] svc-processos"
                    """
                }
            }
        }
    }

    post {
        always {
            script {
                sh """
                    echo "=== STATUS FINAL ==="
                    docker ps --filter "name=kealex-" --format "table {{.Names}}\\t{{.Status}}\\t{{.Ports}}" || true
                """
            }
        }
        success {
            echo "[SUCESSO] API disponível em: https://srv1023256.hstgr.cloud/kealex/v1/lex/"
        }
        failure {
            script {
                sh """
                    echo "=== LOGS DE ERRO ==="
                    echo "--- API Gateway ---"
                    echo "Verificando logs detalhados do nginx..."
                    docker logs kealex-api-gateway 2>&1 | tail -50
                    
                    echo ""
                    echo "Testando configuração do nginx..."
                    docker exec kealex-api-gateway nginx -t 2>&1 || echo "Erro na configuração do nginx"
                    
                    echo ""
                    echo "Verificando processos dentro do container..."
                    docker exec kealex-api-gateway ps aux 2>&1 || echo "Container não está rodando"
                    
                    echo ""
                    echo "Verificando se a porta 8000 está ocupada no host..."
                    netstat -tlnp | grep :8000 || echo "Porta 8000 livre"
                    
                    echo ""
                    echo "--- SVC Auth ---"
                    docker logs --tail=20 kealex-svc-auth 2>/dev/null || true
                    echo ""
                    echo "--- SVC Processos ---"
                    docker logs --tail=20 kealex-svc-processos 2>/dev/null || true
                """
            }
        }
    }
}
