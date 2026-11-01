# svc-processos

## Responsabilidade

Gerenciar processos jurídicos por tenant, incluindo vínculo com cliente/advogado, status e fases do fluxo processual.

## Camadas

- API: `app/api/routes/`, `app/api/schemas/` e `app/api/dependencies.py`
- Casos de uso: `app/application/use_cases/`
- Domínio: `app/domain/entities/`
- Persistência: `app/infrastructure/database/`
- Configuração: `app/core/config.py`

## Componentes

- `process_routes.py`: listagem e CRUD de processos.
- `phase_routes.py`: avanço e consulta das próximas fases.
- `debug_routes.py`: endpoints de diagnóstico já existentes.
- `process_schema.py`: contratos Pydantic.
- `process_model.py`: modelos SQLAlchemy de processos, fases e cliente usados pelo serviço.
- `process_access.py`: consulta de processo no escopo de usuário/papel/tenant.
- `process_presenter.py`: enriquecimento com dados do cliente e serialização.
- `phase_queries.py`: composição determinística da resposta de próximas fases.

## Dependências

- MySQL/PyMySQL via `KEALEX_DATABASE_URL` ou `KEALEX_DB_*`.
- JWT HS256 via `KEALEX_SECRET_KEY` ou `KEALEX_JWT_SECRET`.
- `trial_guard` opcional para validação do estado de acesso do tenant.
- Tabelas compartilhadas `clientes` e demais serviços consumidores de `processos`.

## Regras

- Operações de processo devem respeitar o tenant e as restrições por papel (`admin`, `advogado`, `cliente`).
- Advogados acessam processos vinculados à própria identidade; clientes acessam seus próprios processos.
- A criação exige cliente do tenant e gera as fases padrão existentes.
- O avanço atualiza status de fases e `fase_atual` do processo.
- Preserve tabelas, relacionamentos, status, caminhos `/k1/lex/processos` e respostas atuais.
- Mudanças de schema compartilhado exigem migração versionada.

## Como alterar

- CRUD: `app/api/routes/process_routes.py`.
- Fases: `app/api/routes/phase_routes.py` e `app/application/use_cases/phase_queries.py`.
- Diagnóstico: `app/api/routes/debug_routes.py`.
- Contratos: `app/api/schemas/process_schema.py`.
- Acesso e apresentação: `app/application/use_cases/`.
- Modelos e sessão: `app/infrastructure/database/`.

## Testes e build

Use Python 3.12, conforme o Dockerfile. Após instalar `requirements.txt`, execute a partir da raiz do serviço:

```powershell
python -m unittest discover -s tests -v
docker build -t svc-processos:teste .
```
