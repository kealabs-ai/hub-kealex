pipeline {
    agent any

    environment {
        REGISTRY = "registry.kealex.io"
        IMAGE_PREFIX = "${REGISTRY}/kealex"
        TAG = "${env.BUILD_NUMBER}"
        DATABASE_URL = "mysql+pymysql://u549746795_kealex:Sally2026%40%21%40@srv1078.hstgr.io:3306/u549746795_kealex"
    }

    stages {
        stage('Check Environment') {
            steps {
                script {
                    echo "=== VERIFICANDO AMBIENTE ==="
                    
                    // Verificar Docker
                    sh "docker --version"
                    sh "docker info --format 'Server Version: {{.ServerVersion}}'"
                    
                    // Instalar docker-compose se não existir (sem sudo)
                    sh """
                        if ! command -v docker-compose &> /dev/null; then
                            echo 'Instalando docker-compose...'
                            
                            # Criar diretório bin do usuário
                            mkdir -p \$HOME/bin
                            
                            # Baixar docker-compose
                            curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-linux-x86_64" -o \$HOME/bin/docker-compose
                            
                            # Dar permissão de execução
                            chmod +x \$HOME/bin/docker-compose
                            
                            # Adicionar ao PATH
                            export PATH=\$HOME/bin:\$PATH
                            
                            echo 'docker-compose instalado em \$HOME/bin/docker-compose'
                        fi
                        
                        # Garantir que está no PATH
                        export PATH=\$HOME/bin:\$PATH
                        
                        echo 'Verificando docker-compose:'
                        docker-compose --version
                        echo 'Localização:'
                        which docker-compose
                    """
                    
                    // Verificar permissões
                    sh "whoami"
                    sh "id"
                    
                    // Verificar diretório
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
                    
                    // Verificar espaço antes da limpeza
                    sh """
                        echo "Espaço antes da limpeza:"
                        df -h .
                        docker system df
                    """
                    
                    // Limpeza conservadora - apenas recursos não utilizados
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
                    
                    // Verificar espaço após limpeza
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

        stage('Pre-Deploy Check') {
            when { branch 'main' }
            steps {
                script {
                    echo "=== VERIFICAÇÃO PRÉ-DEPLOY ==="
                    
                    // Verificar se há containers rodando que podem conflitar
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
                    
                    // Verificar espaço em disco
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
                    
                    // Verificar se a porta 8000 está livre ou sendo usada pelos nossos containers
                    sh """
                        echo "Verificando porta 8000..."
                        PORT_USER=\$(netstat -tlnp 2>/dev/null | grep :8000 | awk '{print \$7}' | cut -d'/' -f2 || ss -tlnp 2>/dev/null | grep :8000 | awk '{print \$6}' | cut -d'"' -f2 || echo "livre")
                        
                        if [ "\$PORT_USER" = "livre" ]; then
                            echo "[OK] Porta 8000 está livre"
                        elif echo "\$PORT_USER" | grep -E "docker|nginx" >/dev/null; then
                            echo "[OK] Porta 8000 sendo usada por Docker/Nginx (será substituído)"
                        else
                            echo "[AVISO] Porta 8000 sendo usada por: \$PORT_USER"
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
                        
                        // Parar containers antigos primeiro
                        sh """
                            export PATH=\$HOME/bin:\$PATH
                            echo 'Parando containers antigos...'
                            docker-compose down 2>/dev/null || true
                            docker-compose -f docker-compose.prod.yml down 2>/dev/null || true
                            
                            # Remover containers órfãos
                            docker ps -aq --filter "name=kealex" --filter "name=svc-" --filter "name=api-gateway" | xargs -r docker rm -f 2>/dev/null || true
                        """
                        
                        // Criar arquivo .env
                        sh """
                            cat > .env << EOF
SECRET_KEY=${SECRET_KEY}
DATABASE_URL=${DATABASE_URL}
REGISTRY=${REGISTRY}
TAG=${TAG}
EOF
                        """
                        
                        // Escolher arquivo docker-compose
                        sh """
                            export PATH=\$HOME/bin:\$PATH
                            
                            # Verificar se deve usar produção ou desenvolvimento
                            if [ -f "docker-compose.prod.yml" ]; then
                                echo 'Testando registry...'
                                if docker pull ${REGISTRY}/kealex/api-gateway:${TAG} 2>/dev/null; then
                                    echo 'Registry acessível - usando docker-compose.prod.yml'
                                    COMPOSE_FILE="docker-compose.prod.yml"
                                else
                                    echo 'Registry inacessível - usando docker-compose.yml'
                                    COMPOSE_FILE="docker-compose.yml"
                                fi
                            else
                                COMPOSE_FILE="docker-compose.yml"
                            fi
                            
                            echo "Arquivo escolhido: \$COMPOSE_FILE"
                            echo "\$COMPOSE_FILE" > .compose_file
                        """
                        
                        // Deploy
                        sh """
                            export PATH=\$HOME/bin:\$PATH
                            export SECRET_KEY=${SECRET_KEY}
                            export DATABASE_URL=${DATABASE_URL}
                            export REGISTRY=${REGISTRY}
                            export TAG=${TAG}
                            
                            COMPOSE_FILE=\$(cat .compose_file)
                            echo "Fazendo deploy com \$COMPOSE_FILE..."
                            
                            if [ "\$COMPOSE_FILE" = "docker-compose.prod.yml" ]; then
                                # Modo produção - pull das imagens
                                docker-compose -f \$COMPOSE_FILE pull
                                docker-compose -f \$COMPOSE_FILE up -d --remove-orphans
                            else
                                # Modo desenvolvimento - build local
                                docker-compose -f \$COMPOSE_FILE up -d --build --remove-orphans
                            fi
                        """
                        
                        // Aguardar inicialização
                        sh "sleep 60"
                        
                        // Verificar status
                        sh """
                            export PATH=\$HOME/bin:\$PATH
                            COMPOSE_FILE=\$(cat .compose_file)
                            echo "Status dos containers:"
                            docker-compose -f \$COMPOSE_FILE ps
                            
                            echo "Containers em execução:"
                            docker ps --format "table {{.Names}}\\t{{.Status}}\\t{{.Ports}}"
                        """
                        
                        echo "=== DEPLOY CONCLUÍDO ==="
                    }
                }
            }
        }

        stage('Post-Deploy Validation') {
            when { branch 'main' }
            steps {
                script {
                    echo "=== VALIDAÇÃO PÓS-DEPLOY ==="
                    
                    // Aguardar estabilização
                    sh "sleep 30"
                    
                    // Verificar se todos os containers estão rodando
                    sh """
                        export PATH=\$HOME/bin:\$PATH
                        COMPOSE_FILE=\$(cat .compose_file)
                        
                        echo "Verificando status de todos os containers..."
                        
                        FAILED_SERVICES=\$(docker-compose -f \$COMPOSE_FILE ps --services --filter "status=exited")
                        
                        if [ -n "\$FAILED_SERVICES" ]; then
                            echo "[ERRO] Serviços com falha: \$FAILED_SERVICES"
                            
                            for service in \$FAILED_SERVICES; do
                                echo "--- Logs do \$service ---"
                                docker-compose -f \$COMPOSE_FILE logs --tail=20 \$service
                            done
                            
                            exit 1
                        else
                            echo "[OK] Todos os serviços estão rodando"
                        fi
                    """
                    
                    echo "=== VALIDAÇÃO CONCLUÍDA ==="
                }
            }
        }

        stage('Health Check') {
            when { branch 'main' }
            steps {
                script {
                    echo "=== VERIFICAÇÃO DE SAÚDE ==="
                    
                    // Verificar containers
                    sh """
                        export PATH=\$HOME/bin:\$PATH
                        COMPOSE_FILE=\$(cat .compose_file)
                        echo "Verificando containers com \$COMPOSE_FILE..."
                        docker-compose -f \$COMPOSE_FILE ps
                    """
                    
                    // Verificar logs de serviços críticos
                    sh """
                        export PATH=\$HOME/bin:\$PATH
                        COMPOSE_FILE=\$(cat .compose_file)
                        
                        echo "=== Logs do API Gateway ==="
                        docker-compose -f \$COMPOSE_FILE logs --tail=15 api-gateway || echo "Serviço api-gateway não encontrado"
                        
                        echo "=== Logs do SVC Auth ==="
                        docker-compose -f \$COMPOSE_FILE logs --tail=15 svc-auth || echo "Serviço svc-auth não encontrado"
                        
                        echo "=== Logs do SVC Processos ==="
                        docker-compose -f \$COMPOSE_FILE logs --tail=10 svc-processos || echo "Serviço svc-processos não encontrado"
                    """
                    
                    // Verificar se a porta está sendo usada
                    sh """
                        echo "Verificando porta 8000..."
                        netstat -tlnp | grep :8000 || ss -tlnp | grep :8000 || echo "Porta 8000 não está em uso"
                    """
                    
                    // Teste de conectividade com retry mais robusto
                    sh """
                        echo 'Testando conectividade da API...'
                        
                        # Primeiro testar se a porta responde
                        for i in {1..15}; do
                            echo "Tentativa \$i/15 - testando porta 8000..."
                            
                            if curl -s --connect-timeout 5 --max-time 10 http://localhost:8000 >/dev/null 2>&1; then
                                echo '[OK] Porta 8000 respondendo!'
                                break
                            elif [ \$i -eq 15 ]; then
                                echo '[ERRO] Porta 8000 não respondeu após 15 tentativas'
                                
                                # Diagnóstico adicional
                                export PATH=\$HOME/bin:\$PATH
                                COMPOSE_FILE=\$(cat .compose_file)
                                
                                echo "Diagnóstico de containers:"
                                docker ps -a --filter "name=api-gateway" --filter "name=svc-"
                                
                                echo "Logs detalhados do API Gateway:"
                                docker-compose -f \$COMPOSE_FILE logs --tail=30 api-gateway || true
                                
                                echo "Verificando se nginx está rodando:"
                                docker exec \$(docker ps -q --filter "name=api-gateway") ps aux | grep nginx || echo "Nginx não encontrado"
                                
                                exit 1
                            else
                                sleep 8
                            fi
                        done
                        
                        # Testar endpoint específico da API
                        echo 'Testando endpoint da API...'
                        for i in {1..10}; do
                            echo "Tentativa \$i/10 - testando /v1/lex/auth/me..."
                            
                            if curl -f -s --connect-timeout 5 --max-time 10 http://localhost:8000/v1/lex/auth/me >/dev/null 2>&1; then
                                echo '[OK] API endpoint respondendo!'
                                break
                            elif [ \$i -eq 10 ]; then
                                echo '[AVISO] Endpoint da API não respondeu, mas porta está ativa'
                                echo 'Testando resposta direta:'
                                curl -v http://localhost:8000/v1/lex/auth/me || true
                            else
                                sleep 6
                            fi
                        done
                    """
                    
                    // Teste de login
                    sh """
                        echo 'Testando login...'
                        
                        RESPONSE=\$(curl -s -w "%{http_code}" --connect-timeout 10 --max-time 15 \
                            -X POST http://localhost:8000/v1/lex/auth/login \
                            -H "Content-Type: application/json" \
                            -d '{"email": "admin@kealex.com", "senha": "admin123"}' 2>/dev/null || echo "000")
                        
                        HTTP_CODE="\${RESPONSE: -3}"
                        BODY="\${RESPONSE%???}"
                        
                        echo "Status HTTP: \$HTTP_CODE"
                        
                        if [ "\$HTTP_CODE" = "200" ]; then
                            echo '[OK] Login funcionando!'
                            echo "Resposta: \$BODY"
                        elif [ "\$HTTP_CODE" = "000" ]; then
                            echo '[ERRO] Sem resposta do servidor'
                        else
                            echo '[AVISO] Login retornou código: \$HTTP_CODE'
                            echo "Resposta: \$BODY"
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
                // Limpar arquivos temporários
                sh "rm -f .env .compose_file || true"
                
                // Mostrar status final
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
                
                # Tentar usar o arquivo compose correto
                if [ -f ".compose_file" ]; then
                    COMPOSE_FILE=\$(cat .compose_file)
                else
                    COMPOSE_FILE="docker-compose.yml"
                fi
                
                echo "Usando arquivo: \$COMPOSE_FILE"
                
                echo "--- Logs do API Gateway ---"
                docker-compose -f \$COMPOSE_FILE logs --tail=30 api-gateway 2>/dev/null || echo "Serviço não encontrado"
                
                echo "--- Logs do SVC Auth ---"
                docker-compose -f \$COMPOSE_FILE logs --tail=30 svc-auth 2>/dev/null || echo "Serviço não encontrado"
                
                echo "--- Status dos Containers ---"
                docker ps -a --filter "name=kealex" --filter "name=svc-" --filter "name=api-gateway" || true
                
                echo "--- Uso de Recursos ---"
                df -h || true
                free -h || true
                
                echo "--- Portas em Uso ---"
                netstat -tlnp | grep :8000 || ss -tlnp | grep :8000 || echo "Porta 8000 livre"
            """
        }
    }
}
