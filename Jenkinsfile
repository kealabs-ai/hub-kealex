pipeline {
    agent any

    environment {
        PROJETO        = 'hubkealex'
        DEPLOY_PATH    = '/var/jenkins_home/apps/hubkealex'
        GIT_REPO       = 'https://github.com/kealabs-ai/hub-kealex.git'
        GIT_BRANCH     = 'master'
        DOCKER         = '/var/jenkins_home/docker'
    }

    stages {

        // ── 1. PREPARAR AMBIENTE ──────────────────────────────────────────
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

                    # Sobrescrever com arquivos do workspace (alterações locais commitadas via SCM)
                    cp -f $WORKSPACE/docker-compose.yml $DEPLOY_PATH/docker-compose.yml
                    cp -f $WORKSPACE/app/main.py $DEPLOY_PATH/app/main.py
                    echo "  ✔ Arquivos sincronizados do workspace"
                '''
            }
        }

        // ── 2. GARANTIR DOCKER BUILDX ─────────────────────────────────────
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

        // ── 3. BUILD E DEPLOY ─────────────────────────────────────────────
        stage('Deploy') {
            steps {
                sh '''
                    set -e
                    cd $DEPLOY_PATH

                    echo "▶ Garantindo rede kealabs-net..."
                    $DOCKER network inspect kealabs-net >/dev/null 2>&1 || \
                        $DOCKER network create kealabs-net

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

        // ── 4. HEALTH CHECK ───────────────────────────────────────────────
        stage('Health Check') {
            steps {
                sh '''
                    echo "▶ Aguardando container ficar healthy..."

                    for i in 1 2 3 4 5 6 7 8 9 10; do
                        HEALTH_STATUS=$($DOCKER inspect --format='{{.State.Health.Status}}' hubkealex 2>/dev/null || echo "none")

                        echo "  Tentativa $i/10: Status = $HEALTH_STATUS"

                        if [ "$HEALTH_STATUS" = "healthy" ]; then
                            echo "  ✔ Container → HEALTHY"
                            exit 0
                        fi

                        if [ $i -lt 10 ]; then
                            sleep 2
                        fi
                    done

                    echo "  ✘ Container não ficou healthy após 10 tentativas"
                    echo "▶ Logs do container hubkealex:"
                    $DOCKER logs hubkealex | tail -30
                    echo "▶ Status dos containers:"
                    $DOCKER ps -a --filter "name=hubkealex"
                    exit 1
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
