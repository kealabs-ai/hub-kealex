# svc-clientes

## Responsabilidade

Gerenciar clientes associados a um tenant e ao advogado responsável, incluindo cadastro, consulta, atualização, listagem e exclusão.

## Camadas

- API: `app/api/routes/`, schemas em `app/api/schemas/` e dependências em `app/api/dependencies.py`.
- Casos de uso: `app/application/use_cases/`.
- Domínio: conceitos e regras do serviço; modelos persistidos em `app/infrastructure/database/models/`.
- Persistência e segurança: `app/infrastructure/database/` e `app/infrastructure/security/`.
- Configuração: `app/core/`.

O `main.py` da raiz mantém compatibilidade com `uvicorn main:app` no Docker e importa `app.main`. Preserve essa entrada e os contratos HTTP existentes.

## Funcionalidades

- Listar clientes do tenant autenticado.
- Advogados veem e alteram apenas seus próprios clientes; administradores podem gerenciar os clientes do tenant.
- Criar cliente com validação de e-mail e campos opcionais de contato.
- Consultar, atualizar e excluir cliente por identificador.
- Health check em `/health`.

## Dependências

- MySQL compartilhado via SQLAlchemy e PyMySQL.
- JWT HS256 via `python-jose`.
- FastAPI, Pydantic e Uvicorn.
- `python-dotenv` para configuração local.

## Regras

- Todas as consultas e alterações filtram por `tenant_id`; para advogado, também por `advogado_id` derivado do token.
- Apenas papéis `admin` e `advogado` podem acessar as rotas protegidas.
- A criação não permite duplicar e-mail dentro do mesmo tenant.
- Respostas mantêm campos camelCase, como `tenantId`, `advogadoId`, `cpfCnpj`, `createdAt` e `updatedAt`.
- Não altere schema sem migração versionada. `Base.metadata.create_all()` cria tabelas ausentes, mas não migra tabelas existentes.

## Como alterar

- Endpoints: `app/api/routes/clientes_routes.py`.
- Schemas: `app/api/schemas/client_schema.py`.
- Formato de resposta: `app/application/use_cases/client_presenter.py`.
- Dependência de autorização: `app/api/dependencies.py`.
- Modelo: `app/infrastructure/database/models/client_model.py`.
- Banco e sessões: `app/infrastructure/database/session.py`.
- JWT: `app/infrastructure/security/jwt_provider.py`.
- Configuração: `app/core/config.py`.
- Atualize `knowledge.md` e os clientes pertinentes junto com mudanças nos contratos.

## Testes, ambiente e build

Os testes usam `unittest`. Use Python 3.12, alinhado ao `Dockerfile` e às versões fixadas no `requirements.txt`. No PowerShell, a partir da raiz de `svc-clientes`:

```powershell
py -3.12 -m venv .venv312
.\.venv312\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m unittest discover -s tests/unit -v
python -m unittest discover -s tests/integration -v
docker build -t svc-clientes:teste .
docker image ls svc-clientes
```
