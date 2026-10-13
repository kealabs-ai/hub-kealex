# Project Structure — hub-kealex

## Directory Layout

```
hub-kealex/
├── app/                        # Main unified FastAPI application
│   └── main.py                 # Single-file monolith (~2000+ lines)
├── svc-auth/                   # Auth microservice (standalone deployable)
│   ├── main.py
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── fix_hash.py
│   └── seed_users.py
├── svc-clientes/               # Clients microservice
├── svc-cobrancas/              # Billing/charges microservice
├── svc-configuracoes/          # Configuration microservice
├── svc-documentos/             # Documents microservice
├── svc-escritorios/            # Law offices microservice
├── svc-financeiro/             # Financial microservice
├── svc-prazos/                 # Deadlines microservice
├── svc-processos/              # Legal processes microservice
│   └── avancar_fase_model.py   # Phase advancement model
├── svc-repositorios/           # Document repository microservice
├── svc-usuarios/               # Users microservice
├── migrations/                 # SQL migration scripts
├── postman/                    # API test collections
├── knowledge/                  # Project documentation
├── .amazonq/rules/memory-bank/ # AI assistant memory bank
├── docker-compose.yml          # Main compose (production)
├── docker-compose.local.yml    # Local development compose
├── docker-compose.prod.yml     # Production variant
├── docker-compose.hostinger.yml
├── docker-compose.traefik.yml
├── docker-compose.nginx.yml
├── Dockerfile                  # Root app Dockerfile
├── Jenkinsfile                 # Main CI/CD pipeline
├── requirements.txt            # Root app dependencies
├── .env.example                # Environment template
├── trial_guard.py              # Trial enforcement utility
├── shared_modal.py             # Shared modal patterns
└── exemplo_servico_com_modal.py # Service template example
```

## Architectural Pattern: Dual-Mode Architecture

The project operates in two modes simultaneously:

### 1. Unified Monolith (`app/main.py`)
- Single FastAPI app consolidating all domain logic
- Routes prefixed `/k1/lex/` (legacy) and `/v1/lex/`
- All SQLAlchemy models defined inline
- Deployed as `hubkealex` container on port 8000

### 2. Microservices (`svc-*/`)
- Each `svc-*` directory is an independently deployable FastAPI service
- Each has its own `Dockerfile` and `requirements.txt`
- Routed via Traefik path-based routing (`/v1/lex/<service>`)
- Share the same MySQL database with tenant isolation
- Services: auth, usuarios, escritorios, clientes, cobrancas, configuracoes, documentos, financeiro, prazos, processos, repositorios

## Core Components

### Database Layer
- SQLAlchemy ORM with MySQL (PyMySQL driver)
- Connection via `KEALEX_DB_*` environment variables
- `SessionLocal` factory with `get_db()` dependency injection
- All models include: `tenant_id`, `created_at`, `updated_at`
- Audit fields: `user_id`, `escritorio_id` on domain tables

### Authentication Flow
- JWT tokens (python-jose) with HS256
- Token payload: `{ sub, tenant_id, role, exp }`
- `verify_token` dependency used across all protected endpoints
- Passwords hashed with bcrypt

### Multi-tenancy
- Every query filtered by `tenant_id` from JWT
- Tenant model tracks: plan, subscription status, trial dates, billing info
- `Tenant.ativo` flag gates user access

### Routing Convention
```
GET    /v1/lex/<resource>          # List all
POST   /v1/lex/<resource>          # Create
POST   /v1/lex/<resource>/get      # Get single (by id in body)
POST   /v1/lex/<resource>/update   # Update
POST   /v1/lex/<resource>/delete   # Delete
```

### Infrastructure
- Traefik: reverse proxy, TLS termination, CORS middleware, path stripping
- Networks: `easypanel` (external, Traefik), `kealex-internal` (bridge), `kealabs-net` (external)
- Health checks: Python urllib polling `/health` endpoint
- Jenkins pipeline: checkout → build → deploy → health check

## Key Relationships
```
Tenant (1) ──── (N) Usuario
Tenant (1) ──── (N) Processo
Tenant (1) ──── (N) Cliente
Tenant (1) ──── (N) Escritorio
Tenant (1) ──── (N) CfgIA (AI configurations)
Tenant (1) ──── (1) AsaasSubscription
Processo  (1) ──── (N) FaseProcesso
```
