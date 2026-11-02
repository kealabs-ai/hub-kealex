# app — API central Kealex

## Responsabilidade

Backend FastAPI central do hub Kealex. O módulo atual agrega endpoints usados por vários domínios, como autenticação e assinatura, processos, clientes, documentos, financeiro, prazos, audiências, intimações, atividades, configurações e recursos de IA.

## Camadas

- API: `app/api/routes/`, `app/api/schemas/` e `app/api/dependencies.py`.
- Casos de uso e presenters: `app/application/use_cases/`.
- Modelos de persistência: `app/infrastructure/database/models.py`.
- Banco e inicialização: `app/infrastructure/database/session.py` e `initialize.py`.
- Segurança: `app/infrastructure/security/`.
- Configuração: `app/core/config.py`.
- `app/legacy_context.py` ainda reúne helpers compartilhados legados usados pelos routers; novas regras devem ir para sua camada correspondente.

O banco MySQL é compartilhado com os microserviços `svc-*`. Os modelos representam tabelas já utilizadas pelo sistema; alterações no schema precisam ser avaliadas junto aos consumidores e aplicadas por migração versionada.

## Componentes

- `app/main.py`: composição FastAPI, CORS e registro de routers.
- `app/api/routes/`: 10 routers separados por domínio.
- `app/api/schemas/schemas.py`: contratos Pydantic existentes.
- `app/infrastructure/database/models.py`: enums e modelos SQLAlchemy.
- `app/infrastructure/security/jwt_provider.py`: emissão e verificação de JWT.
- `app/api/dependencies.py`: autorização administrativa.
- Integrações: Asaas, provedores de IA e APIs externas para modelos.

## Rotas

Os principais grupos de rotas estão em `app/api/routes/`:

- `/auth/*` e `/k1/lex/auth/*`
- `/k1/lex/processos*`, `/k1/lex/clientes*`, `/k1/lex/documentos*`
- `/k1/lex/financeiro*`, `/k1/lex/prazos*`, `/k1/lex/cobrancas*`
- `/k1/lex/audiencias*`, `/k1/lex/intimacoes*`, `/k1/lex/activities*`
- `/k1/lex/configuracoes/*`, `/k1/lex/ia/*`, `/k1/lex/agentes*`
- `/health`, `/k1/lex/health` e `/debug/db-status`

Os 102 handlers extraídos mantêm os decorators e aliases originais, incluindo caminhos sem prefixo e `/v1/lex/*`. Consulte os decorators para métodos e status HTTP exatos.

## Arquitetura desejada para alterações futuras

- API: `app/api/routes/`, `app/api/schemas/` e `app/api/dependencies.py`.
- Casos de uso: `app/application/use_cases/` e portas em `app/application/ports/`.
- Entidades e regras: `app/domain/`.
- SQLAlchemy e integrações: `app/infrastructure/`.
- Configuração compartilhada: `app/core/`.

Novas extrações devem preservar métodos, caminhos, aliases, autenticação, schemas, respostas, tabelas e inicialização. Migre gradualmente os helpers de `legacy_context.py` para casos de uso, dependências e infraestrutura.

## Dependências

As versões estão em `../requirements.txt` (arquivo `requirements.txt` na raiz do repositório). Entre as principais estão FastAPI, Pydantic, SQLAlchemy, PyMySQL, python-jose, bcrypt, cryptography e clientes Google.

## Testes

Os testes do backend central ficam atualmente em arquivos `test_*.py` na raiz do repositório. Há testes de processos, intimações e chaves públicas. Preserve-os e acrescente cobertura direcionada às rotas e regras extraídas.

## Execução

O Dockerfile da raiz copia o pacote `app/` e inicia `uvicorn app.main:app --host 0.0.0.0 --port 8000`. Instale as dependências do `requirements.txt` na raiz antes da execução local.
