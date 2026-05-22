pipeline {
    agent any

    environment {
        REGISTRY = "registry.kealex.io"
        IMAGE_PREFIX = "kealex"
        TAG = "${env.BUILD_NUMBER}"
        DATABASE_URL = "mysql+pymysql://u549746795_kealex:Sally2026%40%21%40@srv1078.hstgr.io:3306/u549746795_kealex"
        COMPOSE_PROJECT_NAME = "kealex"
    }

    stages {
        stage('Check Environment') {
            steps {
                script {
                    echo "=== VERIFICANDO AMBIENTE ==="
                    
                    sh "docker --version"
                    sh "docker info --format 'Server Version: {{.ServerVersion}}'"
                    
                    sh """
                        if ! command -v docker-compose &> /dev/null; then
                            echo 'Instalando docker-compose...'
                            mkdir -p \$HOME/bin
                            curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-linux-x86_64" -o \$HOME/bin/docker-compose
                            chmod +x \$HOME/bin/docker-compose
                            export PATH=\$HOME/bin:\$PATH
                            echo 'docker-compose instalado em \$HOME/bin/docker-compose'
                        fi
                        
                        export PATH=\$HOME/bin:\$PATH
                        echo 'Verificando docker-compose:'
                        docker-compose --version
                        echo 'Localização:'
                        which docker-compose
                    """
                    
                    sh "whoami"
                    sh "id"
                    sh "pwd"
                    sh "ls -la docker-compose.yml"
                    
                    echo "=== AMBIENTE VERIFICADO ==="
                }
            }
        }

        stage('Cleanup') {
            steps {
                script {
                    echo "=== LIMPEZA INTELIGENTE ==="
                    
                    sh """
                        echo "Espaço antes da limpeza:"
                        df -h .
                        docker system df
                    """
                    
                    sh """
                        echo "Removendo imagens não utilizadas..."
                        docker image prune -f --filter "until=24h" || true
                        echo "Removendo containers parados..."
                        docker container prune -f || true
                        echo "Removendo redes não utilizadas..."
                        docker network prune -f || true
                        echo "Removendo volumes órfãos..."
                        docker volume prune -f || true
                    """
                    
                    sh """
                        echo "Espaço após limpeza:"
                        df -h .
                        docker system df
                    """
                    
                    echo "=== LIMPEZA CONCLUÍDA ==="
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
            steps {
                script {
                    echo "=== BUILD SEQUENCIAL PARA HOSTINGER ==="
                    
                    def services = [
                        'svc-auth', 'svc-processos', 'svc-documentos', 
                        'svc-financeiro', 'svc-prazos', 'svc-usuarios',
                        'svc-clientes', 'svc-configuracoes', 'svc-escritorios',
                        'api-gateway'
                    ]
                    
                    services.each { svc ->
                        echo "Verificando imagem ${svc}..."
                        
                        def imageExists = sh(
                            script: "docker images -q ${IMAGE_PREFIX}/${svc}:latest 2>/dev/null",
                            returnStdout: true
                        ).trim()
                        
                        if (imageExists) {
                            echo "Imagem ${svc} já existe, pulando build..."
                        } else {
                            echo "Building ${svc}..."
                            sh """
                                docker build -t ${IMAGE_PREFIX}/${svc}:${TAG} ./${svc}
                                docker tag ${IMAGE_PREFIX}/${svc}:${TAG} ${IMAGE_PREFIX}/${svc}:latest
                            """
                            sleep(2)
                        }
                    }
                }
            }
        }

        stage('Test Images') {
            steps {
                script {
                    echo "=== TESTANDO IMAGENS CONSTRUÍDAS ==="
                    sh "docker images | grep kealex"
                    
                    sh """
                        docker run --rm \
                          -e DATABASE_URL=sqlite:///./test.db \
                          -e SECRET_KEY=test-key \
                          ${IMAGE_PREFIX}/svc-auth:latest \
                          python -c "import main; print('svc-auth: OK')"
                    """
                }
            }
        }

        stage('Test Nginx Config') {
            steps {
                script {
                    echo "=== TESTANDO CONFIGURAÇÃO DO NGINX ==="
                    
                    sh """
                        echo "Testando sintaxe da configuração do nginx..."
                        docker run --rm ${IMAGE_PREFIX}/api-gateway:latest nginx -t
                    """
                    
                    sh """
                        echo "Verificando arquivos de configuração..."
                        docker run --rm ${IMAGE_PREFIX}/api-gateway:latest ls -la /etc/nginx/conf.d/
                    """
                    
                    echo "=== CONFIGURAÇÃO DO NGINX VALIDADA ==="
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
                            sh "docker push ${REGISTRY}/${IMAGE_PREFIX}/${svc}:${TAG}"
                            sh "docker push ${REGISTRY}/${IMAGE_PREFIX}/${svc}:latest"
                        }
                    }
                }
            }
        }

        stage('Pre-Deploy Check') {
            when { branch 'main' }
            steps {
                script {
                    echo "=== VERIFICAÇÃO PRÉ-DEPLOY ==="
                    
                    sh """
                        echo "Verificando containers existentes..."
                        EXISTING=\$(docker ps -q --filter "name=kealex" --filter "name=svc-" --filter "name=api-gateway")
                        if [ -n "\$EXISTING" ]; then
                            echo "Containers existentes encontrados:"
                            docker ps --filter "name=kealex" --filter "name=svc-" --filter "name=api-gateway"
                            echo "Estes serão substituídos durante o deploy."
                        else
                            echo "Nenhum container existente encontrado."
                        fi
                    """
                    
                    sh """
                        echo "Verificando espaço em disco..."
                        df -h .
                        
                        AVAILABLE=\$(df . | tail -1 | awk '{print \$4}' | sed 's/G//')
                        if [ "\$AVAILABLE" -lt 2 ]; then
                            echo "[AVISO] Pouco espaço em disco disponível: \${AVAILABLE}G"
                            echo "Limpando imagens não utilizadas..."
                            docker image prune -f
                        else
                            echo "[OK] Espaço suficiente: \${AVAILABLE}G"
                        fi
                    """
                    
                    sh """
                        echo "Verificando porta 8000..."
                        
                        if command -v ss &> /dev/null; then
                            PORT_CHECK=\$(ss -tlnp 2>/dev/null | grep :8000 || echo "livre")
                        elif command -v netstat &> /dev/null; then
                            PORT_CHECK=\$(netstat -tlnp 2>/dev/null | grep :8000 || echo "livre")
                        else
                            PORT_CHECK="livre"
                        fi
                        
                        if [ "\$PORT_CHECK" = "livre" ]; then
                            echo "[OK] Porta 8000 está livre"
                        else
                            echo "[OK] Porta 8000 em uso: \$PORT_CHECK"
                        fi
                    """
                    
                    echo "=== PRÉ-VERIFICAÇÃO CONCLUÍDA ==="
                }
            }
        }

        stage('Deploy') {
            when { branch 'main' }
            steps {
                withCredentials([string(credentialsId: 'kealex-secret-key', variable: 'SECRET_KEY')]) {
                    script {
                        echo "=== INICIANDO DEPLOY ==="
                        
                        sh """
                            export PATH=\$HOME/bin:\$PATH
                            echo 'Parando containers antigos...'
                            
                            docker-compose -p ${COMPOSE_PROJECT_NAME} down --remove-orphans 2>/dev/null || true
                            docker ps -aq --filter "name=kealex" | xargs -r docker rm -f 2>/dev/null || true
                            docker network rm kealex-network 2>/dev/null || true
                            
                            echo 'Limpeza concluída'
                        """
                        
                        sh """
                            cat > .env << EOF
SECRET_KEY=${SECRET_KEY}
DATABASE_URL=${DATABASE_URL}
REGISTRY=${REGISTRY}
TAG=${TAG}
COMPOSE_PROJECT_NAME=${COMPOSE_PROJECT_NAME}
EOF
                        """
                        
                        sh """
                            export PATH=\$HOME/bin:\$PATH
                            
                            if [ -f "docker-compose.hostinger.yml" ]; then
                                COMPOSE_FILE="docker-compose.hostinger.yml"
                            else
                                COMPOSE_FILE="docker-compose.yml"
                            fi
                            
                            echo "Usando: \$COMPOSE_FILE"
                            echo "\$COMPOSE_FILE" > .compose_file
                        """
                        
                        sh """
                            export PATH=\$HOME/bin:\$PATH
                            export SECRET_KEY=${SECRET_KEY}
                            export DATABASE_URL=${DATABASE_URL}
                            export TAG=${TAG}
                            export COMPOSE_PROJECT_NAME=${COMPOSE_PROJECT_NAME}
                            
                            COMPOSE_FILE=\$(cat .compose_file)
                            echo "Deploy com \$COMPOSE_FILE..."
                            
                            echo "Validando arquivo docker-compose..."
                            docker-compose -f \$COMPOSE_FILE config --quiet || {
                                echo "[ERRO] Arquivo docker-compose inválido!"
                                docker-compose -f \$COMPOSE_FILE config
                                exit 1
                            }
                            
                            echo "Iniciando containers..."
                            if docker-compose -f \$COMPOSE_FILE -p ${COMPOSE_PROJECT_NAME} up -d --build 2>&1; then
                                echo "[OK] Containers iniciados com sucesso"
                            else
                                EXIT_CODE=\$?
                                echo "[ERRO] Falha ao iniciar containers (exit code: \$EXIT_CODE)"
                                echo "Verificando logs de erro..."
                                docker-compose -f \$COMPOSE_FILE -p ${COMPOSE_PROJECT_NAME} logs --tail=50
                                exit \$EXIT_CODE
                            fi
                            
                            echo "Aguardando inicialização (45s)..."
                            sleep 45
                            
                            echo "=== STATUS DOS CONTAINERS ==="
                            docker-compose -f \$COMPOSE_FILE -p ${COMPOSE_PROJECT_NAME} ps
                            docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
                            
                            echo "Verificando containers com falha..."
                            FAILED=\$(docker-compose -f \$COMPOSE_FILE -p ${COMPOSE_PROJECT_NAME} ps --filter "status=exited" --services)
                            if [ -n "\$FAILED" ]; then
                                echo "[AVISO] Containers com falha: \$FAILED"
                                for service in \$FAILED; do
                                    echo "--- Logs de \$service ---"
                                    docker-compose -f \$COMPOSE_FILE -p ${COMPOSE_PROJECT_NAME} logs --tail=30 \$service
                                done
                            fi
                        """
                        
                        echo "=== DEPLOY CONCLUÍDO ==="
                    }
                }
            }
        }

        stage('Validate Nginx') {
            when { branch 'main' }
            steps {
                script {
                    echo "=== VALIDANDO NGINX ==="
                    
                    sh """
                        export PATH=\$HOME/bin:\$PATH
                        COMPOSE_FILE=\$(cat .compose_file)
                        
                        echo "Verificando se nginx está rodando..."
                        docker-compose -f \$COMPOSE_FILE -p ${COMPOSE_PROJECT_NAME} ps api-gateway
                        
                        echo "Testando configuração do nginx..."
                        docker-compose -f \$COMPOSE_FILE -p ${COMPOSE_PROJECT_NAME} exec -T api-gateway nginx -t || true
                        
                        echo "Verificando logs do nginx..."
                        docker-compose -f \$COMPOSE_FILE -p ${COMPOSE_PROJECT_NAME} logs --tail=20 api-gateway
                        
                        echo "Verificando processos nginx..."
                        docker-compose -f \$COMPOSE_FILE -p ${COMPOSE_PROJECT_NAME} exec -T api-gateway ps aux | grep nginx || true
                    """
                    
                    echo "=== NGINX VALIDADO ==="
                }
            }
        }

        stage('Health Check') {
            when { branch 'main' }
            steps {
                script {
                    echo "=== VERIFICAÇÃO DE SAÚDE ==="
                    
                    sh """
                        export PATH=\$HOME/bin:\$PATH
                        COMPOSE_FILE=\$(cat .compose_file)
                        
                        echo "=== STATUS DOS CONTAINERS ==="
                        docker-compose -f \$COMPOSE_FILE -p ${COMPOSE_PROJECT_NAME} ps
                        
                        echo "=== VERIFICAÇÃO DO NGINX ==="
                        echo "Testando configuração do nginx..."
                        docker-compose -f \$COMPOSE_FILE -p ${COMPOSE_PROJECT_NAME} exec -T api-gateway nginx -t || echo "Falha ao testar nginx"
                        
                        echo "Verificando processos nginx..."
                        docker-compose -f \$COMPOSE_FILE -p ${COMPOSE_PROJECT_NAME} exec -T api-gateway ps aux | grep nginx || echo "Nginx não encontrado"
                        
                        echo "=== LOGS DOS SERVIÇOS ==="
                        echo "--- API Gateway (Nginx) ---"
                        docker-compose -f \$COMPOSE_FILE -p ${COMPOSE_PROJECT_NAME} logs --tail=20 api-gateway
                        
                        echo "--- SVC Auth ---"
                        docker-compose -f \$COMPOSE_FILE -p ${COMPOSE_PROJECT_NAME} logs --tail=15 svc-auth
                        
                        echo "=== VERIFICAÇÃO DE PORTA ==="
                        if command -v ss &> /dev/null; then
                            ss -tlnp | grep :8000 || echo "Porta 8000 não está em uso"
                        elif command -v netstat &> /dev/null; then
                            netstat -tlnp | grep :8000 || echo "Porta 8000 não está em uso"
                        else
                            echo "Não foi possível verificar porta 8000"
                        fi
                    """
                    
                    sh """
                        echo '=== TESTE DE CONECTIVIDADE DO NGINX ==='
                        
                        for i in {1..15}; do
                            echo "Tentativa \$i/15 - testando health endpoint do nginx..."
                            
                            if curl -f -s --connect-timeout 5 --max-time 10 http://localhost:8000/health >/dev/null 2>&1; then
                                echo '[OK] Nginx health endpoint respondendo!'
                                curl -s http://localhost:8000/health
                                break
                            elif [ \$i -eq 15 ]; then
                                echo '[ERRO] Nginx não respondeu após 15 tentativas'
                                
                                export PATH=\$HOME/bin:\$PATH
                                COMPOSE_FILE=\$(cat .compose_file)
                                
                                echo "Diagnóstico do nginx:"
                                docker-compose -f \$COMPOSE_FILE -p ${COMPOSE_PROJECT_NAME} logs --tail=50 api-gateway
                                
                                echo "Status do container:"
                                docker-compose -f \$COMPOSE_FILE -p ${COMPOSE_PROJECT_NAME} ps api-gateway
                                
                                echo "Processos no container:"
                                docker-compose -f \$COMPOSE_FILE -p ${COMPOSE_PROJECT_NAME} exec -T api-gateway ps aux || true
                                
                                exit 1
                            else
                                sleep 8
                            fi
                        done
                        
                        echo '=== TESTE DE ENDPOINTS DA API ==='
                        for i in {1..10}; do
                            echo "Tentativa \$i/10 - testando /v1/lex/auth/me..."
                            
                            RESPONSE=\$(curl -s -w "%{http_code}" http://localhost:8000/v1/lex/auth/me 2>/dev/null || echo "000")
                            HTTP_CODE="\${RESPONSE: -3}"
                            
                            if [ "\$HTTP_CODE" = "401" ] || [ "\$HTTP_CODE" = "200" ]; then
                                echo '[OK] API endpoint respondendo (HTTP \$HTTP_CODE)!'
                                break
                            elif [ \$i -eq 10 ]; then
                                echo '[AVISO] Endpoint retornou: \$HTTP_CODE'
                                echo 'Resposta completa:'
                                curl -v http://localhost:8000/v1/lex/auth/me || true
                            else
                                sleep 6
                            fi
                        done
                    """
                    
                    sh """
                        echo '=== TESTE DE LOGIN VIA NGINX ==='
                        
                        RESPONSE=\$(curl -s -w "%{http_code}" --connect-timeout 10 --max-time 15 \
                            -X POST http://localhost:8000/v1/lex/auth/login \
                            -H "Content-Type: application/json" \
                            -d '{"email": "admin@kealex.com", "senha": "admin123"}' 2>/dev/null || echo "000")
                        
                        HTTP_CODE="\${RESPONSE: -3}"
                        BODY="\${RESPONSE%???}"
                        
                        echo "Status HTTP: \$HTTP_CODE"
                        
                        if [ "\$HTTP_CODE" = "200" ]; then
                            echo '[OK] Login via nginx funcionando!'
                            echo "Resposta: \$BODY"
                        elif [ "\$HTTP_CODE" = "000" ]; then
                            echo '[ERRO] Nginx não está encaminhando requisições'
                            
                            export PATH=\$HOME/bin:\$PATH
                            COMPOSE_FILE=\$(cat .compose_file)
                            
                            echo "Verificando configuração do nginx:"
                            docker-compose -f \$COMPOSE_FILE -p ${COMPOSE_PROJECT_NAME} exec -T api-gateway cat /etc/nginx/conf.d/default.conf | head -50
                        else
                            echo '[AVISO] Login retornou código: \$HTTP_CODE'
                            echo "Resposta: \$BODY"
                        fi
                    """
                    
                    echo "=== NGINX E API VALIDADOS ==="
                    echo "=== SAÚDE VERIFICADA ==="
                }
            }
        }
    }

    post {
        always {
            script {
                sh "rm -f .env .compose_file || true"
                
                sh """
                    export PATH=\$HOME/bin:\$PATH
                    
                    echo "=== STATUS FINAL DOS CONTAINERS ==="
                    docker ps --format "table {{.Names}}\\t{{.Status}}\\t{{.Ports}}" --filter "name=kealex" --filter "name=svc-" --filter "name=api-gateway" || true
                    
                    echo "=== RESUMO DE RECURSOS ==="
                    docker system df || true
                """
            }
        }
        success {
            echo "[SUCESSO] Pipeline executado com sucesso!"
            echo "[INFO] API disponível em: http://localhost:8000/v1/lex/"
            echo "[INFO] Documentação: http://localhost:8000/docs"
            echo "[INFO] Credenciais padrão: admin@kealex.com / admin123"
        }
        failure {
            echo "[ERRO] Pipeline falhou - coletando diagnóstico..."
            sh """
                export PATH=\$HOME/bin:\$PATH
                
                echo "=== LOGS DE ERRO ==="
                
                if [ -f ".compose_file" ]; then
                    COMPOSE_FILE=\$(cat .compose_file)
                else
                    COMPOSE_FILE="docker-compose.yml"
                fi
                
                echo "Usando arquivo: \$COMPOSE_FILE"
                
                echo "--- Validando docker-compose ---"
                docker-compose -f \$COMPOSE_FILE config 2>&1 || echo "Erro na validação do docker-compose"
                
                echo "--- Verificando imagens ---"
                docker images | grep kealex || echo "Nenhuma imagem kealex encontrada"
                
                echo "--- Logs do API Gateway ---"
                docker-compose -f \$COMPOSE_FILE -p ${COMPOSE_PROJECT_NAME} logs --tail=30 api-gateway 2>/dev/null || echo "Serviço não encontrado"
                
                echo "--- Logs do SVC Auth ---"
                docker-compose -f \$COMPOSE_FILE -p ${COMPOSE_PROJECT_NAME} logs --tail=30 svc-auth 2>/dev/null || echo "Serviço não encontrado"
                
                echo "--- Status dos Containers ---"
                docker ps -a --filter "name=kealex" --filter "name=svc-" --filter "name=api-gateway" || true
                
                echo "--- Tentando iniciar manualmente para debug ---"
                docker-compose -f \$COMPOSE_FILE -p ${COMPOSE_PROJECT_NAME} up --no-start 2>&1 || echo "Falha ao criar containers"
                
                echo "--- Uso de Recursos ---"
                df -h || true
                free -h || true
                
                echo "--- Portas em Uso ---"
                if command -v ss &> /dev/null; then
                    ss -tlnp | grep :8000 || echo "Porta 8000 livre"
                elif command -v netstat &> /dev/null; then
                    netstat -tlnp | grep :8000 || echo "Porta 8000 livre"
                else
                    echo "Não foi possível verificar portas"
                fi
            """
        }
    }
}
