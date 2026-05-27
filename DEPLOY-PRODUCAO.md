# Deploy Kealex em Produção - Usando Traefik Existente

## Pré-requisitos

1. **Traefik deve estar rodando** na rede `easypanel`
2. **Rede easypanel deve existir**
3. **Domínio srv1023256.hstgr.cloud deve apontar para o servidor**

## Verificação do Ambiente

```bash
# 1. Verificar se Traefik está rodando
docker ps | grep traefik

# 2. Verificar rede easypanel
docker network ls | grep easypanel

# 3. Executar script de verificação
chmod +x check-traefik.sh
./check-traefik.sh
```

## Deploy do Kealex

```bash
# 1. Configurar variáveis de ambiente
export SECRET_KEY="sua-chave-secreta-aqui"
export DATABASE_URL="mysql+pymysql://user:pass@host/db"

# 2. Deploy completo
docker-compose up -d --build

# 3. Verificar status
docker-compose ps

# 4. Verificar logs
docker-compose logs -f kealex-api-gateway
```

## Testes

```bash
# 1. Health check direto (porta 8000)
curl http://localhost:8000/health

# 2. Health check via Traefik
curl http://srv1023256.hstgr.cloud/kealex/health

# 3. API Gateway direto
curl http://localhost:8000/

# 4. API Gateway via Traefik
curl http://srv1023256.hstgr.cloud/kealex/

# 5. Endpoint de auth direto
curl http://localhost:8000/v1/lex/auth/me

# 6. Endpoint de auth via Traefik
curl http://srv1023256.hstgr.cloud/kealex/v1/lex/auth/me
```

## URLs Finais

### Acesso Direto (Porta 8000)
- **API Base**: `http://localhost:8000/v1/lex/`
- **Health Check**: `http://localhost:8000/health`
- **Auth**: `http://localhost:8000/v1/lex/auth/`
- **Processos**: `http://localhost:8000/v1/lex/processos/`

### Acesso via Traefik
- **API Base**: `http://srv1023256.hstgr.cloud/kealex/v1/lex/`
- **Health Check**: `http://srv1023256.hstgr.cloud/kealex/health`
- **Auth**: `http://srv1023256.hstgr.cloud/kealex/v1/lex/auth/`
- **Processos**: `http://srv1023256.hstgr.cloud/kealex/v1/lex/processos/`

## Troubleshooting

### Se o Traefik não estiver rodando:

```bash
# Criar rede se não existir
docker network create easypanel

# Iniciar Traefik básico
docker run -d \
  --name traefik \
  --restart unless-stopped \
  -p 80:80 -p 443:443 -p 8080:8080 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  --network easypanel \
  traefik:v2.10 \
  --api.dashboard=true \
  --api.insecure=true \
  --providers.docker=true \
  --providers.docker.exposedbydefault=false \
  --entrypoints.web.address=:80 \
  --entrypoints.websecure.address=:443
```

### Se houver conflitos de porta:

```bash
# Verificar o que está usando as portas
netstat -tlnp | grep -E ":(80|443)"

# Parar serviços conflitantes se necessário
sudo systemctl stop nginx  # se nginx estiver rodando no host
sudo systemctl stop apache2  # se apache estiver rodando no host
```

### Logs úteis:

```bash
# Logs do Traefik
docker logs traefik

# Logs do Kealex Gateway
docker logs kealex-api-gateway

# Logs de um microserviço específico
docker logs kealex-svc-auth
```

## Configuração Atual

O docker-compose.yml está configurado para:

- ✅ **Usar Traefik existente** (não cria novo container)
- ✅ **Rede easypanel externa** (conecta ao Traefik existente)
- ✅ **Rede interna kealex-internal** (comunicação entre microserviços)
- ✅ **Roteamento isolado** (`/kealex` prefix)
- ✅ **SSL automático** (via Traefik)
- ✅ **CORS configurado**
- ✅ **Health checks**