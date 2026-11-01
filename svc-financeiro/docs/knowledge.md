# Base de conhecimento — svc-financeiro

## Visão geral

API FastAPI para registrar e consultar honorários associados a processos, clientes e advogados. `main.py` na raiz preserva o ponto de entrada `uvicorn main:app`.

## Persistência e domínio

A tabela `honorarios` armazena tenant, usuário, escritório, processo, cliente, advogado, descrição, valor em centavos, vencimento, pagamento, status e timestamps. O enum do banco mantém o nome `status_honorario_enum` e os estados `pendente`, `pago`, `vencido` e `cancelado`.

## Contratos existentes

- `GET /v1/lex/financeiro`: lista honorários do tenant autenticado.
- `GET /v1/lex/financeiro/dashboard`: totaliza valores pendentes, pagos, vencidos e geral.
- `POST /v1/lex/financeiro/get`: consulta pelo identificador.
- `POST /v1/lex/financeiro`: cria honorário.
- `POST /v1/lex/financeiro/update`: atualiza dados permitidos.
- `POST /v1/lex/financeiro/delete`: remove o honorário.
- `GET /health`: `{"status":"ok","service":"svc-financeiro"}`.

Os contratos usam nomes camelCase; valores monetários são centavos inteiros. Preserve métodos, caminhos, status HTTP e formatos de resposta.

## Autorização e configuração

As rotas autenticadas usam JWT. O tenant vem de `tenant_id` ou, no token legado, de `sub`. O `trial_guard` é opcional no ambiente e, quando disponível, substitui o guard JWT simples.

Configure banco por `KEALEX_DATABASE_URL` ou `KEALEX_DB_HOST`, `KEALEX_DB_NAME`, `KEALEX_DB_USER`, `KEALEX_DB_PASSWORD` e `KEALEX_DB_PORT` opcional. O segredo JWT obrigatório é `KEALEX_SECRET_KEY` ou `KEALEX_JWT_SECRET`.

Use Python 3.12 conforme o Dockerfile. Instale `requirements.txt`, rode `python -m unittest discover -s tests -v` e faça build com `docker build -t svc-financeiro:teste .` na pasta do serviço.
