pipeline {
    agent any

    environment {
        PROJETO = 'hubkealex'
        DOCKER  = '/var/jenkins_home/docker'
    }

    stages {

        // ── 1. PREPARAR AMBIENTE ────────────────────────────────────────────────────────────────
        stage('Prepare') {
            steps {
                dir("${env.WORKSPACE}") {
                    deleteDir()
                    checkout([
                        $class: 'GitSCM',
                        branches: [[name: '*/master']],
                        userRemoteConfigs: [[url: 'https://github.com/kealabs-ai/hubkealex.git']]
                    ])
                    sh 'echo "✔ Repositório clonado com sucesso" && pwd && ls -la | head -10'
                }
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
                    cd ${WORKSPACE}

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
                    echo "▶ Aguardando containers subirem (15s)..."
                    sleep 15

                    echo "▶ Testando health check local..."
                    for i in 1 2 3 4 5; do
                        STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
                            --max-time 5 \
                            http://localhost:8000/health || echo "000")
                        if [ "$STATUS" = "200" ]; then
                            echo "  ✔ /health → OK (local)"
                            break
                        fi
                        echo "  Tentativa $i/5 falhou, aguardando..."
                        sleep 3
                    done

                    echo "▶ Testando health check via Traefik..."
                    STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
                        --max-time 5 \
                        https://srv1023256.hstgr.cloud/v1/lex/health || echo "000")

                    if [ "$STATUS" = "200" ]; then
                        echo "  ✔ /v1/lex/health → OK (Traefik)"
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