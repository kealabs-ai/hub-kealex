pipeline {
    agent any

    environment {
        IMAGE_PREFIX = "kealex"
        TAG = "latest"
        DATABASE_URL = credentials('kealex-database-url')
        SECRET_KEY = credentials('kealex-secret-key')
        COMPOSE_PROJECT_NAME = "kealex"
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
                        sh "docker build -t ${IMAGE_PREFIX}/${svc}:${TAG} ./${svc}"
                    }
                }
            }
        }

        stage('Deploy Containers') {
            steps {
                script {
                    echo "=== DEPLOY DOS CONTAINERS ==="
                    
                    sh """
                        docker-compose -p ${COMPOSE_PROJECT_NAME} down --remove-orphans || true
                        
                        export SECRET_KEY=${SECRET_KEY}
                        export DATABASE_URL=${DATABASE_URL}
                        
                        docker-compose -p ${COMPOSE_PROJECT_NAME} up -d
                        
                        echo "Aguardando inicialização dos serviços..."
                        sleep 30
                    """
                }
            }
        }

        stage('Health Check') {
            steps {
                script {
                    echo "=== VERIFICAÇÃO DE SAÚDE ==="
                    
                    sh """
                        docker-compose -p ${COMPOSE_PROJECT_NAME} ps
                        
                        echo "Testando nginx health endpoint..."
                        for i in {1..10}; do
                            if curl -f http://localhost:8000/health; then
                                echo "[OK] Nginx respondendo"
                                break
                            fi
                            sleep 5
                        done
                        
                        echo "Testando endpoint de autenticação..."
                        curl -X POST http://localhost:8000/v1/lex/auth/login \
                            -H "Content-Type: application/json" \
                            -d '{"email": "admin@kealex.com", "senha": "admin123"}' || true
                    """
                }
            }
        }
    }

    post {
        always {
            sh """
                echo "=== STATUS FINAL ==="
                docker-compose -p ${COMPOSE_PROJECT_NAME} ps
            """
        }
        success {
            echo "[SUCESSO] API disponível em: http://localhost:8000/v1/lex/"
        }
        failure {
            sh """
                echo "=== LOGS DE ERRO ==="
                docker-compose -p ${COMPOSE_PROJECT_NAME} logs --tail=50
            """
        }
    }
}
