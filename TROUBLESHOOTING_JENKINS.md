# Resumo das Melhorias no Jenkinsfile

## Problema Identificado

O pipeline estava falhando com `exit code 125` porque o `docker-compose up` estava falhando silenciosamente sem mostrar o erro real.

## Soluções Implementadas

### 1. Validação do docker-compose antes do deploy

```bash
docker-compose -f $COMPOSE_FILE config --quiet || {
    echo "[ERRO] Arquivo docker-compose inválido!"
    docker-compose -f $COMPOSE_FILE config
    exit 1
}
```

**Benefício:** Detecta erros de sintaxe no docker-compose.yml antes de tentar fazer o deploy.

### 2. Captura de erro do docker-compose up

```bash
if docker-compose -f $COMPOSE_FILE -p ${COMPOSE_PROJECT_NAME} up -d --build 2>&1; then
    echo "[OK] Containers iniciados com sucesso"
else
    EXIT_CODE=$?
    echo "[ERRO] Falha ao iniciar containers (exit code: $EXIT_CODE)"
    echo "Verificando logs de erro..."
    docker-compose -f $COMPOSE_FILE -p ${COMPOSE_PROJECT_NAME} logs --tail=50
    exit $EXIT_CODE
fi
```

**Benefício:** Captura o output de erro do docker-compose e mostra os logs imediatamente.

### 3. Verificação de containers com falha

```bash
FAILED=$(docker-compose -f $COMPOSE_FILE -p ${COMPOSE_PROJECT_NAME} ps --filter "status=exited" --services)
if [ -n "$FAILED" ]; then
    echo "[AVISO] Containers com falha: $FAILED"
    for service in $FAILED; do
        echo "--- Logs de $service ---"
        docker-compose -f $COMPOSE_FILE -p ${COMPOSE_PROJECT_NAME} logs --tail=30 $service
    done
fi
```

**Benefício:** Identifica quais containers falharam e mostra seus logs automaticamente.

### 4. Diagnóstico aprimorado no bloco failure

Adicionado ao bloco `post { failure }`:

```bash
echo "--- Validando docker-compose ---"
docker-compose -f $COMPOSE_FILE config 2>&1 || echo "Erro na validação do docker-compose"

echo "--- Verificando imagens ---"
docker images | grep kealex || echo "Nenhuma imagem kealex encontrada"

echo "--- Tentando iniciar manualmente para debug ---"
docker-compose -f $COMPOSE_FILE -p ${COMPOSE_PROJECT_NAME} up --no-start 2>&1 || echo "Falha ao criar containers"
```

**Benefício:** Fornece informações detalhadas sobre o que causou a falha.

## Testes do Nginx Implementados

### Stage: Test Nginx Config

Valida a configuração do nginx antes do deploy:

```groovy
stage('Test Nginx Config') {
    steps {
        sh "docker run --rm ${IMAGE_PREFIX}/api-gateway:${TAG} nginx -t"
        sh "docker run --rm ${IMAGE_PREFIX}/api-gateway:${TAG} ls -la /etc/nginx/conf.d/"
    }
}
```

### Stage: Validate Nginx

Valida o nginx após o deploy:

```groovy
stage('Validate Nginx') {
    steps {
        sh "docker-compose exec -T api-gateway nginx -t"
        sh "docker-compose exec -T api-gateway ps aux | grep nginx"
        sh "docker-compose logs --tail=20 api-gateway"
    }
}
```

### Health Check com testes do nginx

```bash
# Teste do health endpoint
curl -f http://localhost:8000/health

# Teste de roteamento
curl http://localhost:8000/v1/lex/auth/me

# Teste de login via nginx
curl -X POST http://localhost:8000/v1/lex/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@kealex.com", "senha": "admin123"}'
```

## Possíveis Causas do Exit Code 125

O exit code 125 do Docker geralmente indica:

1. **Erro de sintaxe no comando docker-compose**
   - Solução: Validação com `docker-compose config`

2. **Imagens não encontradas**
   - Solução: Verificação de imagens no diagnóstico

3. **Problemas com variáveis de ambiente**
   - Solução: Validação do arquivo .env

4. **Conflito de nomes de containers**
   - Solução: Limpeza completa antes do deploy

5. **Problemas de rede Docker**
   - Solução: Remoção de redes antigas

6. **Arquivo docker-compose.yml inválido**
   - Solução: Validação com `docker-compose config`

## Como Debugar

### 1. Verificar logs do Jenkins

Procure por:
- `[ERRO] Arquivo docker-compose inválido!`
- `[ERRO] Falha ao iniciar containers (exit code: 125)`
- Output do `docker-compose config`

### 2. Verificar se as imagens existem

```bash
docker images | grep kealex
```

Todas as imagens devem estar presentes:
- kealex/api-gateway
- kealex/svc-auth
- kealex/svc-processos
- etc.

### 3. Testar docker-compose localmente

```bash
# Validar sintaxe
docker-compose -f docker-compose.yml config

# Tentar criar containers sem iniciar
docker-compose -f docker-compose.yml up --no-start

# Iniciar com logs visíveis
docker-compose -f docker-compose.yml up
```

### 4. Verificar variáveis de ambiente

```bash
# No Jenkins, verificar se as variáveis estão definidas
echo $SECRET_KEY
echo $DATABASE_URL
echo $TAG
```

### 5. Verificar healthchecks

O docker-compose.yml usa healthchecks que podem estar causando problemas:

```yaml
healthcheck:
  test: ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

Se curl não estiver disponível nos containers, os healthchecks falharão.

## Próximos Passos

Se o erro persistir após essas mudanças:

1. **Verificar output do `docker-compose config`** no log de erro
2. **Verificar se todas as imagens foram construídas** no stage "Build Images"
3. **Testar docker-compose manualmente** no servidor Jenkins
4. **Verificar se há conflitos de porta** (porta 8000)
5. **Verificar recursos do sistema** (memória, disco)

## Documentação Relacionada

- [JENKINS_NGINX.md](JENKINS_NGINX.md) - Documentação completa do nginx no Jenkins
- [api-gateway/README.md](api-gateway/README.md) - Documentação do API Gateway
- [README.md](README.md) - Documentação principal do projeto
