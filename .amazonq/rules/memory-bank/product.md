# Product Overview — hub-kealex

## Purpose
hub-kealex is the unified backend for the **Kealex** platform — a SaaS system designed for Brazilian law firms (escritórios de advocacia). It consolidates multiple microservices into a single FastAPI application with a microservices-ready architecture, providing authentication, billing, case management, client management, document handling, and AI agent capabilities.

## Value Proposition
- Single deployable backend replacing fragmented microservices
- Multi-tenant SaaS with per-tenant data isolation
- Integrated billing via Asaas (Brazilian payment gateway) with subscription lifecycle management
- AI agent support (Gemini, OpenAI, Groq, Anthropic, Cerebras)
- Trial → paid plan conversion flow built-in

## Key Features

### Authentication & Multi-tenancy
- JWT-based authentication with tenant_id embedded in tokens
- Tenant registration with automatic trial period (configurable days)
- Role-based access (admin, user roles per tenant)
- Slug-based tenant identification

### Billing & Subscriptions (Asaas Integration)
- Subscription creation and management via Asaas API
- Webhook processing with idempotency (duplicate event detection)
- Subscription lifecycle: trial → active → past_due → canceled → inactive
- Billing profile management (CPF/CNPJ, address, contact)
- Plans: trial, starter, professional, enterprise

### Core Domain Services
- **Processos** — Legal case/process management with phases (fases)
- **Clientes** — Client management per tenant
- **Documentos** — Document management (Google Drive integration)
- **Financeiro** — Financial records
- **Prazos** — Deadline tracking
- **Usuários** — User management within tenants
- **Escritórios** — Law office management
- **Configurações** — Tenant-level configuration including AI settings
- **Repositórios** — Document repository with Google Drive sync
- **Cobranças** — Billing/charge management

### AI Agents
- Multi-provider AI configuration per tenant (Gemini, OpenAI, Groq, Anthropic, Cerebras)
- Configurable AI agents with custom prompts and models
- Per-tenant AI key management

## Target Users
- Brazilian law firms (escritórios de advocacia)
- Legal professionals managing cases, clients, deadlines, and documents
- SaaS administrators managing tenant subscriptions

## Deployment
- Docker + Docker Compose containerized
- Traefik reverse proxy with automatic HTTPS
- Jenkins CI/CD pipeline
- Hosted on Hostinger VPS
- MySQL database (shared across services via tenant isolation)
- API versioning: `/v1/lex/` (current) and `/k1/lex/` (legacy compatibility)
