# svc-auth

## Responsabilidade

Autenticação, emissão e validação de tokens, identidade de usuários, isolamento por tenant e operações relacionadas à assinatura e cobrança da conta.

## Camadas

Organização adotada para separar responsabilidades:

- API: `app/api/routes/`
- Casos de uso: `app/application/use_cases/`
- Domínio: `app/domain/` para regras e exceções; os modelos persistidos ficam em `app/infrastructure/database/models/`.
- Persistência e segurança: `app/infrastructure/`
- Configuração e utilitários comuns: `app/core/`

O `main.py` da raiz permanece como ponto de compatibilidade para o comando Docker atual e importa `app.main`. Novas mudanças devem preservar essa entrada e os contratos HTTP existentes.

## Funcionalidades

- Cadastro e login de usuário.
- Validação de credenciais e armazenamento de senhas com bcrypt.
- Emissão e validação de JWT.
- Consulta da identidade autenticada.
- Associação de usuários a tenants e escritórios.
- Controle de acesso baseado no estado do trial e da assinatura.
- Operações de assinatura e integração de cobrança com o Asaas.
- Recepção e deduplicação de webhooks do Asaas.

## Dependências

- Banco de usuários e tenants via SQLAlchemy e MySQL/PyMySQL.
- Provedor JWT via `python-jose`.
- Serviço de hashing de senhas via `bcrypt`.
- API externa do Asaas via `httpx`, para operações de cobrança.

## Regras

- Senhas nunca são armazenadas em texto puro; usar bcrypt para criar e validar hashes.
- Tokens JWT usam HS256, têm expiração de 8 horas na implementação atual e carregam identidade, papel e escopo do tenant.
- Erros de autenticação não devem revelar se o usuário existe; login retorna mensagem genérica para credenciais inválidas.
- Rotas devem distinguir autenticação de autorização: fluxos necessários para consultar ou regularizar cobrança podem aceitar uma conta sem acesso ativo; operações da plataforma devem aplicar a regra de acesso do tenant.
- Consultas e alterações de dados de usuários e escritórios devem respeitar o `tenant_id` obtido de contexto confiável.
- A autorização por escritório deve ser validada pelo serviço responsável pelo recurso, sem confiar em identificadores fornecidos pelo cliente.
- Eventos de cobrança devem ser autenticados e processados de forma idempotente.
- Segredos e credenciais devem vir da configuração do ambiente e nunca ser registrados em logs ou incluídos no repositório.
- Alterações de schema requerem migração versionada; `create_all()` não substitui migrações.
- Preservar caminhos, payloads e formatos de resposta atuais, incluindo campos camelCase consumidos por clientes existentes.

## Como alterar

- Endpoints de cadastro/login: `app/api/routes/auth_routes.py`.
- Consulta da identidade autenticada: `app/api/routes/user_routes.py`.
- Endpoints de cobrança: `app/api/routes/billing_routes.py`.
- Regra de acesso e concessão de período de assinatura: `app/application/use_cases/`.
- Erros de domínio: `app/domain/exceptions.py`.
- Schemas HTTP: `app/api/schemas/`.
- Modelos e sessões de banco: `app/infrastructure/database/`.
- JWT e hashing: `app/infrastructure/security/`.
- Configuração e normalização: `app/core/`.
- Ao alterar contratos ou regras, atualizar também `knowledge.md` e os clientes afetados.

## Testes

- Unitários: `tests/unit/`.
- Integração: `tests/integration/`.
- Os testes usam `unittest`; o cliente de integração cobre health checks sem inicializar o banco. O ambiente local precisa instalar `requirements.txt` para executá-los.

Use Python 3.12 localmente, alinhado ao `Dockerfile` e às versões fixadas no `requirements.txt`. Python 3.13 pode levar o `pip` a tentar compilar `pydantic-core` para essa combinação de dependências.

## Ambiente de desenvolvimento e build

Use Python 3.12, alinhado ao `Dockerfile` e às dependências fixadas. A partir da raiz do microserviço:

```powershell
py -3.12 -m venv .venv312
.\.venv312\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m unittest discover -s tests/unit -v
python -m unittest discover -s tests/integration -v
docker build -t svc-auth:teste .
docker image ls svc-auth
```