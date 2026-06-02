# hubKealex — Backend Unificado

Backend do sistema Kealex em arquitetura unificada com FastAPI (Monolítico melhorado).

## Visão Geral

Aplicação FastAPI única que consolida todos os serviços anteriores (auth, processos, documentos, financeiro, prazos, usuários, configurações, escritórios, clientes) em uma única aplicação escalável.

## Subir localmente

```bash
# Copiar arquivo de ambiente
cp .env.example .env

# Configurar SECRET_KEY no .env (opcional, possui padrão de desenvolvimento)
# SECRET_KEY=sua_chave_segura_aqui

# Build e iniciar containers
docker compose up --build
```

A aplicação estará disponível em `http://localhost:8000`.

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

## Endpoints Disponíveis

### Autenticação
```
POST   /v1/lex/auth/login
GET    /v1/lex/auth/me
GET    /health
```

### Processos
```
GET    /v1/lex/processos
POST   /v1/lex/processos
POST   /v1/lex/processos/get
POST   /v1/lex/processos/update
POST   /v1/lex/processos/delete
```

### Clientes
```
GET    /v1/lex/clientes
POST   /v1/lex/clientes
POST   /v1/lex/clientes/get
POST   /v1/lex/clientes/update
POST   /v1/lex/clientes/delete
```

### Documentos (Em desenvolvimento)
```
GET    /v1/lex/documentos
POST   /v1/lex/documentos
POST   /v1/lex/documentos/get
POST   /v1/lex/documentos/update
POST   /v1/lex/documentos/delete
```

### Financeiro (Em desenvolvimento)
```
GET    /v1/lex/financeiro
POST   /v1/lex/financeiro
POST   /v1/lex/financeiro/get
POST   /v1/lex/financeiro/update
POST   /v1/lex/financeiro/delete
```

### Prazos (Em desenvolvimento)
```
GET    /v1/lex/prazos
POST   /v1/lex/prazos
POST   /v1/lex/prazos/get
POST   /v1/lex/prazos/update
POST   /v1/lex/prazos/delete
```

### Usuários (Em desenvolvimento)
```
GET    /v1/lex/usuarios
POST   /v1/lex/usuarios
POST   /v1/lex/usuarios/get
POST   /v1/lex/usuarios/update
POST   /v1/lex/usuarios/delete
```

### Escritórios (Em desenvolvimento)
```
GET    /v1/lex/escritorios
POST   /v1/lex/escritorios
POST   /v1/lex/escritorios/get
POST   /v1/lex/escritorios/update
POST   /v1/lex/escritorios/delete
```

### Configurações (Em desenvolvimento)
```
GET    /v1/lex/configuracoes/geral
POST   /v1/lex/configuracoes/geral
```

## CI/CD (Jenkins)

O `Jenkinsfile` executa:
1. Checkout automático pelo Jenkins (Git Public)
2. Garantir Docker Buildx instalado
3. Build da imagem Docker
4. Criar rede Traefik (easypanel)
5. Deploy via `docker compose`
6. Health checks locais e via Traefik
7. Relatório de status final

Configure as credentials no Jenkins:
- `SECRET_KEY` — Secret text com o valor da chave secreta

**Fluxo:**
```
Checkout SCM → Prepare → Ensure Buildx → Deploy → Health Check
```

## Testes API (Postman)

Coleções disponíveis em `/postman`:

```bash
# Importar no Postman:
# - Kealex-Processos-API.postman_collection.json
# - Kealex-Environment.postman_environment.json

# Ou executar via Newman (CLI):
npm install -g newman
cd postman
./run-tests.bat  # Windows
```

## Estrutura do Projeto

```
hubKealex/
├── app/
│   └── main.py              # Aplicação FastAPI unificada
├── migrations/              # Scripts SQL de migração
├── postman/                 # Coleções de testes da API
├── .env.example             # Template de variáveis de ambiente
├── .dockerignore            # Arquivos ignorados no build Docker
├── docker-compose.yml       # Configuração Docker Compose
├── Dockerfile               # Build da aplicação
├── Jenkinsfile              # Pipeline CI/CD
├── requirements.txt         # Dependências Python
└── README.md                # Este arquivo
```

## Variáveis de Ambiente

```bash
SECRET_KEY=sua_chave_segura
DATABASE_URL=mysql+pymysql://usuario:senha@host:3306/banco
MYSQL_HOST=srv1078.hstgr.io
MYSQL_PORT=3306
MYSQL_DATABASE=u549746795_kealex
MYSQL_USER=u549746795_kealex
MYSQL_PASSWORD=senha_aqui
```

## Deploy em Produção

A aplicação está configurada com Traefik para:
- Routing via `srv1023256.hstgr.cloud/v1/lex`
- HTTPS automático
- CORS configurado
- Health checks automáticos

## Stack Tecnológico

- **Python 3.11**
- **FastAPI** - Framework web assíncrono
- **SQLAlchemy** - ORM para banco de dados
- **PyMySQL** - Driver MySQL
- **Pydantic** - Validação de dados
- **python-jose** - JWT handling
- **bcrypt** - Hash de senhas
- **Docker & Docker Compose** - Containerização
- **Traefik** - Reverse proxy
- **Jenkins** - CI/CD

## Troubleshooting

### Erro de conexão com MySQL
```bash
# Verificar variáveis de ambiente
docker compose exec hubkealex env | grep MYSQL

# Testar conectividade
docker compose exec hubkealex python -c "import pymysql; pymysql.connect(...)"
```

### Container não inicia
```bash
# Ver logs da aplicação
docker compose logs -f hubkealex

# Verificar health check
docker compose exec hubkealex curl http://localhost:8000/health
```

### Problema no Jenkins
```bash
# Verificar workspace do Jenkins
ls -la /var/jenkins_home/workspace/hub_kealex

# Forçar rebuild
# (Delete o workspace e retrigger a pipeline)
```

## Próximos Passos

- Implementar endpoints de Documentos, Financeiro, Prazos
- Adicionar testes unitários e de integração
- Implementar cache (Redis)
- Adicionar monitoramento (Prometheus/Grafana)
- Otimizar queries do banco de dados