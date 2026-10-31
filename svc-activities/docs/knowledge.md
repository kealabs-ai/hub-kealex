# Base de conhecimento — `svc-activities`

## Visão geral

`svc-activities` é uma API FastAPI para gerenciar atividades e suas colunas de status, com escopo por usuário e tenant. A implementação está em `app/`; o `main.py` da raiz importa `app.main` para manter compatibilidade com `uvicorn main:app` usado pelo Docker.

## Estrutura

| Caminho | Responsabilidade |
|---|---|
| `app/main.py` | Configuração da aplicação, CORS, router, middleware, inicialização do banco e health check. |
| `app/api/routes/activity_routes.py` | Endpoints de atividades e colunas, incluindo aliases de compatibilidade. |
| `app/api/schemas/activity_schema.py` | Schemas de entrada e aliases de campos Pydantic. |
| `app/api/dependencies.py` | Validação das claims de usuário e tenant presentes no token. |
| `app/application/use_cases/activity_support.py` | Colunas padrão e conversão de entidades em respostas da API. |
| `app/infrastructure/database/models/activity_model.py` | Modelos SQLAlchemy `Activity` e `ActivityColumn`. |
| `app/infrastructure/database/session.py` | Engine, fábrica de sessões e dependência `get_db`. |
| `app/infrastructure/security/jwt_provider.py` | Validação de JWT Bearer com HS256. |
| `app/core/config.py` | Configuração de banco, segredo JWT e origens CORS. |
| `app/core/middleware.py` | Middleware de log das requisições/respostas de atividades. |
| `tests/unit/` e `tests/integration/` | Testes de schemas/serialização e contratos HTTP. |
| `Dockerfile` e `requirements.txt` | Build do container e dependências fixadas. |

## Dados e isolamento

- Tabela `activities`: atividade associada a `user_id` e `tenant_id`, com título, descrição, status, prioridade e data opcional.
- Tabela `activity_columns`: colunas do quadro vinculadas a `user_id` e `tenant_id`, com título, cor e posição.
- JWT validado fornece `sub` e `tenant_id`; todas as consultas/alterações de atividades e colunas devem filtrar ambos.
- Ao consultar colunas sem registros, o serviço cria as colunas padrão `todo`, `in_progress` e `done` para aquele usuário e tenant.
- Não há chaves estrangeiras declaradas nesses modelos. `user_id` e `tenant_id` são vínculos lógicos.

## Contrato HTTP

Prefixos preservados:

- `/activities` e `/activities/columns`.
- `/api/activities` e `/api/activities/columns`.
- `/k1/lex/activities` e `/k1/lex/activities/columns`.
- `/v1/lex/activities` e `/v1/lex/activities/columns`.

Operações disponíveis em cada família: GET e POST na coleção, POST em `/update` e `/delete`; para colunas, GET/POST em `/columns` e POST em `/columns/update` e `/columns/delete`. O health check é `GET /health`.

Campos legados aceitos incluem `status`, `columnId` e `column_id`, assim como `dueDate` e `due_date`. Respostas usam camelCase (`userId`, `dueDate`, `createdAt`, `updatedAt`). Não altere esses formatos sem atualizar os consumidores.

## Configuração

O módulo carrega `.env` via `python-dotenv`.

| Variável | Uso |
|---|---|
| `KEALEX_DB_HOST`, `KEALEX_DB_NAME`, `KEALEX_DB_USER`, `KEALEX_DB_PASSWORD` | Configuração individual do MySQL; usadas em conjunto. |
| `KEALEX_DB_PORT` | Porta do MySQL; padrão `3306`. |
| `KEALEX_DATABASE_URL` | URL SQLAlchemy alternativa, usada se o conjunto de variáveis MySQL não estiver completo. |
| `KEALEX_SECRET_KEY` ou `KEALEX_JWT_SECRET` | Segredo obrigatório para validar JWT. |
| `KEALEX_CORS_ALLOWED_ORIGINS` | Origens permitidas, separadas por vírgula; vazio significa nenhuma origem explicitamente permitida por CORS. |

## Inicialização e operação

No startup, `Base.metadata.create_all(engine)` cria tabelas ausentes; falhas são registradas no log e não interrompem o startup, conforme o comportamento atual. `create_all()` não substitui migrações para alterações em tabelas existentes.

O middleware `ActivityConsoleLogMiddleware` registra no stdout os corpos JSON de requisição e resposta para os prefixos de atividades. Esses corpos podem conter dados do usuário; leve esse comportamento em conta ao acessar logs e não amplie seu escopo sem necessidade.

O `Dockerfile` usa Python 3.12 slim, instala `requirements.txt`, copia o serviço para `/app` e inicia `uvicorn main:app --host 0.0.0.0 --port 8000`.

## Testes e build local

Use Python 3.12, alinhado ao container e às dependências fixadas. A partir da raiz de `svc-activities`, no PowerShell:

```powershell
py -3.12 -m venv .venv312
.\.venv312\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m unittest discover -s tests/unit -v
python -m unittest discover -s tests/integration -v
docker build -t svc-activities:teste .
docker image ls svc-activities
```
