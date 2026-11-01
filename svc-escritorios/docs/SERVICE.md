# svc-escritorios

## Responsabilidade

Gerenciar escritórios de um tenant, credenciais de acesso da conta do escritório, associação de advogados e limites de membros.

## Camadas

- API: `app/api/routes/`, `app/api/schemas/` e `app/api/dependencies.py`
- Casos de uso e apresentação: `app/application/use_cases/`
- Persistência: `app/infrastructure/database/`
- Segurança: dependências JWT em `app/api/dependencies.py`
- Configuração: `app/core/config.py`

## Componentes

- `office_routes.py`: listagem, consulta, criação, alteração e exclusão de escritórios, credenciais e associação de membros/códigos.
- `office_schema.py`: contratos HTTP existentes.
- `office_model.py`: modelo SQLAlchemy da tabela `escritorios`.
- `office_usage.py`: consulta de uso do limite de advogados.
- `office_presenter.py`: serialização de respostas.

## Dependências

- Banco MySQL compartilhado via SQLAlchemy/PyMySQL e configuração `KEALEX_DATABASE_URL` ou `KEALEX_DB_*`.
- JWT HS256 via `KEALEX_SECRET_KEY` ou `KEALEX_JWT_SECRET`.
- Tabela compartilhada `usuarios` para criar credenciais e validar membros.

## Regras

- Todas as consultas e alterações de escritório devem respeitar o tenant do token.
- Escritórios gerenciam apenas seus vínculos; administradores executam operações administrativas.
- Validar capacidade antes de associar advogados ativos e preservar bloqueios transacionais existentes.
- Senhas iniciais são armazenadas com bcrypt; nunca retorná-las ou registrá-las em logs.
- Preserve tabela, colunas, rotas `/v1/lex/escritorios` e formato camelCase das respostas.
- Alterações de schema compartilhado exigem migração versionada.

## Como alterar

- Endpoints: `app/api/routes/office_routes.py`.
- Schemas: `app/api/schemas/office_schema.py`.
- Contagem de membros: `app/application/use_cases/office_usage.py`.
- Respostas: `app/application/use_cases/office_presenter.py`.
- Modelo e sessão: `app/infrastructure/database/`.
- JWT: `app/api/dependencies.py`.

## Testes e build

O Dockerfile usa Python 3.11. Instale `requirements.txt` com essa versão e execute na raiz do serviço:

```powershell
python -m unittest discover -s tests -v
docker build -t svc-escritorios:teste .
```
