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
                        
                        \$COMPOSE_CMD -f docker-compose.local.yml --project-name kealex down --remove-orphans || true
                        \$COMPOSE_CMD -f docker-compose.local.yml up -d --build --remove-orphans --project-name kealex
                    """

                    echo "Aguardando inicialização dos microserviços..."
                    sleep 20
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
                        echo "Testando nginx health endpoint..."
                        for i in 1 2 3 4 5 6 7 8 9 10; do
                            if curl -f http://localhost:18000/health 2>/dev/null; then
                                echo "[OK] Nginx respondendo"
                                break
                            fi
                            echo "Tentativa \$i/10 falhou, aguardando..."
                            sleep 3
                        done
                        
                        echo ""
                        echo "Verificando logs do nginx..."
                        docker logs --tail=10 kealex-api-gateway 2>&1 | grep -i error || echo "Sem erros no nginx"
                        
                        echo ""
                        echo "Testando conectividade com microserviços..."
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
            echo "[SUCESSO] API disponível em: http://localhost:18000/v1/lex/"
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
