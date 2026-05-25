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
                    
                    def composeCmd = sh(script: "docker compose version 2>/dev/null && echo 'docker compose' || echo 'docker-compose'", returnStdout: true).trim()
                    echo "Usando: ${composeCmd}"
                    
                    sh """
                        export SECRET_KEY='${SECRET_KEY}'
                        export DATABASE_URL='${DATABASE_URL}'
                        ${composeCmd} down --remove-orphans || true
                        ${composeCmd} up -d --build --remove-orphans
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
                            if curl -f http://localhost:8000/health 2>/dev/null; then
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
