# Base de conhecimento — svc-integracoes

## Visão geral

Microserviço FastAPI para integrações externas. Atualmente encapsula as consultas fiscais do fornecedor FiscalAPI que eram servidas pelo backend central.

## Contratos

- `POST /api/v1/certidoes/consulta-ie`
- `POST /api/v1/certidoes/enriquecimento`
- `POST /api/v1/certidoes/cnd-estadual`
- `POST /api/v1/certidoes/federais`
- `POST /api/v1/certidoes/sigef`
- `GET /api/v1/certidoes/consultas/{id}` e `/documento`
- `GET /health` retorna `{"status":"ok","service":"svc-integracoes"}`.

Cada POST exige `Idempotency-Key`. O JWT precisa conter usuário e tenant e a role autorizada. A consulta e o documento pertencem exclusivamente ao usuário e tenant autenticados. A chave do fornecedor só existe no servidor.

## Persistência e segredos

O histórico usa as tabelas legadas `consultas_fiscalapi` e `documentos_fiscalapi`, compartilhadas com o backend. Aplique `migrations/create_fiscalapi_consultas.sql` uma vez nos bancos existentes antes de publicar o serviço. Resultados e PDFs são cifrados com uma chave derivada estável de `KEALEX_SECRET_KEY` (ou `CERTIFICATES_STORAGE_KEY`). Não altere a derivação sem plano de migração dos dados.

Configure `FISCALAPI_ENABLED`, `FISCALAPI_BASE_URL`, `FISCALAPI_API_KEY`, `FISCALAPI_TIMEOUT` e `FISCALAPI_RATE_LIMIT_PER_MINUTE` no ambiente do serviço. A base é fixada ao host HTTPS oficial `api.fiscalapi.com.br`; não registre API keys, CPF/CNPJ, conteúdo de consultas ou PDFs.

O banco é compartilhado via `KEALEX_DATABASE_URL` ou `KEALEX_DB_*`; JWT HS256 usa `KEALEX_SECRET_KEY` ou `KEALEX_JWT_SECRET`. O Dockerfile usa Python 3.12 e a entrada compatível é `uvicorn main:app`.
