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
                        ENV_BACKUP=""
                        if [ -f .env ]; then
                            ENV_BACKUP=$(mktemp)
                            cp .env "$ENV_BACKUP"
                        fi
                        git fetch origin
                        git reset --hard origin/$GIT_BRANCH
                        if [ -n "$ENV_BACKUP" ]; then
                            cp "$ENV_BACKUP" .env
                            rm -f "$ENV_BACKUP"
                        fi
                    else
                        git clone -b $GIT_BRANCH $GIT_REPO .
                    fi

                    echo "  ✔ Repositório atualizado em $DEPLOY_PATH"

                    cp -f $WORKSPACE/docker-compose.yml $DEPLOY_PATH/docker-compose.yml
                    cp -f $WORKSPACE/app/main.py $DEPLOY_PATH/app/main.py
                    mkdir -p $DEPLOY_PATH/svc-cobrancas
                    cp -f $WORKSPACE/svc-cobrancas/main.py $DEPLOY_PATH/svc-cobrancas/main.py
                    cp -f $WORKSPACE/svc-cobrancas/Dockerfile $DEPLOY_PATH/svc-cobrancas/Dockerfile
                    cp -f $WORKSPACE/svc-cobrancas/requirements.txt $DEPLOY_PATH/svc-cobrancas/requirements.txt
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
                    sleep 2

                    echo "▶ Limpando containers órfãos..."
                    $DOCKER container prune -f 2>/dev/null || true

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
                    echo "▶ Aguardando containers ficarem healthy..."

                    cd "$DEPLOY_PATH"
                    COMPOSE_FILE="docker-compose.yml"
                    SERVICES="rabbitmq hubkealex kealex-svc-auth kealex-svc-auth-worker kealex-svc-usuarios kealex-svc-escritorios svc-activities svc-cobrancas kealex-svc-configuracoes svc-arquivos"

                    for SERVICE in $SERVICES; do
                        echo "Verificando serviço Compose $SERVICE..."
                        SERVICE_READY=0
                        for i in 1 2 3 4 5 6 7 8 9 10; do
                            CONTAINER_IDS=$($DOCKER compose -f "$COMPOSE_FILE" -p "$PROJETO" ps -q "$SERVICE")
                            ALL_READY=1
                            if [ -z "$CONTAINER_IDS" ]; then
                                ALL_READY=0
                            else
                                for CONTAINER_ID in $CONTAINER_IDS; do
                                    CONTAINER_STATE=$($DOCKER inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$CONTAINER_ID" 2>/dev/null || echo "missing")
                                    echo "    Tentativa $i/10: $SERVICE ($CONTAINER_ID) = $CONTAINER_STATE"
                                    if [ "$CONTAINER_STATE" != "healthy" ] && [ "$CONTAINER_STATE" != "running" ]; then ALL_READY=0; fi
                                done
                            fi
                            if [ "$ALL_READY" -eq 1 ]; then SERVICE_READY=1; break; fi
                            sleep 3
                        done
                        if [ "$SERVICE_READY" -ne 1 ]; then
                            echo "Serviço $SERVICE não iniciou corretamente"
                            $DOCKER compose -f "$COMPOSE_FILE" -p "$PROJETO" ps "$SERVICE" || true
                            $DOCKER compose -f "$COMPOSE_FILE" -p "$PROJETO" logs --no-color --tail=80 "$SERVICE" || true
                            exit 1
                        fi
                    done
                    echo "Todos os serviços estão saudáveis ou em execução"
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
                    /var/jenkins_home/docker ps --filter "name=hubkealex" --filter "name=svc-cobrancas" || true
                '''
            }
        }
    }
}
