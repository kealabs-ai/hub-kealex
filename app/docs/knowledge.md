# Base de conhecimento — app central Kealex

## Visão geral

`app/main.py` é a composição da API central FastAPI do hub Kealex. Os handlers estão em routers por domínio e o serviço compartilha o banco MySQL com os microserviços `svc-*`. Não confundir essa aplicação com um diretório `svc-app`: o código fica na pasta `app/` da raiz do repositório.

## Domínios e tabelas

O módulo declara modelos para tenants e usuários, clientes e processos, documentos e prazos, audiências e intimações, cobranças e histórico, atividades, configurações, agentes e políticas de IA, uso de tokens e chaves de API. Os nomes das tabelas são contratos compartilhados; não alterá-los sem migração e análise de compatibilidade.

## Autenticação e isolamento

- JWT assinado com HS256; segredo configurado por `KEALEX_JWT_SECRET` ou `KEALEX_SECRET_KEY`.
- A autenticação usa Bearer token.
- Rotas administrativas usam `_require_admin`.
- As operações devem aplicar o escopo do tenant derivado dos claims validados; não confiar em `tenant_id` fornecido no payload HTTP.
- Chaves pessoais de API são protegidas com Fernet e a configuração `KEALEX_API_KEYS_ENCRYPTION_KEY` ou derivação compatível do segredo JWT.

## Configuração

O banco aceita `KEALEX_DATABASE_URL` ou as variáveis `KEALEX_DB_HOST`, `KEALEX_DB_NAME`, `KEALEX_DB_USER`, `KEALEX_DB_PASSWORD` e `KEALEX_DB_PORT`. O token JWT expira conforme `KEALEX_JWT_EXPIRY_HOURS` (padrão atual: 8 horas). As integrações de IA usam variáveis `KEALEX_*_API_KEY`; cobrança usa credenciais Asaas configuradas no ambiente.

Nunca copiar valores reais de `.env` para documentação, testes ou logs. `create_all()` não migra tabelas existentes.

## Organização do código

- Composição FastAPI e CORS: `app/main.py`.
- Rotas agrupadas por domínio: `app/api/routes/`.
- Schemas: `app/api/schemas/schemas.py`.
- Casos de uso e presenters: `app/application/use_cases/`.
- Modelos SQLAlchemy: `app/infrastructure/database/models.py`.
- Sessões e startup do banco: `app/infrastructure/database/`.
- Configuração: `app/core/config.py`.
- JWT, hashing e dependências de autorização: `app/infrastructure/security/` e `app/api/dependencies.py`.
- `app/legacy_context.py` serve como ponte temporária para helpers compartilhados ainda não extraídos.

Ao continuar a extração, preserve os contratos existentes e atualize os testes correspondentes.

## Testes existentes

Os testes relevantes ficam na raiz do repositório: `test_processos.py`, `test_processos_fases.py`, `test_intimacoes.py` e `test_public_keys.py`. Consulte também os diretórios de testes dos microserviços; cada suíte deve ser executada no contexto do serviço que a mantém.

O Dockerfile da raiz carrega `app.main:app`; a execução local deve usar o mesmo import path e as dependências da raiz.
