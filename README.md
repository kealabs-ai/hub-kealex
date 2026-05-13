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

```
POST   /auth/login
GET    /auth/me

GET    /processos
POST   /processos
GET    /processos/:id
PATCH  /processos/:id
DELETE /processos/:id

GET    /documentos
GET    /documentos/processo/:processoId
POST   /documentos
GET    /documentos/:id
PATCH  /documentos/:id
DELETE /documentos/:id

GET    /financeiro
GET    /financeiro/dashboard
POST   /financeiro
GET    /financeiro/:id
PATCH  /financeiro/:id
DELETE /financeiro/:id

GET    /prazos
GET    /prazos/vencendo?dias=7
GET    /prazos/processo/:processoId
POST   /prazos
GET    /prazos/:id
PATCH  /prazos/:id
DELETE /prazos/:id

GET    /usuarios?role=
POST   /usuarios
GET    /usuarios/:id
PATCH  /usuarios/:id
DELETE /usuarios/:id

GET    /escritorios
POST   /escritorios
GET    /escritorios/:id
PATCH  /escritorios/:id
DELETE /escritorios/:id

GET    /configuracoes/geral
POST   /configuracoes/geral
GET    /configuracoes/cdn
POST   /configuracoes/cdn
GET    /configuracoes/database
POST   /configuracoes/database
GET    /configuracoes/ia
GET    /configuracoes/ia/modelos
GET    /configuracoes/ia/ativa
POST   /configuracoes/ia
GET    /configuracoes/usuarios
POST   /configuracoes/usuarios
GET    /configuracoes/seguranca
POST   /configuracoes/seguranca
GET    /configuracoes/notificacoes
POST   /configuracoes/notificacoes
```

## CI/CD (Jenkins)

O `Jenkinsfile` executa:
1. Build paralelo de todas as imagens
2. Smoke test de importação
3. Push para registry (branch `main`)
4. Deploy via `docker compose` (branch `main`)

Configure as credentials no Jenkins:
- `kealex-secret-key` — Secret text com o valor de SECRET_KEY
- `registry-creds` — Username/Password do registry Docker

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
