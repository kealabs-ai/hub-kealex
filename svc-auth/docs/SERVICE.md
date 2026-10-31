# svc-auth

## Responsabilidade

AutenticaÃ§Ã£o, emissÃ£o e validaÃ§Ã£o de tokens, identidade de usuÃ¡rios, isolamento por tenant e operaÃ§Ãµes relacionadas Ã  assinatura e cobranÃ§a da conta.

## Camadas

OrganizaÃ§Ã£o adotada para separar responsabilidades:

- API: `app/api/routes/`
- Casos de uso: `app/application/use_cases/`
- Entidades: `app/domain/entities/`
- PersistÃªncia e seguranÃ§a: `app/infrastructure/`
- ConfiguraÃ§Ã£o e utilitÃ¡rios comuns: `app/core/`

O `main.py` da raiz permanece como ponto de compatibilidade para o comando Docker atual e importa `app.main`. Novas mudanÃ§as devem preservar essa entrada e os contratos HTTP existentes.

## Funcionalidades

- Cadastro e login de usuÃ¡rio.
- ValidaÃ§Ã£o de credenciais e armazenamento de senhas com bcrypt.
- EmissÃ£o e validaÃ§Ã£o de JWT.
- Consulta da identidade autenticada.
- AssociaÃ§Ã£o de usuÃ¡rios a tenants e escritÃ³rios.
- Controle de acesso baseado no estado do trial e da assinatura.
- OperaÃ§Ãµes de assinatura e integraÃ§Ã£o de cobranÃ§a com o Asaas.
- RecepÃ§Ã£o e deduplicaÃ§Ã£o de webhooks do Asaas.

## DependÃªncias

- Banco de usuÃ¡rios e tenants via SQLAlchemy e MySQL/PyMySQL.
- Provedor JWT via `python-jose`.
- ServiÃ§o de hashing de senhas via `bcrypt`.
- API externa do Asaas via `httpx`, para operaÃ§Ãµes de cobranÃ§a.

## Regras

- Senhas nunca sÃ£o armazenadas em texto puro; usar bcrypt para criar e validar hashes.
- Tokens JWT usam HS256, tÃªm expiraÃ§Ã£o de 8 horas na implementaÃ§Ã£o atual e carregam identidade, papel e escopo do tenant.
- Erros de autenticaÃ§Ã£o nÃ£o devem revelar se o usuÃ¡rio existe; login retorna mensagem genÃ©rica para credenciais invÃ¡lidas.
- Rotas devem distinguir autenticaÃ§Ã£o de autorizaÃ§Ã£o: fluxos necessÃ¡rios para consultar ou regularizar cobranÃ§a podem aceitar uma conta sem acesso ativo; operaÃ§Ãµes da plataforma devem aplicar a regra de acesso do tenant.
- Consultas e alteraÃ§Ãµes de dados de usuÃ¡rios e escritÃ³rios devem respeitar o `tenant_id` obtido de contexto confiÃ¡vel.
- A autorizaÃ§Ã£o por escritÃ³rio deve ser validada pelo serviÃ§o responsÃ¡vel pelo recurso, sem confiar em identificadores fornecidos pelo cliente.
- Eventos de cobranÃ§a devem ser autenticados e processados de forma idempotente.
- Segredos e credenciais devem vir da configuraÃ§Ã£o do ambiente e nunca ser registrados em logs ou incluÃ­dos no repositÃ³rio.
- AlteraÃ§Ãµes de schema requerem migraÃ§Ã£o versionada; `create_all()` nÃ£o substitui migraÃ§Ãµes.
- Preservar caminhos, payloads e formatos de resposta atuais, incluindo campos camelCase consumidos por clientes existentes.

## Como alterar

- Endpoints de cadastro/login: `app/api/routes/auth_routes.py`.
- Consulta da identidade autenticada: `app/api/routes/user_routes.py`.
- Endpoints de cobranÃ§a: `app/api/routes/billing_routes.py`.
- Regra de acesso e concessÃ£o de perÃ­odo de assinatura: `app/application/use_cases/`.
- Erros de domÃ­nio: `app/domain/exceptions.py`.
- Schemas HTTP: `app/api/schemas/`.
- Modelos e sessÃµes de banco: `app/infrastructure/database/`.
- JWT e hashing: `app/infrastructure/security/`.
- ConfiguraÃ§Ã£o e normalizaÃ§Ã£o: `app/core/`.
- Ao alterar contratos ou regras, atualizar tambÃ©m `knowledge.md` e os clientes afetados.

## Testes

- UnitÃ¡rios: `tests/unit/`.
- IntegraÃ§Ã£o: `tests/integration/`.
- Os testes usam `unittest`; o cliente de integraÃ§Ã£o cobre health checks sem inicializar o banco. O ambiente local precisa instalar `requirements.txt` para executÃ¡-los.

