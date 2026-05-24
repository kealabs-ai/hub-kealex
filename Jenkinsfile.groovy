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
                        sh "docker build -t ${IMAGE_PREFIX}/${svc}:${TAG} ./${svc} || exit 1"
                    }
                }
            }
        }

        stage('Deploy Containers') {
            steps {
                script {
                    echo "=== DEPLOY DOS CONTAINERS ==="
                    sh """
                        # Limpar containers antigos do Kealex para evitar conflitos de porta/nome
                        docker ps -aq --filter "name=kealex-" | xargs -r docker rm -f || true
                        export SECRET_KEY='${SECRET_KEY}'
                        export DATABASE_URL='${DATABASE_URL}'
                        docker compose up -d --build --remove-orphans
                    """

                    echo "Aguardando inicialização dos microserviços..."
                    sleep 20
                }
            }
        }

        stage('Health Check API') {
            steps {
                script {
                    echo "=== VERIFICAÇÃO DE SAÚDE ==="
                    
                    sh """
                        echo "=== STATUS DOS CONTAINERS ==="
                        docker ps --filter "name=kealex-" --format "table {{.Names}}\\t{{.Status}}\\t{{.Ports}}"
                        
                        echo ""
                        echo "Testando serviços..."
                        
                        # Verificar se os containers estão realmente na rede easypanel
                        echo "Verificando presença na rede easypanel..."
                        docker network inspect easypanel | grep kealex || echo "[CRÍTICO] Containers Kealex não encontrados na rede easypanel"
                        
                        # Testar via Traefik
                        echo ""
                        echo "Testando via Traefik..."
                        curl -i -k https://srv1023256.hstgr.cloud/k1/kealex/auth/login -X POST \\
                            -H "Content-Type: application/json" \\
                            -d '{"email": "admin@kealex.com", "senha": "admin123"}' || echo "[INFO] Erro de comunicação com o Traefik"
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
            echo "[SUCESSO] Containers rodando com sucesso!"
            echo "URLs de teste:"
            echo "  - Direto: http://localhost:8001/health (auth)"
            echo "  - Traefik: https://srv1023256.hstgr.cloud/k1/kealex/auth/login"
        }
        failure {
            script {
                sh """
                    echo "=== LOGS DE ERRO ==="
                    echo "--- API Gateway ---"
                    docker logs --tail=50 kealex-api-gateway 2>/dev/null || echo "API Gateway não encontrado"
                    echo ""
                    echo "--- SVC Auth ---"
                    docker logs --tail=30 kealex-svc-auth 2>/dev/null || true
                    echo ""
                    echo "--- SVC Processos ---"
                    docker logs --tail=30 kealex-svc-processos 2>/dev/null || true
                    echo ""
                    echo "--- Verificar rede ---"
                    docker network inspect easypanel 2>/dev/null | grep -A 20 Containers || echo "Rede easypanel não encontrada"
                """
            }
        }
    }
}
