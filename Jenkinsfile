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
                        for i in 1 2 3 4 5; do
                            if curl -f http://localhost:8000/health 2>/dev/null; then
                                echo "[OK] Nginx respondendo"
                                exit 0
                            fi
                            echo "Tentativa \$i/10..."
                            sleep 5
                        done
                        exit 1
                        
                        echo ""
                        echo "Testando endpoint de autenticação..."
                        curl -i -X POST http://localhost:8000/k1/lex/auth/login \\
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
