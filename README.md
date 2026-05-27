# hubKealex — Backend Microserviços

Backend do sistema Kealex em arquitetura de microserviços Python/FastAPI.

## Serviços

| Serviço | Responsabilidade | Porta interna |
|---|---|---|
| `api-gateway` | Nginx — roteamento único na porta 8000 | 8000 |
| `svc-auth` | Login JWT | 8000 |
| `svc-processos` | CRUD processos | 8000 |
| `svc-documentos` | CRUD documentos | 8000 |
| `svc-financeiro` | CRUD honorários + dashboard | 8000 |
| `svc-prazos` | CRUD prazos + vencendo | 8000 |
| `svc-usuarios` | CRUD usuários (admin only) | 8000 |
| `svc-configuracoes` | CRUD configurações sistema | 8000 |
| `svc-escritorios` | CRUD escritórios/firmas | 8000 |

## Subir localmente

```bash
cp .env.example .env   # ajuste SECRET_KEY
docker compose up --build
```

Frontend (ViewKealex) aponta para `http://localhost:8000` via proxy Vite.

## Usuário padrão

- Email: `admin@kealex.com`
- Senha: `admin123`

## Arquitetura

### Multitenancy
- Todas as tabelas incluem `tenant_id` para isolamento de dados
- JWT tokens carregam `tenant_id` para filtragem automática
- Usuários pertencem a um tenant específico

### Auditoria
- Todas as tabelas incluem `user_id` (usuário que criou/modificou)
- Todas as tabelas incluem `escritorio_id` (escritório associado)
- Timestamps automáticos (`created_at`, `updated_at`)

### Endpoints
- Padrão GET/POST (não REST tradicional)
- POST para creates, updates e deletes
- Sufixos: `/get`, `/update`, `/delete`
- **Base URL Direta**: `http://localhost:8000/v1/lex/`
- **Base URL via Traefik**: `https://srv1023256.hstgr.cloud/kealex/v1/lex/`

```
# Acesso direto (porta 8000)
POST   http://localhost:8000/v1/lex/auth/login
GET    http://localhost:8000/v1/lex/auth/me

# Acesso via Traefik HTTPS
POST   https://srv1023256.hstgr.cloud/kealex/v1/lex/auth/login
GET    https://srv1023256.hstgr.cloud/kealex/v1/lex/auth/me

GET    https://srv1023256.hstgr.cloud/kealex/v1/lex/processos
POST   https://srv1023256.hstgr.cloud/kealex/v1/lex/processos
POST   https://srv1023256.hstgr.cloud/kealex/v1/lex/processos/get
POST   https://srv1023256.hstgr.cloud/kealex/v1/lex/processos/update
POST   https://srv1023256.hstgr.cloud/kealex/v1/lex/processos/delete

GET    /v1/lex/documentos
GET    /v1/lex/documentos/processo/:processoId
POST   /v1/lex/documentos
POST   /v1/lex/documentos/get
POST   /v1/lex/documentos/update
POST   /v1/lex/documentos/delete

GET    /v1/lex/financeiro
GET    /v1/lex/financeiro/dashboard
POST   /v1/lex/financeiro
POST   /v1/lex/financeiro/get
POST   /v1/lex/financeiro/update
POST   /v1/lex/financeiro/delete

GET    /v1/lex/prazos
GET    /v1/lex/prazos/vencendo?dias=7
GET    /v1/lex/prazos/processo/:processoId
POST   /v1/lex/prazos
POST   /v1/lex/prazos/get
POST   /v1/lex/prazos/update
POST   /v1/lex/prazos/delete

GET    /v1/lex/usuarios?role=
POST   /v1/lex/usuarios
POST   /v1/lex/usuarios/get
POST   /v1/lex/usuarios/update
POST   /v1/lex/usuarios/delete

GET    /v1/lex/escritorios
POST   /v1/lex/escritorios
POST   /v1/lex/escritorios/get
POST   /v1/lex/escritorios/update
POST   /v1/lex/escritorios/delete

GET    /v1/lex/clientes
POST   /v1/lex/clientes
POST   /v1/lex/clientes/get
POST   /v1/lex/clientes/update
POST   /v1/lex/clientes/delete

GET    /v1/lex/configuracoes/geral
POST   /v1/lex/configuracoes/geral
GET    /v1/lex/configuracoes/cdn
POST   /v1/lex/configuracoes/cdn
GET    /v1/lex/configuracoes/database
POST   /v1/lex/configuracoes/database
GET    /v1/lex/configuracoes/ia
GET    /v1/lex/configuracoes/ia/modelos
GET    /v1/lex/configuracoes/ia/ativa
POST   /v1/lex/configuracoes/ia
GET    /v1/lex/configuracoes/usuarios
POST   /v1/lex/configuracoes/usuarios
GET    /v1/lex/configuracoes/seguranca
POST   /v1/lex/configuracoes/seguranca
GET    /v1/lex/configuracoes/notificacoes
POST   /v1/lex/configuracoes/notificacoes
```

## CI/CD (Jenkins)

O `Jenkinsfile` executa:
1. Build paralelo de todas as imagens
2. Teste de sintaxe e configuração do nginx
3. Smoke test de importação
4. Validação do nginx após deploy
5. Health checks completos (nginx + microserviços)
6. Push para registry (branch `main`)
7. Deploy via `docker compose` (branch `main`)

Configure as credentials no Jenkins:
- `kealex-secret-key` — Secret text com o valor de SECRET_KEY
- `registry-creds` — Username/Password do registry Docker

**Documentação detalhada:** [JENKINS_NGINX.md](JENKINS_NGINX.md)

## Testes API (Postman)

Coleções completas para testar todas as APIs:

```bash
cd postman
# Importar no Postman:
# - Kealex-Processos-API.postman_collection.json
# - Kealex-Environment.postman_environment.json

# Ou executar via Newman (CLI):
npm install -g newman
./run-tests.bat  # Windows
```

**Coleções disponíveis:**
- `Kealex-Processos-API` — CRUD completo de processos
- `Kealex-Testes-Avancados` — Testes de performance e segurança

## Configuração de IA

### Providers Suportados
- **Cerebras**: Modelos Llama otimizados
- **Groq**: Modelos Llama e Gemma com alta velocidade

### Modelos Disponíveis

**Cerebras:**
- `llama-3.3-70b` (padrão)
- `llama-3.1-70b`
- `llama-3.1-8b`

**Groq:**
- `llama-3.3-70b-versatile`
- `llama-3.1-70b-versatile`
- `llama-3.1-8b-instant`
- `llama-3.2-90b-text-preview`
- `llama-3.2-11b-text-preview`
- `llama-3.2-3b-preview`
- `llama-3.2-1b-preview`
- `gemma2-9b-it`
- `gemma-7b-it`

### Migração de Modelos Descontinuados

Se você estiver usando modelos Groq descontinuados, execute:

```bash
cd migrations
./update_groq_models.bat  # Windows
# ou
mysql -h host -u user -p database < update_groq_models.sql  # Linux/Mac
```

**Modelos migrados automaticamente:**
- `mixtral-8x7b-32768` → `llama-3.1-70b-versatile`
- `llama2-70b-4096` → `llama-3.1-70b-versatile`
- `gemma-7b-it` → `gemma2-9b-it`
