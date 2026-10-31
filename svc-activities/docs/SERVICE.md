# svc-activities

## Responsabilidade

Gerenciar atividades e colunas de status por usuário e tenant, incluindo criação, consulta, atualização e exclusão.

## Camadas

- API: `app/api/routes/`, schemas HTTP em `app/api/schemas/` e dependências em `app/api/dependencies.py`.
- Casos de uso: `app/application/use_cases/`.
- Domínio: regras e conceitos do serviço; os modelos persistidos estão em `app/infrastructure/database/models/`.
- Persistência e segurança: `app/infrastructure/database/` e `app/infrastructure/security/`.
- Configuração e middleware: `app/core/`.

O `main.py` da raiz mantém compatibilidade com `uvicorn main:app` no Docker e importa `app.main`. Preserve os aliases de rota e os contratos JSON atuais.

## Funcionalidades

- Listar, criar, atualizar e excluir atividades.
- Listar, criar, atualizar e excluir colunas de atividade.
- Criar colunas padrão para um usuário/tenant sem colunas cadastradas.
- Validar JWT e filtrar operações pelo usuário e tenant do token.
- Disponibilizar health check em `/health`.

## Dependências

- MySQL via SQLAlchemy e PyMySQL.
- JWT HS256 via `python-jose`.
- FastAPI, Pydantic e Uvicorn.
- `python-dotenv` para carregar configuração local.

## Regras

- Toda consulta ou alteração de atividade e coluna deve restringir os registros pelo `user_id` e `tenant_id` autenticados.
- Senhas ou segredos não pertencem a este serviço; JWT é validado com `KEALEX_SECRET_KEY` ou `KEALEX_JWT_SECRET`.
- Datas podem chegar em `dueDate` ou `due_date`; status pode chegar em `status`, `columnId` ou `column_id`.
- Respostas mantêm os campos camelCase existentes, como `userId`, `dueDate`, `createdAt` e `updatedAt`.
- Atualizações devem ignorar campos ausentes, rejeitar valores nulos não permitidos e validar o status contra as colunas do usuário/tenant.
- Colunas padrão não podem ser removidas se forem a última coluna; uma coluna com atividades não pode ser removida antes de mover essas atividades.
- Não alterar schema sem migração versionada. `create_all()` apenas cria tabelas ausentes.

## Rotas e aliases

Cada operação de atividades tem aliases para compatibilidade:

- `/activities`
- `/api/activities`
- `/k1/lex/activities`
- `/v1/lex/activities`

As mesmas famílias de prefixo são usadas para `/columns`, `/columns/update`, `/columns/delete`, `/update` e `/delete`. Consulte `app/api/routes/activity_routes.py` para métodos e contratos precisos.

## Como alterar

- Rotas e HTTP: `app/api/routes/activity_routes.py`.
- Schemas e aliases de entrada: `app/api/schemas/activity_schema.py`.
- Regras de suporte e colunas padrão: `app/application/use_cases/activity_support.py`.
- Extração da identidade de usuário/tenant: `app/api/dependencies.py`.
- Tabelas: `app/infrastructure/database/models/activity_model.py`.
- Sessão e engine: `app/infrastructure/database/session.py`.
- JWT: `app/infrastructure/security/jwt_provider.py`.
- Configuração: `app/core/config.py`.
- Middleware de log: `app/core/middleware.py`.
- Ao alterar contratos, atualizar também `knowledge.md` e os consumidores pertinentes.

## Testes, ambiente e build

Os testes usam `unittest`. Use Python 3.12, alinhado ao `Dockerfile` e às versões fixadas em `requirements.txt`. No PowerShell, a partir da raiz de `svc-activities`:

```powershell
py -3.12 -m venv .venv312
.\.venv312\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m unittest discover -s tests/unit -v
python -m unittest discover -s tests/integration -v
docker build -t svc-activities:teste .
docker image ls svc-activities
```
