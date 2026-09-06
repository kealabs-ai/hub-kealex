# Health Check Options for HubKealex Pipeline

## Opção 1: Python urllib no Jenkins (ATUAL - Recomendada)

### ✅ Vantagens
- ✔ Não requer modificação do docker-compose.yml
- ✔ Controle total sobre retry logic no Jenkins
- ✔ Logs detalhados de cada tentativa
- ✔ Compatível com imagem slim (Python built-in)
- ✔ Simples de debugar no pipeline

### ❌ Desvantagens
- ✗ Depende do Jenkins estar disponível
- ✗ Health check só roda na hora do deploy

### 📋 Como usar
1. Use o arquivo: `Jenkinsfile` (atual)
2. Use o arquivo: `docker-compose.yml` (sem healthcheck)
3. Execute: `docker-compose up -d --build`
4. Pipeline testa com: `python3 -c "import urllib.request; ..."`

### 🔍 Exemplo de Log
```
▶ Aguardando containers subirem (10s)...
▶ Testando health check via Python urllib...
  Tentativa 1/5: HTTP 000
  Tentativa 2/5: HTTP 000
  Tentativa 3/5: HTTP 200
  ✔ /k1/lex/health → OK (via Python)
```

---

## Opção 2: Docker Healthcheck Nativo

### ✅ Vantagens
- ✔ Health check contínuo (mesmo fora do deploy)
- ✔ Docker monitora automaticamente
- ✔ Status visível via `docker ps` (healthy/unhealthy)
- ✔ Orquestração automática em caso de falha
- ✔ Mais robusto em produção

### ❌ Desvantagens
- ✗ Requer modificação do docker-compose.yml
- ✗ Healthcheck roda continuamente (overhead)
- ✗ Menos controle sobre retry timing

### 📋 Como usar
1. Use o arquivo: `Jenkinsfile.healthcheck-native`
2. Use o arquivo: `docker-compose.healthcheck.yml`
3. Renomeie: `mv docker-compose.healthcheck.yml docker-compose.yml`
4. Execute: `docker-compose up -d --build`
5. Pipeline inspeciona com: `docker inspect --format='{{.State.Health.Status}}'`

### 🔍 Exemplo de Log
```
▶ Aguardando container ficar healthy...
  Tentativa 1/10: Status = starting
  Tentativa 2/10: Status = starting
  Tentativa 3/10: Status = healthy
  ✔ Container → HEALTHY
```

---

## Configuração de Healthcheck no docker-compose.yml

### Sintaxe Completa
```yaml
healthcheck:
  test: ["CMD", "python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/k1/lex/health', timeout=5)"]
  interval: 10s        # Testa a cada 10 segundos
  timeout: 5s          # Timeout de 5 segundos por teste
  retries: 3           # Máximo de 3 falhas antes de marcar unhealthy
  start_period: 15s    # Aguarda 15 segundos antes de primeiro teste
```

### Alternativas de Test
```yaml
# Opção A: Python urllib (Recomendada)
test: ["CMD", "python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/k1/lex/health', timeout=5)"]

# Opção B: wget (se instalado)
test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:8000/k1/lex/health"]

# Opção C: Script externo
test: ["CMD", "/app/healthcheck.sh"]
```

---

## Comparação Visual

| Aspecto | Opção 1 (Python urllib) | Opção 2 (Healthcheck) |
|---------|------------------------|----------------------|
| Setup | Simples | Média |
| Runtime | Sob demanda | Contínuo |
| Overhead | Baixo | Médio |
| Debug | Fácil | Médio |
| Produção | Bom | Excelente |
| Custo | Mínimo | Mínimo |

---

## Recomendação Final

### Use Opção 1 se:
- ✔ Você quer apenas validar deploy no Jenkins
- ✔ Quer máximo controle sobre health check
- ✔ Não precisa de monitoramento contínuo
- ✔ Quer manter docker-compose simples

### Use Opção 2 se:
- ✔ Quer monitoramento contínuo do container
- ✔ Está em ambiente de produção
- ✔ Precisa de orquestração automática (Swarm/K8s)
- ✔ Quer que Docker manage container lifecycle

---

## Teste Local

```bash
# Opção 1: Testar manualmente com Python
docker exec hubkealex python3 -c "import urllib.request; print(urllib.request.urlopen('http://hubkealex:8000/k1/lex/health', timeout=5).status)"

# Opção 2: Inspecionar healthcheck status
docker inspect --format='{{.State.Health.Status}}' hubkealex

# Ver história de healthcheck
docker inspect --format='{{json .State.Health}}' hubkealex | jq .
```

---

## Instalação de Opção 1 (ATUAL)

```bash
# Arquivos necessários:
# - Jenkinsfile (já configurado)
# - docker-compose.yml (sem healthcheck)

# Deploy:
cd /var/jenkins_home/apps/hubkealex
docker compose up -d --build

# Pipeline executará automaticamente o health check
```

---

## Instalação de Opção 2 (ALTERNATIVA)

```bash
# Substituir arquivos:
cp docker-compose.healthcheck.yml docker-compose.yml
cp Jenkinsfile.healthcheck-native Jenkinsfile

# Deploy:
cd /var/jenkins_home/apps/hubkealex
docker compose up -d --build

# Verificar status:
docker ps
# HEALTHY = ✔ OK
# unhealthy = ✘ ERRO
```
