# svc-repositorios

## Responsabilidade

Gerenciar repositórios de arquivos locais, CDN e Google Drive, indexar seus arquivos e receber uploads em repositórios locais. Os dados são isolados por tenant.

## Camadas

- API: `app/api/routes/` e `app/api/schemas/`
- Casos de uso: `app/application/use_cases/`
- Entidades: `app/domain/entities/`
- Persistência e integrações: `app/infrastructure/`
- Configuração: `app/core/`

## Componentes

- `repository_routes.py`: operações CRUD de repositórios.
- `file_routes.py`: listagem, scan e upload de arquivos.
- `repository_scanner.py`: leitura de diretórios, CDN e Google Drive.
- `repository_model.py`: modelos SQLAlchemy `Repositorio` e `Arquivo`.
- `session.py`: engine, sessões e dependência de banco.
- `repository_presenter.py`: conversão dos modelos para o formato da API.
- `main.py`: criação da aplicação, routers e health check.
- `main.py` na raiz mantém a entrada `uvicorn main:app` usada pelo Docker.

## Funcionalidades e rotas

- `GET /health`
- `GET /k1/lex/repositorios`
- `POST /k1/lex/repositorios` (criação, HTTP 201)
- `POST /k1/lex/repositorios/get`
- `POST /k1/lex/repositorios/update`
- `POST /k1/lex/repositorios/delete`
- `GET /k1/lex/repositorios/{repo_id}/arquivos`
- `POST /k1/lex/repositorios/{repo_id}/scan`
- `POST /k1/lex/repositorios/{repo_id}/upload`

## Dependências e configuração

- MySQL/PyMySQL e SQLAlchemy.
- JWT HS256 com `KEALEX_SECRET_KEY` ou `KEALEX_JWT_SECRET`.
- `KEALEX_DATABASE_URL` ou `KEALEX_DB_HOST`, `KEALEX_DB_NAME`, `KEALEX_DB_USER`, `KEALEX_DB_PASSWORD` e opcionalmente `KEALEX_DB_PORT`.
- `STORAGE_PATH` define o armazenamento de uploads (padrão `/tmp/repositorios`).
- `GDRIVE_TOKEN` permite consultar o Google Drive.

## Regras

- Todas as consultas de repositórios usam o `tenant_id` validado no JWT.
- Upload só é permitido para repositórios do tipo `local`.
- Repositórios CDN exigem `url`; locais exigem `caminhoLocal`; Google Drive exige `gdriveFolder`.
- Tabelas existentes não são alteradas por `create_all`; mudanças de schema exigem migração versionada.
- Não registrar tokens ou credenciais de banco nos logs.

## Testes

- Unitários: `tests/unit`.
- Integração: `tests/integration`.

Instale `requirements.txt` e rode da raiz do serviço:

```powershell
python -m unittest discover -s tests/unit -v
python -m unittest discover -s tests/integration -v
docker build -t svc-repositorios:teste .
```
