# Base de conhecimento — svc-prazos

## Visão geral

API FastAPI para cadastro, consulta e acompanhamento de prazos jurídicos. `main.py` na raiz preserva o comando `uvicorn main:app` do container.

## Modelo e dados

A tabela `prazos` guarda tenant, usuário, escritório, processo, advogado, título, descrição, vencimento, status e timestamps. `processo_id` se liga logicamente à tabela compartilhada `processos`; a criação consulta `advogado_id` e `escritorio_id` nesse processo. Não altere esses nomes sem migração coordenada.

## Contratos existentes

- `GET /v1/lex/prazos`: lista os prazos do tenant.
- `POST /v1/lex/prazos/get`: consulta por ID.
- `POST /v1/lex/prazos/vencendo`: lista prazos pendentes até `dias` (padrão 7).
- `POST /v1/lex/prazos/by-processo`: consulta prazos de um processo.
- `POST /v1/lex/prazos`: cria prazo a partir de processo existente.
- `POST /v1/lex/prazos/update` e `/delete`: alteram ou removem prazo.
- `GET /health`: `{"status":"ok","service":"svc-prazos"}`.

Os requests e respostas usam campos camelCase; os valores de data são strings `YYYY-MM-DD`. Preserve os contratos e status HTTP atuais.

## Autorização e configuração

As rotas usam JWT e o guard `trial_guard` quando disponível. O tenant é obtido de `tenant_id` ou do claim legado `sub`.

Configure o banco via `KEALEX_DATABASE_URL` ou `KEALEX_DB_HOST`, `KEALEX_DB_NAME`, `KEALEX_DB_USER`, `KEALEX_DB_PASSWORD` e `KEALEX_DB_PORT` opcional. Configure `KEALEX_SECRET_KEY` ou `KEALEX_JWT_SECRET` para validar JWT.

Use Python 3.12 conforme o Dockerfile. Instale `requirements.txt`; execute `python -m unittest discover -s tests -v` e construa com `docker build -t svc-prazos:teste .` dentro do diretório do serviço.
