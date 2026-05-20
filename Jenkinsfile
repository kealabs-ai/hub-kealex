pipeline {
    agent any

    environment {
        REGISTRY = "registry.kealex.io"
        IMAGE_PREFIX = "${REGISTRY}/kealex"
        TAG = "${env.BUILD_NUMBER}"
        DATABASE_URL = "mysql+pymysql://u549746795_kealex:Sally2026%40%21%40@srv1078.hstgr.io:3306/u549746795_kealex"
    }

    stages {
        stage('Cleanup') {
            steps {
                script {
                    // Parar containers antigos se existirem
                    sh "docker compose down || true"
                    sh "docker system prune -f || true"
                }
            }
        }

        stage('Checkout') {
            steps { 
                checkout scm 
                sh "ls -la"
            }
        }

        stage('Build Images') {
            parallel {
                stage('svc-auth') { 
                    steps { 
                        sh "docker build -t ${IMAGE_PREFIX}/svc-auth:${TAG} ./svc-auth"
                        sh "docker tag ${IMAGE_PREFIX}/svc-auth:${TAG} ${IMAGE_PREFIX}/svc-auth:latest"
                    } 
                }
                stage('svc-processos') { 
                    steps { 
                        sh "docker build -t ${IMAGE_PREFIX}/svc-processos:${TAG} ./svc-processos"
                        sh "docker tag ${IMAGE_PREFIX}/svc-processos:${TAG} ${IMAGE_PREFIX}/svc-processos:latest"
                    } 
                }
                stage('svc-documentos') { 
                    steps { 
                        sh "docker build -t ${IMAGE_PREFIX}/svc-documentos:${TAG} ./svc-documentos"
                        sh "docker tag ${IMAGE_PREFIX}/svc-documentos:${TAG} ${IMAGE_PREFIX}/svc-documentos:latest"
                    } 
                }
                stage('svc-financeiro') { 
                    steps { 
                        sh "docker build -t ${IMAGE_PREFIX}/svc-financeiro:${TAG} ./svc-financeiro"
                        sh "docker tag ${IMAGE_PREFIX}/svc-financeiro:${TAG} ${IMAGE_PREFIX}/svc-financeiro:latest"
                    } 
                }
                stage('svc-prazos') { 
                    steps { 
                        sh "docker build -t ${IMAGE_PREFIX}/svc-prazos:${TAG} ./svc-prazos"
                        sh "docker tag ${IMAGE_PREFIX}/svc-prazos:${TAG} ${IMAGE_PREFIX}/svc-prazos:latest"
                    } 
                }
                stage('svc-usuarios') { 
                    steps { 
                        sh "docker build -t ${IMAGE_PREFIX}/svc-usuarios:${TAG} ./svc-usuarios"
                        sh "docker tag ${IMAGE_PREFIX}/svc-usuarios:${TAG} ${IMAGE_PREFIX}/svc-usuarios:latest"
                    } 
                }
                stage('svc-clientes') { 
                    steps { 
                        sh "docker build -t ${IMAGE_PREFIX}/svc-clientes:${TAG} ./svc-clientes"
                        sh "docker tag ${IMAGE_PREFIX}/svc-clientes:${TAG} ${IMAGE_PREFIX}/svc-clientes:latest"
                    } 
                }
                stage('svc-configuracoes') { 
                    steps { 
                        sh "docker build -t ${IMAGE_PREFIX}/svc-configuracoes:${TAG} ./svc-configuracoes"
                        sh "docker tag ${IMAGE_PREFIX}/svc-configuracoes:${TAG} ${IMAGE_PREFIX}/svc-configuracoes:latest"
                    } 
                }
                stage('svc-escritorios') { 
                    steps { 
                        sh "docker build -t ${IMAGE_PREFIX}/svc-escritorios:${TAG} ./svc-escritorios"
                        sh "docker tag ${IMAGE_PREFIX}/svc-escritorios:${TAG} ${IMAGE_PREFIX}/svc-escritorios:latest"
                    } 
                }
                stage('api-gateway') { 
                    steps { 
                        sh "docker build -t ${IMAGE_PREFIX}/api-gateway:${TAG} ./api-gateway"
                        sh "docker tag ${IMAGE_PREFIX}/api-gateway:${TAG} ${IMAGE_PREFIX}/api-gateway:latest"
                    } 
                }
            }
        }

        stage('Test Images') {
            steps {
                script {
                    echo "=== TESTANDO IMAGENS CONSTRUÍDAS ==="
                    sh "docker images | grep kealex"
                    
                    // Teste básico de importação
                    sh """
                        docker run --rm \
                          -e DATABASE_URL=sqlite:///./test.db \
                          -e SECRET_KEY=test-key \
                          ${IMAGE_PREFIX}/svc-auth:${TAG} \
                          python -c "import main; print('svc-auth: OK')"
                    """
                }
            }
        }

        stage('Show Endpoints') {
            steps {
                echo "=== KEALEX API ENDPOINTS ==="
                echo "Base URL: http://localhost:8000/v1/lex/"
                echo ""
                echo "Auth:"
                echo "  POST /v1/lex/auth/login"
                echo "  GET  /v1/lex/auth/me"
                echo ""
                echo "Processos:"
                echo "  GET/POST /v1/lex/processos"
                echo ""
                echo "Documentos:"
                echo "  GET/POST /v1/lex/documentos"
                echo ""
                echo "Financeiro:"
                echo "  GET/POST /v1/lex/financeiro"
                echo "  GET /v1/lex/financeiro/dashboard"
                echo ""
                echo "Prazos:"
                echo "  GET/POST /v1/lex/prazos"
                echo "  GET /v1/lex/prazos/vencendo?dias=7"
                echo ""
                echo "Usuarios:"
                echo "  GET/POST /v1/lex/usuarios"
                echo ""
                echo "Escritorios:"
                echo "  GET/POST /v1/lex/escritorios"
                echo ""
                echo "Clientes:"
                echo "  GET/POST /v1/lex/clientes"
                echo ""
                echo "Configuracoes:"
                echo "  GET/POST /v1/lex/configuracoes/*"
                echo "================================"
            }
        }

        stage('Push to Registry') {
            when { branch 'main' }
            steps {
                withCredentials([usernamePassword(credentialsId: 'registry-creds', usernameVariable: 'USER', passwordVariable: 'PASS')]) {
                    script {
                        sh "echo $PASS | docker login ${REGISTRY} -u $USER --password-stdin"
                        
                        def services = ['svc-auth', 'svc-processos', 'svc-documentos', 'svc-financeiro', 
                                      'svc-prazos', 'svc-usuarios', 'svc-clientes', 'svc-configuracoes', 
                                      'svc-escritorios', 'api-gateway']
                        
                        services.each { svc ->
                            sh "docker push ${IMAGE_PREFIX}/${svc}:${TAG}"
                            sh "docker push ${IMAGE_PREFIX}/${svc}:latest"
                        }
                    }
                }
            }
        }

        stage('Deploy') {
            when { branch 'main' }
            steps {
                withCredentials([string(credentialsId: 'kealex-secret-key', variable: 'SECRET_KEY')]) {
                    script {
                        echo "=== INICIANDO DEPLOY ==="
                        
                        // Criar arquivo .env temporário
                        sh """
                            cat > .env.deploy << EOF
SECRET_KEY=${SECRET_KEY}
DATABASE_URL=${DATABASE_URL}
REGISTRY=${REGISTRY}
TAG=${TAG}
EOF
                        """
                        
                        // Deploy usando docker-compose local (build)
                        sh """
                            export SECRET_KEY=${SECRET_KEY}
                            export DATABASE_URL=${DATABASE_URL}
                            export TAG=${TAG}
                            docker compose up -d --build --remove-orphans
                        """
                        
                        // Aguardar inicialização
                        sh "sleep 45"
                        
                        // Verificar status
                        sh "docker compose ps"
                        
                        echo "=== DEPLOY CONCLUÍDO ==="
                    }
                }
            }
        }

        stage('Health Check') {
            when { branch 'main' }
            steps {
                script {
                    echo "=== VERIFICAÇÃO DE SAÚDE ==="
                    
                    // Verificar containers
                    sh "docker compose ps"
                    
                    // Verificar logs
                    sh "docker compose logs --tail=10 api-gateway || true"
                    sh "docker compose logs --tail=10 svc-auth || true"
                    
                    // Teste de conectividade
                    sh """
                        echo 'Testando conectividade...'
                        for i in {1..12}; do
                            echo "Tentativa \$i/12"
                            if curl -f -s http://localhost:8000/v1/lex/auth/me >/dev/null 2>&1; then
                                echo '[OK] API respondendo!'
                                break
                            elif [ \$i -eq 12 ]; then
                                echo '[ERRO] API nao respondeu apos 12 tentativas'
                                docker compose logs api-gateway
                                exit 1
                            else
                                sleep 10
                            fi
                        done
                    """
                    
                    // Teste de login
                    sh """
                        echo 'Testando login...'
                        RESPONSE=\$(curl -s -w "%{http_code}" -X POST http://localhost:8000/v1/lex/auth/login \
                            -H "Content-Type: application/json" \
                            -d '{"email": "admin@kealex.com", "senha": "admin123"}')
                        
                        if echo "\$RESPONSE" | grep -q "200"; then
                            echo '[OK] Login funcionando!'
                        else
                            echo '[ERRO] Problema no login:'
                            echo "\$RESPONSE"
                        fi
                    """
                    
                    echo "=== SAÚDE VERIFICADA ==="
                }
            }
        }
    }

    post {
        always {
            script {
                // Limpar arquivo temporário
                sh "rm -f .env.deploy || true"
                
                // Mostrar status final
                sh "docker compose ps || true"
            }
        }
        success {
            echo "[SUCESSO] Pipeline executado com sucesso!"
            echo "[INFO] API disponivel em: http://localhost:8000/v1/lex/"
        }
        failure {
            echo "[ERRO] Pipeline falhou - verificando logs..."
            sh "docker compose logs --tail=50 || true"
        }
    }
}
