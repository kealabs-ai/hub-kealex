# svc-cobrancas

## Responsabilidade

Gerenciar cobranças, suas fases e histórico, iniciar pagamentos pelo Asaas e processar notificações de pagamento.

## Camadas

- API: `app/api/routes/`, `app/api/schemas/` e `app/api/dependencies.py`
- Casos de uso e transformações da aplicação: `app/application/use_cases/`
- Endpoints e adaptação HTTP: `app/api/routes/cobrancas_routes.py`
- Entidades e modelos persistidos: `app/infrastructure/database/models/`
- Persistência: `app/infrastructure/database/session.py`
- Configuração: `app/core/config.py`

## Componentes

- `Cobranca`: dados, status e fase da cobrança.
- `HistoricoCobranca`: transições e ações efetuadas.
- `AsaasWebhookEvent`: controle de idempotência dos eventos do Asaas.
- `cobrancas_routes`: criação, consulta, pagamento, atualização de fase, cancelamento, timeline e webhook.
- `cobranca_support`: serialização, montagem de payload para o Asaas e ações disponíveis para a cobrança.
- `verify_token` e `auth_guard`: validação JWT e integração opcional com `trial_guard`.

## Dependências

- Banco configurado por `KEALEX_DATABASE_URL` ou pelas variáveis `KEALEX_DB_*`.
- Asaas para iniciar pagamentos, configurado por `KEALEX_ASAAS_API_KEY` e opcionalmente `KEALEX_ASAAS_BASE_URL`.
- `KEALEX_SECRET_KEY` ou `KEALEX_JWT_SECRET` para validação JWT.
- `KEALEX_ASAAS_WEBHOOK_TOKEN` para autenticar webhooks.

## Regras

- Valores monetários internos são armazenados em centavos.
- Cobranças e eventos mantêm os nomes de tabela existentes; alterações de schema exigem migração versionada.
- Webhooks validados são registrados para evitar processamento duplicado.
- Rotas legadas `/k1/lex/cobrancas`, `/v1/lex/cobrancas` e o alias `/cobrancas` devem permanecer compatíveis.
- O token do Asaas não deve ser exposto em respostas ou logs.

## Como alterar

- Rotas e regras do fluxo: `app/api/routes/cobrancas_routes.py`.
- Contratos HTTP: `app/api/schemas/cobranca_schema.py`.
- Autenticação: `app/api/dependencies.py`.
- Modelos do banco: `app/infrastructure/database/models/cobranca_model.py`.
- Sessões e conexão: `app/infrastructure/database/session.py`.
- Configuração e variáveis de ambiente: `app/core/config.py`.

## Testes

- Unitários: `tests/unit/`.
- Integração da API: `tests/integration/`.
- Execute no diretório do serviço: `python -m unittest discover -s tests -v`.

## Build

O Dockerfile usa Python 3.11 e instala as dependências de `requirements.txt`.

```powershell
docker build -t svc-cobrancas .
docker run --rm -p 8000:8000 --env-file .env svc-cobrancas
```
