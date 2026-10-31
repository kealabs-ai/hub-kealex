# Base de conhecimento — `svc-usuarios`

## Visão geral

`svc-usuarios` é uma API FastAPI para gerenciamento de usuários e escritórios, papéis, modalidade, chaves públicas do DataJud e consultas processuais. A aplicação está em `app/`; o `main.py` na raiz importa `app.main` para compatibilidade com o comando atual do container.

## Estrutura

| Caminho | Responsabilidade |
|---|---|
| `app/main.py` | Criação da aplicação, CORS, routers, inicialização do schema e health check. |
| `app/api/routes/user_routes.py` | CRUD de usuários, modalidade e identidade atual. |
| `app/api/routes/public_key_routes.py` | Gestão das chaves públicas do usuário. |
| `app/api/routes/datajud_routes.py` | Consulta processual externa ao DataJud. |
| `app/api/schemas/user_schema.py` | Schemas de entrada e validação Pydantic. |
| `app/api/dependencies.py` | Guardas de administrador/equipe e integração opcional com `trial_guard`. |
| `app/application/use_cases/office_capacity.py` | Regra do limite de advogados por escritório. |
| `app/application/use_cases/user_presenter.py` | Serialização dos contratos de resposta. |
| `app/domain/entities/role.py` | Enum de papéis (`RoleEnum`). |
| `app/infrastructure/database/models/user_model.py` | Modelos `Usuario` e `UsuarioChavePublica`. |
| `app/infrastructure/database/session.py` | Engine, sessões e dependência `get_db`. |
| `app/infrastructure/security/` | Verificação JWT e hash bcrypt. |
| `app/core/config.py` | Banco, segredo JWT e configuração de ambiente. |
| `tests/` | Testes unitários e de integração com `unittest`. |

## Modelo e isolamento

- `Usuario` mapeia a tabela compartilhada `usuarios`; inclui tenant, escritório, código, OAB, papel e estado ativo.
- `UsuarioChavePublica` mapeia `usuarios_chaves_publicas`, com chave única por usuário e órgão e chave estrangeira para `usuarios.id`.
- Consultas de usuário devem filtrar `tenant_id`. A equipe de escritório também deve filtrar pelo escritório declarado no JWT.
- A capacidade é consultada em `escritorios.limite_advogados`; registros precisam pertencer ao tenant informado.
- `create_all()` roda no startup e cria tabelas ausentes. Alterações de tabelas existentes requerem migração versionada.

## Rotas e contratos

Prefixo principal: `/v1/lex/usuarios`. Inclui endpoints de listagem, cadastro, atualização, exclusão, modalidade, `/me` e consultas DataJud. Gestão de chaves públicas também mantém aliases `/chaves-publicas` e `/me/chaves-publicas`, com operações de listagem, criação, atualização e exclusão. O health check é `GET /health`.

As respostas expõem camelCase, por exemplo `tenantId`, `escritorioId`, `codigoEscritorio`, `createdAt`, `userId` e `chavePublica`. Preserve os formatos consumidos pelo frontend e por outros serviços.

## Autorização

- JWT Bearer é validado com HS256 e `KEALEX_SECRET_KEY` ou `KEALEX_JWT_SECRET`.
- Se `trial_guard.require_active_trial` estiver disponível, ele é usado como guarda comum; caso contrário, as rotas usam apenas a validação JWT.
- `admin_guard` limita exclusão a administradores.
- `team_guard` permite administradores e escritórios, restringindo escritório aos próprios advogados associados.
- Um advogado pode alterar sua própria modalidade, mas não a de outro usuário.

## DataJud

A consulta exige número CNJ com 20 dígitos, tribunal mapeado e chave pública cadastrada para o ramo da Justiça correspondente. O cliente HTTP usa `urllib` com timeout de 25 segundos. Erros do provedor são convertidos em status HTTP 502/503; não registre nem retorne a chave pública.

## Configuração e execução

O serviço carrega `.env` via `python-dotenv`.

| Variáveis | Uso |
|---|---|
| `KEALEX_DB_HOST`, `KEALEX_DB_NAME`, `KEALEX_DB_USER`, `KEALEX_DB_PASSWORD` | Configuração individual do MySQL, quando fornecidas em conjunto. |
| `KEALEX_DB_PORT` | Porta do MySQL; padrão `3306`. |
| `KEALEX_DATABASE_URL` | URL SQLAlchemy alternativa. |
| `KEALEX_SECRET_KEY` ou `KEALEX_JWT_SECRET` | Segredo obrigatório para validar JWT. |

O `Dockerfile` usa Python 3.12 slim, instala `requirements.txt` e inicia `uvicorn main:app --host 0.0.0.0 --port 8000`.

## Testes e build local

Use Python 3.12 para alinhar ao container e às dependências fixadas. No PowerShell, a partir da raiz do serviço:

```powershell
py -3.12 -m venv .venv312
.\.venv312\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m unittest discover -s tests/unit -v
python -m unittest discover -s tests/integration -v
docker build -t svc-usuarios:teste .
docker image ls svc-usuarios
```
