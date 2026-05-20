pipeline {
    agent any

    environment {
        REGISTRY     = "registry.kealex.io"
        IMAGE_PREFIX = "${REGISTRY}/kealex"
        TAG          = "${env.BUILD_NUMBER}"
    }

    stages {
        stage('Checkout') {
            steps { checkout scm }
        }

        stage('Build Images') {
            parallel {
                stage('svc-auth')       { steps { sh "docker build -t ${IMAGE_PREFIX}/svc-auth:${TAG} ./svc-auth" } }
                stage('svc-processos')  { steps { sh "docker build -t ${IMAGE_PREFIX}/svc-processos:${TAG} ./svc-processos" } }
                stage('svc-documentos') { steps { sh "docker build -t ${IMAGE_PREFIX}/svc-documentos:${TAG} ./svc-documentos" } }
                stage('svc-financeiro') { steps { sh "docker build -t ${IMAGE_PREFIX}/svc-financeiro:${TAG} ./svc-financeiro" } }
                stage('svc-prazos')     { steps { sh "docker build -t ${IMAGE_PREFIX}/svc-prazos:${TAG} ./svc-prazos" } }
                stage('svc-usuarios')   { steps { sh "docker build -t ${IMAGE_PREFIX}/svc-usuarios:${TAG} ./svc-usuarios" } }
                stage('svc-clientes')   { steps { sh "docker build -t ${IMAGE_PREFIX}/svc-clientes:${TAG} ./svc-clientes" } }
                stage('svc-configuracoes') { steps { sh "docker build -t ${IMAGE_PREFIX}/svc-configuracoes:${TAG} ./svc-configuracoes" } }
                stage('svc-escritorios') { steps { sh "docker build -t ${IMAGE_PREFIX}/svc-escritorios:${TAG} ./svc-escritorios" } }
                stage('api-gateway')    { steps { sh "docker build -t ${IMAGE_PREFIX}/api-gateway:${TAG} ./api-gateway" } }
            }
        }

        stage('Show API Endpoints') {
            steps {
                echo "=== KEALEX API ENDPOINTS ==="
                echo "Base URL: http://localhost:8000/v1/lex"
                echo ""
                echo "Auth Service:"
                echo "  POST /v1/lex/auth/login"
                echo "  GET  /v1/lex/auth/me"
                echo ""
                echo "Processos Service:"
                echo "  GET    /v1/lex/processos"
                echo "  POST   /v1/lex/processos"
                echo "  POST   /v1/lex/processos/get"
                echo "  POST   /v1/lex/processos/update"
                echo "  POST   /v1/lex/processos/delete"
                echo ""
                echo "Documentos Service:"
                echo "  GET    /v1/lex/documentos"
                echo "  POST   /v1/lex/documentos"
                echo "  GET    /v1/lex/documentos/processo/{processoId}"
                echo ""
                echo "Financeiro Service:"
                echo "  GET    /v1/lex/financeiro"
                echo "  GET    /v1/lex/financeiro/dashboard"
                echo "  POST   /v1/lex/financeiro"
                echo ""
                echo "Prazos Service:"
                echo "  GET    /v1/lex/prazos"
                echo "  GET    /v1/lex/prazos/vencendo?dias=7"
                echo "  GET    /v1/lex/prazos/processo/{processoId}"
                echo "  POST   /v1/lex/prazos"
                echo ""
                echo "Usuários Service:"
                echo "  GET    /v1/lex/usuarios"
                echo "  POST   /v1/lex/usuarios"
                echo ""
                echo "Escritórios Service:"
                echo "  GET    /v1/lex/escritorios"
                echo "  POST   /v1/lex/escritorios"
                echo ""
                echo "Clientes Service:"
                echo "  GET    /v1/lex/clientes"
                echo "  POST   /v1/lex/clientes"
                echo ""
                echo "Configurações Service:"
                echo "  GET    /v1/lex/configuracoes/geral"
                echo "  POST   /v1/lex/configuracoes/geral"
                echo "  GET    /v1/lex/configuracoes/ia"
                echo "  POST   /v1/lex/configuracoes/ia"
                echo "================================"
            }
        }

        stage('Test') {
            parallel {
                stage('svc-auth') {
                    steps {
                        sh """
                            docker run --rm \
                              -e DATABASE_URL=sqlite:///./test.db \
                              -e SECRET_KEY=test \
                              ${IMAGE_PREFIX}/svc-auth:${TAG} \
                              python -c "import main; print('OK')"
                        """
                    }
                }
                stage('svc-processos') {
                    steps {
                        sh """
                            docker run --rm \
                              -e DATABASE_URL=sqlite:///./test.db \
                              -e SECRET_KEY=test \
                              ${IMAGE_PREFIX}/svc-processos:${TAG} \
                              python -c "import main; print('OK')"
                        """
                    }
                }
            }
        }

        stage('Push Images') {
            when { branch 'main' }
            steps {
                withCredentials([usernamePassword(credentialsId: 'registry-creds', usernameVariable: 'USER', passwordVariable: 'PASS')]) {
                    sh "echo $PASS | docker login ${REGISTRY} -u $USER --password-stdin"
                }
                sh """
                    for svc in svc-auth svc-processos svc-documentos svc-financeiro svc-prazos svc-usuarios svc-clientes svc-configuracoes svc-escritorios api-gateway; do
                        docker push ${IMAGE_PREFIX}/\$svc:${TAG}
                        docker tag  ${IMAGE_PREFIX}/\$svc:${TAG} ${IMAGE_PREFIX}/\$svc:latest
                        docker push ${IMAGE_PREFIX}/\$svc:latest
                    done
                """
            }
        }

        stage('Deploy') {
            when { branch 'main' }
            steps {
                withCredentials([string(credentialsId: 'kealex-secret-key', variable: 'SECRET_KEY')]) {
                    sh "SECRET_KEY=${SECRET_KEY} TAG=${TAG} docker compose up -d --build"
                }
            }
        }
    }

    post {
        failure { echo "Pipeline falhou — verifique os logs acima." }
    }
}
