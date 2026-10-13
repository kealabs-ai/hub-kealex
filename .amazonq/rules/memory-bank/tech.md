# Technology Stack — hub-kealex

## Language & Runtime
- **Python 3.11** (specified in `FROM python:3.11-slim` Dockerfile)
- All services use Python exclusively

## Core Framework
- **FastAPI 0.111.0** — async web framework, OpenAPI auto-docs
- **Uvicorn 0.29.0** — ASGI server, runs on `0.0.0.0:8000`
- **Pydantic v2 (2.7.1)** — request/response validation and serialization

## Database
- **MySQL** — primary database (hosted on Hostinger)
- **SQLAlchemy 2.0.30** — ORM (uses 2.x style with `Session`)
- **PyMySQL 1.1.1** — MySQL driver
- Connection string: `mysql+pymysql://{user}:{pass}@{host}:{port}/{db}`
- Environment variables: `KEALEX_DB_HOST`, `KEALEX_DB_PORT`, `KEALEX_DB_NAME`, `KEALEX_DB_USER`, `KEALEX_DB_PASSWORD`

## Authentication & Security
- **python-jose[cryptography] 3.3.0** — JWT creation and verification (HS256)
- **bcrypt 4.2.1** — password hashing
- **cryptography 42.0.8** — cryptographic primitives

## HTTP Client
- **httpx 0.27.0** — async HTTP client (used for Asaas API calls and inter-service communication)

## External Integrations
- **Asaas** — Brazilian payment gateway (subscriptions, webhooks)
  - `KEALEX_ASAAS_API_KEY`, `KEALEX_ASAAS_BASE_URL`, `KEALEX_ASAAS_WEBHOOK_TOKEN`
- **Google APIs** — Drive integration for documents
  - `google-auth 2.31.0`, `google-auth-oauthlib`, `google-auth-httplib2`, `google-api-python-client 2.121.0`
- **AI Providers** (keys via env):
  - `KEALEX_GEMINI_API_KEY` — Google Gemini
  - `KEALEX_OPENAI_API_KEY` — OpenAI
  - `KEALEX_GROQ_API_KEY` — Groq
  - `KEALEX_ANTHROPIC_API_KEY` — Anthropic
  - `KEALEX_CEREBRAS_API_KEY` — Cerebras

## Infrastructure & DevOps
- **Docker** — containerization (`python:3.11-slim` base image)
- **Docker Compose** — multi-service orchestration (multiple compose files for different environments)
- **Traefik** — reverse proxy, TLS termination, CORS, path-based routing, path stripping
- **Jenkins** — CI/CD pipeline (Jenkinsfile in repo root)
- **Hostinger VPS** — production hosting

## Environment Configuration
- **python-dotenv 1.0.1** — `.env` file loading
- All env vars prefixed with `KEALEX_`
- `.env.example` provided as template

## Development Commands

```bash
# Local development
cp .env.example .env
# Edit .env with your DB credentials
docker compose -f docker-compose.local.yml up --build

# Production deploy
docker compose -f docker-compose.yml up -d --build

# Run specific service
docker compose up --build hubkealex

# View logs
docker compose logs -f hubkealex

# Health check
curl http://localhost:8000/health
curl http://localhost:8000/k1/lex/health

# Database debug
curl http://localhost:8000/debug/db-status

# Run SQL migrations
python run_sql_file.py <migration_file.sql>
```

## CI/CD Pipeline (Jenkins)
Stages: `Prepare` → `Ensure Buildx` → `Deploy` → `Health Check`
- Git pull from `master` branch (preserves `.env` on server)
- Docker Buildx installation if missing
- `docker compose down` → `docker compose up -d --build`
- Health check polls container status 10x with 3s intervals

## Compose File Variants
| File | Purpose |
|------|---------|
| `docker-compose.yml` | Main production (Traefik + easypanel) |
| `docker-compose.local.yml` | Local development |
| `docker-compose.prod.yml` | Production variant |
| `docker-compose.hostinger.yml` | Hostinger-specific |
| `docker-compose.traefik.yml` | Traefik-focused |
| `docker-compose.nginx.yml` | Nginx reverse proxy variant |

## API Documentation
- Auto-generated Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Postman collections in `/postman/` directory
