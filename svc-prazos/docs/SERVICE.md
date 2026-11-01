# svc-prazos

## Responsabilidade

Gerenciar prazos jurídicos vinculados a processos, advogados, escritórios e tenants, incluindo consulta por processo e vencimentos próximos.

## Camadas

- API: `app/api/routes/`, `app/api/schemas/` e `app/api/dependencies.py`
- Casos de uso e apresentação: `app/application/use_cases/`
- Domínio: `app/domain/entities/`
- Persistência: `app/infrastructure/database/`
- Configuração: `app/core/config.py`

## Componentes

- `prazo_routes.py`: listagem, consulta, filtro por vencimento/processo, criação, atualização e exclusão.
- `prazo_schema.py`: contratos de entrada.
- `prazo_status.py`: estados pendente, concluído e vencido.
- `prazo_model.py`: modelo SQLAlchemy da tabela `prazos` existente.
- `due_date_window.py`: cálculo do intervalo de vencimentos.
- `prazo_presenter.py`: serialização camelCase.

## Dependências

- MySQL via SQLAlchemy/PyMySQL, configurado por `KEALEX_DATABASE_URL` ou `KEALEX_DB_*`.
- JWT HS256 via `KEALEX_SECRET_KEY` ou `KEALEX_JWT_SECRET`.
- Integração opcional com `trial_guard` para controle de acesso do tenant.
- A tabela compartilhada `processos` é consultada na criação do prazo.

## Regras

- Todas as consultas e alterações são limitadas ao tenant do token.
- Um prazo deve apontar para processo existente no mesmo tenant; advogado e escritório são obtidos do processo.
- Os estados persistidos são `pendente`, `concluido` e `vencido` no enum `status_prazo_enum`.
- Datas de vencimento são armazenadas como strings ISO `YYYY-MM-DD`.
- Preserve tabela, enum, métodos, caminhos `/v1/lex/prazos` e formatos camelCase. Alterações de schema exigem migração versionada.

## Como alterar

- Endpoints: `app/api/routes/prazo_routes.py`.
- Schemas: `app/api/schemas/prazo_schema.py`.
- Intervalo de vencimento: `app/application/use_cases/due_date_window.py`.
- Respostas: `app/application/use_cases/prazo_presenter.py`.
- Status: `app/domain/entities/prazo_status.py`.
- Banco e configuração: `app/infrastructure/database/` e `app/core/config.py`.

## Testes e build

Use Python 3.12, conforme o Dockerfile. Após instalar `requirements.txt`, rode na raiz do serviço:

```powershell
python -m unittest discover -s tests -v
docker build -t svc-prazos:teste .
```
