# Base de conhecimento — svc-escritorios

## Visão geral

API FastAPI para cadastro e administração de escritórios e associação de advogados. `main.py` na raiz continua compatível com `uvicorn main:app`.

## Persistência

O serviço usa a tabela compartilhada `escritorios`, que contém tenant, dados de contato, limite de advogados, código único, estado e timestamps. A tabela `usuarios` fornece contas de escritório e membros. O serviço usa SQL direto nessa tabela compartilhada para preservar o contrato com os demais microsserviços.

## Contratos existentes

- `GET /v1/lex/escritorios`: lista escritórios visíveis ao usuário.
- `POST /v1/lex/escritorios/get`: consulta por identificador.
- `POST /v1/lex/escritorios`: cria escritório.
- `POST /v1/lex/escritorios/criar-acesso`: cria credenciais de acesso do escritório.
- `POST /v1/lex/escritorios/update`, `/delete` e `/associar-membro`: administração do escritório e membros.
- `POST /v1/lex/escritorios/associar-codigo`: associação de advogado autônomo por código.
- `GET /health`: retorna `{"status":"ok","service":"svc-escritorios"}`.

Os contratos usam camelCase onde já definido pelos schemas. Os caminhos e métodos são consumidos pelo gateway e frontend; preserve-os.

## Autorização e regras de negócio

- O JWT contém o tenant e o papel; as consultas devem escopar os dados pelo tenant.
- Admin pode criar/editar/excluir escritórios e associar membros.
- Uma conta de escritório lista apenas o próprio escritório.
- Advogados só podem associar a própria conta usando o código e apenas quando autônomos.
- Criação pelo advogado titular é limitada a um escritório durante o trial.
- O limite de membros conta advogados ativos. A associação usa bloqueios `FOR UPDATE` na tabela do escritório para evitar ultrapassar a quota concorrencialmente.
- Credenciais de escritório são armazenadas com bcrypt.

## Configuração e execução

Configure `KEALEX_DATABASE_URL` ou `KEALEX_DB_HOST`, `KEALEX_DB_NAME`, `KEALEX_DB_USER`, `KEALEX_DB_PASSWORD` e, opcionalmente, `KEALEX_DB_PORT`. Configure também `KEALEX_SECRET_KEY` ou `KEALEX_JWT_SECRET`.

Use Python 3.11, conforme o Dockerfile. Instale `requirements.txt` e rode `python -m unittest discover -s tests -v`. Para build, use `docker build -t svc-escritorios:teste .` dentro desta pasta.
