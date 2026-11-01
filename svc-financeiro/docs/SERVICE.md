# svc-financeiro

## Responsabilidade

Gerenciar honorários vinculados a processos, clientes, advogados e escritórios, incluindo status, vencimentos e totais financeiros do tenant.

## Camadas

- API: `app/api/routes/`, `app/api/schemas/` e `app/api/dependencies.py`
- Casos de uso: `app/application/use_cases/`
- Domínio: `app/domain/entities/`
- Persistência: `app/infrastructure/database/`
- Configuração: `app/core/config.py`

## Componentes

- `financial_routes.py`: listagem, dashboard, consulta, criação, atualização e exclusão de honorários.
- `honorario_schema.py`: contratos de entrada da API.
- `honorario_status.py`: enum de estados do honorário.
- `honorario_model.py`: modelo SQLAlchemy da tabela existente `honorarios`.
- `honorario_presenter.py`: serialização camelCase.
- `financial_dashboard.py`: cálculo dos totais por status.

## Dependências

- MySQL via SQLAlchemy/PyMySQL, usando `KEALEX_DATABASE_URL` ou variáveis `KEALEX_DB_*`.
- JWT HS256 usando `KEALEX_SECRET_KEY` ou `KEALEX_JWT_SECRET`.
- Integração opcional com `trial_guard` para limitar o acesso conforme o estado do tenant.

## Regras

- Consultas são sempre filtradas pelo tenant do token.
- Valores são armazenados em centavos.
- Os status existentes são `pendente`, `pago`, `vencido` e `cancelado`.
- Preserve a tabela e os enums existentes; alterações de schema exigem migração versionada.
- Preserve os caminhos `/v1/lex/financeiro` e os campos camelCase da API.

## Como alterar

- Endpoints: `app/api/routes/financial_routes.py`.
- Contratos: `app/api/schemas/honorario_schema.py`.
- Cálculo do dashboard: `app/application/use_cases/financial_dashboard.py`.
- Respostas: `app/application/use_cases/honorario_presenter.py`.
- Status: `app/domain/entities/honorario_status.py`.
- Persistência e configuração: `app/infrastructure/database/` e `app/core/config.py`.

## Testes e build

Use Python 3.12, alinhado ao Dockerfile. Após instalar `requirements.txt`, execute na raiz do serviço:

```powershell
python -m unittest discover -s tests -v
docker build -t svc-financeiro:teste .
```
