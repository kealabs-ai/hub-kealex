pipeline {
    agent any

    environment {
        PROJETO        = 'hubkealex'
        DEPLOY_PATH    = '/var/jenkins_home/apps/hubkealex'
        GIT_REPO       = 'https://github.com/kealabs-ai/hubkealex.git'
        GIT_BRANCH     = 'main'
        DOCKER         = '/var/jenkins_home/docker'
    }

    stages {

        // ── 1. PREPARAR AMBIENTE ────────────────────────────────────────────────────────────────
        stage('Prepare') {
            steps {
                sh '''
                    set -e
                    mkdir -p $DEPLOY_PATH
                    cd $DEPLOY_PATH

                    if [ -d ".git" ]; then
                        git fetch origin
                        git reset --hard origin/$GIT_BRANCH
                    else
                        git clone -b $GIT_BRANCH $GIT_REPO .
                    fi

                    echo "  ✔ Repositório atualizado em $DEPLOY_PATH"
                '''
            }
        }

        // ── 3. GARANTIR DOCKER BUILDX ───────────────────────────────────────────────────────────
        stage('Ensure Buildx') {
            steps {
                sh '''
                    BUILDX_PATH="/var/jenkins_home/.docker/cli-plugins/docker-buildx"
                    if [ ! -f "$BUILDX_PATH" ]; then
                        echo "Instalando docker-buildx..."
                        mkdir -p /var/jenkins_home/.docker/cli-plugins
                        curl -fsSL "https://github.com/docker/buildx/releases/download/v0.17.1/buildx-v0.17.1.linux-amd64" \
                             -o "$BUILDX_PATH"
                        chmod +x "$BUILDX_PATH"
                        echo "  ✔ buildx instalado"
                    else
                        echo "  ✔ buildx já presente"
                    fi
                '''
            }
        }

        // ── 4. BUILD E DEPLOY ─────────────────────────────────────────────────────────────
        stage('Deploy') {
            steps {
                sh '''
                    set -e
                    cd $DEPLOY_PATH

                    echo "▶ Garantindo rede easypanel..."
                    $DOCKER network inspect easypanel >/dev/null 2>&1 || \
                        $DOCKER network create easypanel

                    echo "▶ Derrubando stack anterior..."
                    $DOCKER compose -f docker-compose.yml -p $PROJETO down --remove-orphans 2>/dev/null || true

                    echo "▶ Build e subida dos containers..."
                    $DOCKER compose -f docker-compose.yml -p $PROJETO up -d --build

                    echo "✅ Deploy concluído"
                '''
            }
        }

        // ── 5. HEALTH CHECK ───────────────────────────────────────────────────────────────
        stage('Health Check') {
            steps {
                sh '''
                    echo "▶ Aguardando containers subirem (10s)..."
                    sleep 10

                    STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
                        --max-time 5 \
                        https://srv1023256.hstgr.cloud/v1/lex/health || echo "000")

                    if [ "$STATUS" = "200" ]; then
                        echo "  ✔ /v1/lex/health → OK"
                    else
                        echo "  ✘ /v1/lex/health → HTTP $STATUS"
                        exit 1
                    fi
                '''
            }
        }

    }

    post {
        success {
            echo '✅ Deploy HubKealex realizado com sucesso!'
        }
        failure {
            echo '❌ Falha no deploy HubKealex!'
        }
        always {
            node('built-in') {
                sh '''
                    echo "▶ Estado final dos containers:"
                    /var/jenkins_home/docker ps --filter "name=hubkealex" || true

                '''
            }
        }
    }
}
