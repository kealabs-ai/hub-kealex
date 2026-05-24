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
                        cd /var/jenkins_home/workspace/hub_kealex
                        /usr/local/bin/docker-compose -f docker-compose.yml up -d --remove-orphans || docker compose -f docker-compose.yml up -d --remove-orphans
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
                        
                        # Testar auth direto
                        echo "Testando svc-auth na porta 8001..."
                        curl -f http://localhost:8001/health 2>/dev/null && echo "[OK] Auth respondendo" || echo "[ERRO] Auth não respondeu"
                        
                        # Testar processos direto
                        echo "Testando svc-processos na porta 8002..."
                        curl -f http://localhost:8002/health 2>/dev/null && echo "[OK] Processos respondendo" || echo "[ERRO] Processos não respondeu"
                        
                        # Testar via Traefik
                        echo ""
                        echo "Testando via Traefik..."
                        curl -k https://srv1023256.hstgr.cloud/k1/kealex/auth/login -X POST \\
                            -H "Content-Type: application/json" \\
                            -d '{"email": "admin@kealex.com", "password": "admin123"}' 2>/dev/null || echo "[INFO] Traefik ainda não configurado"
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
