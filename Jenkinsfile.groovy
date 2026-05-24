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
                        export SECRET_KEY='${SECRET_KEY}'
                        export DATABASE_URL='${DATABASE_URL}'
                        docker compose -f docker-compose.yml up -d --remove-orphans
                    """

                    echo "Aguardando inicialização dos microserviços..."
                    sleep 20
                }
            }
        }

        stage('Setup API Gateway') {
            steps {
                script {
                    sh """
                        echo "Aguardando inicialização dos microserviços..."
                        sleep 20
                        
                        # Iniciar API Gateway
                        docker run -d --name kealex-api-gateway \\
                            --network kealex-network \\
                            -p 8000:80 \\
                            --restart unless-stopped \\
                            kealex/api-gateway:latest
                        
                        echo "Aguardando inicialização do nginx..."
                        sleep 10
                    """
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
                        HEALTH_OK=0
                        for i in 1 2 3 4 5; do
                            if curl -f http://localhost:8000/health 2>/dev/null; then
                                echo "[OK] Nginx respondendo"
                                HEALTH_OK=1
                                break
                            fi
                            echo "Tentativa \$i/10..."
                            sleep 5
                        done

                        if [ \$HEALTH_OK -eq 0 ]; then
                            echo "[ERRO] Nginx não respondeu"
                            exit 1
                        fi
                        
                        echo ""
                        echo "Testando endpoint de autenticação..."
                        curl -X POST http://localhost:8000/k1/lex/auth/login \\
                            -H "Content-Type: application/json" \\
                            -d '{"email": "admin@kealex.com", "senha": "admin123"}' || true
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
            echo "[SUCESSO] API disponível em: http://localhost:8000/k1/lex/"
        }
        failure {
            script {
                sh """
                    echo "=== LOGS DE ERRO ==="
                    echo "--- API Gateway ---"
                    docker logs --tail=30 kealex-api-gateway 2>/dev/null || true
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
