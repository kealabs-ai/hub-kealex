# svc-configuracoes

## Responsabilidade

Armazenar e fornecer configurações de tenants, preferências de IA, chaves de provedores, agentes de IA e fontes de contexto do Google Drive.

## Camadas

- API e endpoints: `app/api/routes/`
- Contratos HTTP: `app/api/schemas/`
- Casos de uso: `app/application/use_cases/`
- Modelos persistidos: `app/infrastructure/database/models/`
- Sessões e conexão: `app/infrastructure/database/session.py`
- Autenticação: `app/api/dependencies.py`
- Configuração: `app/core/config.py`

## Componentes

- `configuration_routes.py`: configurações gerais, CDN, banco, IA, chaves do usuário, usuários, segurança e notificações.
- `agent_routes.py`: agentes, políticas de IA por plano/usuário e catálogo de modelos.
- `drive_routes.py`: fontes Google Drive, sincronização e contexto de arquivos.
- `configuration_model.py`: modelos SQLAlchemy das tabelas já utilizadas pelo serviço.
- `ai_catalog.py`, `ai_policy.py`, `user_api_keys.py` e `configuration_support.py`: regras reutilizáveis da aplicação.

## Dependências e ambiente

- Banco MySQL via `KEALEX_DATABASE_URL` ou variáveis `KEALEX_DB_*`.
- JWT via `KEALEX_SECRET_KEY` ou `KEALEX_JWT_SECRET`.
- Google Drive via service account informada na operação correspondente.
- `KEALEX_API_KEYS_ENCRYPTION_KEY` é opcional; quando ausente, a chave de criptografia é derivada do segredo JWT conforme o comportamento existente.

## Regras

- Todas as consultas e alterações devem manter o escopo por tenant e usuário exigido pela rota.
- Chaves de API devem permanecer criptografadas no banco e mascaradas nas respostas.
- A rota de ambiente do banco nunca retorna a senha em texto claro.
- Credenciais de Google e provedores de IA não devem aparecer em logs ou respostas.
- As tabelas e seus campos são compartilhados com outros componentes; alterações de schema exigem migração versionada.
- Preserve os caminhos `/k1/lex/configuracoes`, `/k1/lex/agentes`, `/k1/lex/ia`, `/k1/lex/drive-sources` e a resposta atual de `GET /health`.

## Como alterar

- Rotas: módulo correspondente em `app/api/routes/`.
- Schemas Pydantic: `app/api/schemas/`.
- Regras e transformações: `app/application/use_cases/`.
- Persistência: `app/infrastructure/database/`.
- JWT: `app/api/dependencies.py`.
- Configuração de ambiente e criptografia: `app/core/config.py`.

## Testes e build

O Dockerfile usa Python 3.12. Instale `requirements.txt` nessa versão e, a partir da raiz do serviço, rode:

```powershell
python -m unittest discover -s tests -v
docker build -t svc-configuracoes:teste .
```
