pipeline {
    agent any

    environment {
        IMAGE_PREFIX = "kealex"
        TAG = "latest"
        SECRET_KEY = "${env.SECRET_KEY}"
        DATABASE_URL = "${env.DATABASE_URL}"
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
                        # Parar containers existentes
                        docker ps -aq --filter "name=kealex-" | xargs -r docker rm -f || true
                        
                        # Criar rede se não existir
                        docker network create kealex-network || true
                        
                        # Iniciar microserviços
                        docker run -d --name kealex-svc-auth \\
                            --network kealex-network \\
                            -e SECRET_KEY='${SECRET_KEY}' \\
                            -e DATABASE_URL='${DATABASE_URL}' \\
                            --restart unless-stopped \\
                            kealex/svc-auth:latest
                        
                        docker run -d --name kealex-svc-processos \\
                            --network kealex-network \\
                            -e SECRET_KEY='${SECRET_KEY}' \\
                            -e DATABASE_URL='${DATABASE_URL}' \\
                            --restart unless-stopped \\
                            kealex/svc-processos:latest
                        
                        docker run -d --name kealex-svc-documentos \\
                            --network kealex-network \\
                            -e SECRET_KEY='${SECRET_KEY}' \\
                            -e DATABASE_URL='${DATABASE_URL}' \\
                            --restart unless-stopped \\
                            kealex/svc-documentos:latest
                        
                        docker run -d --name kealex-svc-financeiro \\
                            --network kealex-network \\
                            -e SECRET_KEY='${SECRET_KEY}' \\
                            -e DATABASE_URL='${DATABASE_URL}' \\
                            --restart unless-stopped \\
                            kealex/svc-financeiro:latest
                        
                        docker run -d --name kealex-svc-prazos \\
                            --network kealex-network \\
                            -e SECRET_KEY='${SECRET_KEY}' \\
                            -e DATABASE_URL='${DATABASE_URL}' \\
                            --restart unless-stopped \\
                            kealex/svc-prazos:latest
                        
                        docker run -d --name kealex-svc-usuarios \\
                            --network kealex-network \\
                            -e SECRET_KEY='${SECRET_KEY}' \\
                            -e DATABASE_URL='${DATABASE_URL}' \\
                            --restart unless-stopped \\
                            kealex/svc-usuarios:latest
                        
                        docker run -d --name kealex-svc-clientes \\
                            --network kealex-network \\
                            -e SECRET_KEY='${SECRET_KEY}' \\
                            -e DATABASE_URL='${DATABASE_URL}' \\
                            --restart unless-stopped \\
                            kealex/svc-clientes:latest
                        
                        docker run -d --name kealex-svc-configuracoes \\
                            --network kealex-network \\
                            -e SECRET_KEY='${SECRET_KEY}' \\
                            -e DATABASE_URL='${DATABASE_URL}' \\
                            --restart unless-stopped \\
                            kealex/svc-configuracoes:latest
                        
                        docker run -d --name kealex-svc-escritorios \\
                            --network kealex-network \\
                            -e SECRET_KEY='${SECRET_KEY}' \\
                            -e DATABASE_URL='${DATABASE_URL}' \\
                            --restart unless-stopped \\
                            kealex/svc-escritorios:latest
                        
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
                        for i in {1..10}; do
                            if curl -f http://localhost:8000/health 2>/dev/null; then
                                echo "[OK] Nginx respondendo"
                                break
                            fi
                            echo "Tentativa \$i/10..."
                            sleep 5
                        done
                        
                        echo ""
                        echo "Testando endpoint de autenticação..."
                        curl -X POST http://localhost:8000/v1/lex/auth/login \\
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
            echo "[SUCESSO] API disponível em: http://localhost:8000/v1/lex/"
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
