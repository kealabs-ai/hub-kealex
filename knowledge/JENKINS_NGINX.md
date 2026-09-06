# Configuração do Nginx no Jenkins

Este documento descreve as melhorias implementadas no Jenkinsfile para garantir que o nginx (api-gateway) seja testado e validado corretamente durante o processo de CI/CD.

## Mudanças Implementadas

### 1. Novo Stage: Test Nginx Config

Adicionado após o stage "Test Images" para validar a configuração do nginx antes do deploy:

```groovy
stage('Test Nginx Config') {
    steps {
        // Testa sintaxe da configuração do nginx
        docker run --rm ${IMAGE_PREFIX}/api-gateway:${TAG} nginx -t
        
        // Verifica se arquivos de configuração existem
        docker run --rm ${IMAGE_PREFIX}/api-gateway:${TAG} ls -la /etc/nginx/conf.d/
    }
}
```

**Benefícios:**
- Detecta erros de sintaxe no nginx.conf antes do deploy
- Valida que os arquivos de configuração foram copiados corretamente
- Falha rápido se houver problemas de configuração

### 2. Deploy Simplificado com docker-compose

O stage "Deploy" foi simplificado para usar `docker-compose` em vez de `docker run` manual:

```groovy
stage('Deploy') {
    steps {
        // Usa docker-compose para gerenciar todos os containers
        docker-compose -f $COMPOSE_FILE -p ${COMPOSE_PROJECT_NAME} up -d --build
    }
}
```

**Benefícios:**
- Gerenciamento consistente de containers
- Respeita dependências entre serviços
- Usa healthchecks definidos no docker-compose.yml
- Mais fácil de debugar

### 3. Novo Stage: Validate Nginx

Adicionado após o deploy para validar que o nginx está funcionando:

```groovy
stage('Validate Nginx') {
    steps {
        // Verifica se nginx está rodando
        docker-compose ps api-gateway
        
        // Testa configuração do nginx
        docker-compose exec -T api-gateway nginx -t
        
        // Verifica logs do nginx
        docker-compose logs --tail=20 api-gateway
        
        // Verifica processos nginx
        docker-compose exec -T api-gateway ps aux | grep nginx
    }
}
```

**Benefícios:**
- Confirma que o nginx iniciou corretamente
- Valida que a configuração está ativa
- Detecta problemas de inicialização rapidamente

### 4. Health Check Melhorado

O stage "Health Check" foi aprimorado com testes específicos do nginx:

#### 4.1 Teste do Health Endpoint do Nginx

```bash
curl -f http://localhost:8000/health
```

- Testa o endpoint `/health` definido no nginx.conf
- Confirma que o nginx está respondendo na porta 8000
- Falha se o nginx não responder em 15 tentativas

#### 4.2 Teste de Roteamento do Nginx

```bash
curl http://localhost:8000/v1/lex/auth/me
```

- Testa se o nginx está roteando corretamente para os microserviços
- Valida que os upstreams estão configurados
- Aceita HTTP 401 (não autorizado) como sucesso, pois confirma que o serviço está respondendo

#### 4.3 Teste de Login via Nginx

```bash
curl -X POST http://localhost:8000/v1/lex/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@kealex.com", "senha": "admin123"}'
```

- Testa o fluxo completo: nginx → svc-auth → banco de dados
- Valida que o proxy_pass está funcionando
- Confirma que os headers estão sendo passados corretamente

## Fluxo de Validação do Nginx

```
1. Build Images
   ↓
2. Test Nginx Config (NOVO)
   - Valida sintaxe do nginx.conf
   - Verifica arquivos de configuração
   ↓
3. Deploy
   - Usa docker-compose para deploy consistente
   ↓
4. Validate Nginx (NOVO)
   - Confirma que nginx iniciou
   - Testa configuração ativa
   - Verifica processos
   ↓
5. Health Check (MELHORADO)
   - Testa /health endpoint
   - Testa roteamento para microserviços
   - Testa login completo via nginx
```

## Diagnóstico de Problemas

### Nginx não inicia

Se o nginx não iniciar, o Jenkins mostrará:

```
[ERRO] Nginx não respondeu após 15 tentativas

Diagnóstico do nginx:
<logs do container>

Status do container:
<status do docker-compose>

Processos no container:
<lista de processos>
```

**Soluções:**
1. Verificar logs do nginx no output do Jenkins
2. Verificar se a porta 8000 está livre
3. Validar sintaxe do nginx.conf localmente: `docker run --rm kealex/api-gateway nginx -t`

### Nginx inicia mas não roteia

Se o nginx iniciar mas não rotear corretamente:

```
[AVISO] Endpoint retornou: 502

Verificando configuração do nginx:
<primeiras 50 linhas do nginx.conf>
```

**Soluções:**
1. Verificar se os upstreams estão corretos no nginx.conf
2. Confirmar que os microserviços estão rodando: `docker-compose ps`
3. Testar conectividade entre containers: `docker network inspect kealex-network`

### Configuração do nginx inválida

Se houver erro de sintaxe no nginx.conf:

```
nginx: [emerg] unexpected "}" in /etc/nginx/conf.d/default.conf:45
nginx: configuration file /etc/nginx/conf.d/default.conf test failed
```

**Soluções:**
1. Validar nginx.conf localmente antes de commitar
2. Usar `nginx -t` para testar sintaxe
3. Verificar se todos os blocos `location` estão fechados corretamente

## Testes Locais

Antes de fazer push para o Jenkins, teste localmente:

### 1. Testar sintaxe do nginx

```bash
cd api-gateway
docker build -t test-nginx .
docker run --rm test-nginx nginx -t
```

### 2. Testar nginx completo

```bash
# Subir todos os serviços
docker-compose up -d

# Testar health endpoint
curl http://localhost:8000/health

# Testar roteamento
curl http://localhost:8000/v1/lex/auth/me

# Testar login
curl -X POST http://localhost:8000/v1/lex/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@kealex.com", "senha": "admin123"}'
```

### 3. Usar script de teste

```bash
# Windows
test-nginx.bat

# Linux/Mac
./test-nginx.sh
```

## Configuração do Nginx

### Arquivos Importantes

- `api-gateway/nginx.conf` - Configuração principal do nginx
- `api-gateway/nginx-ssl.conf` - Configuração com SSL para produção
- `api-gateway/Dockerfile` - Build do container nginx
- `api-gateway/switch-nginx.sh` - Script para alternar entre configurações

### Endpoints Configurados

Todos os endpoints são prefixados com `/v1/lex/`:

```nginx
location /v1/lex/auth { proxy_pass http://svc_auth; }
location /v1/lex/processos { proxy_pass http://svc_processos; }
location /v1/lex/documentos { proxy_pass http://svc_documentos; }
location /v1/lex/financeiro { proxy_pass http://svc_financeiro; }
location /v1/lex/prazos { proxy_pass http://svc_prazos; }
location /v1/lex/usuarios { proxy_pass http://svc_usuarios; }
location /v1/lex/configuracoes { proxy_pass http://svc_configuracoes; }
location /v1/lex/escritorios { proxy_pass http://svc_escritorios; }
location /v1/lex/clientes { proxy_pass http://svc_clientes; }
```

### Health Check Endpoint

```nginx
location /health {
    access_log off;
    return 200 "healthy\n";
    add_header Content-Type text/plain;
}
```

### CORS Headers

O nginx está configurado para adicionar headers CORS automaticamente:

```nginx
add_header Access-Control-Allow-Origin "*" always;
add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
add_header Access-Control-Allow-Headers "Authorization, Content-Type, X-Requested-With" always;
```

## Monitoramento

### Verificar Status do Nginx

```bash
# Via docker-compose
docker-compose ps api-gateway

# Via docker
docker ps --filter "name=api-gateway"

# Logs do nginx
docker-compose logs -f api-gateway
```

### Testar Configuração

```bash
# Dentro do container
docker-compose exec api-gateway nginx -t

# Ver configuração ativa
docker-compose exec api-gateway nginx -T
```

### Recarregar Configuração

```bash
# Recarregar sem downtime
docker-compose exec api-gateway nginx -s reload

# Reiniciar container
docker-compose restart api-gateway
```

## Troubleshooting

### Problema: Porta 8000 já em uso

```bash
# Verificar o que está usando a porta
sudo netstat -tlnp | grep :8000
# ou
sudo ss -tlnp | grep :8000

# Parar o processo ou mudar a porta no docker-compose.yml
```

### Problema: Nginx retorna 502 Bad Gateway

**Causas comuns:**
1. Microserviço não está rodando
2. Nome do upstream está errado
3. Microserviço não está na mesma rede Docker

**Soluções:**
```bash
# Verificar se todos os serviços estão rodando
docker-compose ps

# Verificar rede Docker
docker network inspect kealex-network

# Testar conectividade do nginx para o serviço
docker-compose exec api-gateway ping svc-auth
```

### Problema: Nginx retorna 404 Not Found

**Causas comuns:**
1. Rota não está configurada no nginx.conf
2. Prefixo `/v1/lex/` está faltando na URL

**Soluções:**
```bash
# Verificar rotas configuradas
docker-compose exec api-gateway cat /etc/nginx/conf.d/default.conf | grep location

# Testar com prefixo correto
curl http://localhost:8000/v1/lex/auth/me
```

## Referências

- [Nginx Documentation](https://nginx.org/en/docs/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [api-gateway/README.md](api-gateway/README.md) - Documentação específica do API Gateway
