pipeline {
    agent any

    environment {
        REGISTRY     = "registry.kealex.io"
        IMAGE_PREFIX = "${REGISTRY}/kealex"
        TAG          = "${env.BUILD_NUMBER}"
        SECRET_KEY   = credentials('kealex-secret-key')
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
                stage('api-gateway')    { steps { sh "docker build -t ${IMAGE_PREFIX}/api-gateway:${TAG} ./api-gateway" } }
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
                    for svc in svc-auth svc-processos svc-documentos svc-financeiro svc-prazos svc-usuarios api-gateway; do
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
                sh "SECRET_KEY=${SECRET_KEY} TAG=${TAG} docker compose up -d --build"
            }
        }
    }

    post {
        always {
            sh """
                for svc in svc-auth svc-processos svc-documentos svc-financeiro svc-prazos svc-usuarios api-gateway; do
                    docker rmi ${IMAGE_PREFIX}/\$svc:${TAG} || true
                done
            """
        }
        failure { echo "Pipeline falhou — verifique os logs acima." }
    }
}
