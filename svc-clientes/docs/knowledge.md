# Base de conhecimento — `svc-clientes`

## Visão geral

`svc-clientes` é uma API FastAPI para gerenciar clientes de um tenant e advogado. A aplicação está em `app/`; o `main.py` na raiz importa `app.main` para manter o comando Docker `uvicorn main:app`.

## Estrutura

| Caminho | Responsabilidade |
|---|---|
| `app/main.py` | Aplicação FastAPI, CORS, router, startup do banco e health check. |
| `app/api/routes/clientes_routes.py` | Endpoints de listagem, cadastro, consulta, atualização e exclusão. |
| `app/api/schemas/client_schema.py` | Schemas Pydantic de entrada. |
| `app/api/dependencies.py` | Validação JWT, integração opcional com `trial_guard` e autorização por papel. |
| `app/application/use_cases/client_presenter.py` | Conversão de modelo para resposta camelCase. |
| `app/infrastructure/database/models/client_model.py` | Modelo SQLAlchemy `Cliente`. |
| `app/infrastructure/database/session.py` | Engine, sessões e dependência `get_db`. |
| `app/infrastructure/security/jwt_provider.py` | Validação de token Bearer HS256. |
| `app/core/config.py` | Configuração de conexão MySQL e segredo JWT. |
| `tests/unit/`, `tests/integration/` | Testes com `unittest`. |
| `Dockerfile`, `requirements.txt` | Build do container e dependências fixadas. |

## Modelo e isolamento

A tabela `clientes` contém `tenant_id`, `advogado_id`, nome, e-mail e campos de contato. `tenant_id` e `advogado_id` são vínculos lógicos ao restante do banco compartilhado.

Todas as consultas restringem por tenant. Quando o token pertence a um advogado, as consultas e alterações também filtram por `advogado_id` do token. Não confie em identificadores de escopo enviados pelo cliente.

## API

Prefixo: `/v1/lex/clientes`.

| Método | Rota | Ação |
|---|---|---|
| GET | `/v1/lex/clientes` | Lista clientes do escopo autorizado. |
| POST | `/v1/lex/clientes` | Cria cliente; responde HTTP 201. |
| POST | `/v1/lex/clientes/get` | Consulta cliente por `id`. |
| POST | `/v1/lex/clientes/update` | Atualiza campos fornecidos. |
| POST | `/v1/lex/clientes/delete` | Exclui cliente por `id`. |
| GET | `/health` | Retorna status do serviço. |

O cadastro impede e-mail duplicado dentro do tenant. Respostas mantêm nomes camelCase (`tenantId`, `advogadoId`, `cpfCnpj`, `createdAt`, `updatedAt`).

## Autorização

- JWT Bearer é validado com HS256 e `KEALEX_SECRET_KEY` ou `KEALEX_JWT_SECRET`.
- Se `trial_guard.require_active_trial` estiver disponível, ele é aplicado antes da autorização por papel; caso contrário, usa-se validação JWT.
- Papéis aceitos: `admin` e `advogado`.
- `admin` pode acessar clientes do tenant. `advogado` pode acessar apenas os clientes cujo `advogado_id` corresponde a `sub`.

## Configuração e inicialização

O serviço carrega `.env` por `python-dotenv`.

| Variável | Uso |
|---|---|
| `KEALEX_DB_HOST`, `KEALEX_DB_NAME`, `KEALEX_DB_USER`, `KEALEX_DB_PASSWORD` | Configuração do MySQL quando fornecidas em conjunto. |
| `KEALEX_DB_PORT` | Porta MySQL; padrão `3306`. |
| `KEALEX_DATABASE_URL` | URL SQLAlchemy alternativa. |
| `KEALEX_SECRET_KEY` ou `KEALEX_JWT_SECRET` | Segredo obrigatório para validar JWT. |

No startup, `Base.metadata.create_all(engine)` cria tabelas ausentes. Mudanças em tabelas existentes precisam de migração versionada. O `Dockerfile` usa Python 3.12 slim e inicia Uvicorn na porta 8000.

## Testes e build local

Use Python 3.12, alinhado ao container e às dependências fixadas. No PowerShell, a partir da raiz de `svc-clientes`:

```powershell
py -3.12 -m venv .venv312
.\.venv312\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m unittest discover -s tests/unit -v
python -m unittest discover -s tests/integration -v
docker build -t svc-clientes:teste .
docker image ls svc-clientes
```
