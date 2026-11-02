# Base de conhecimento — svc-repositorios

## Visão geral

API FastAPI para gerenciar repositórios locais, CDN e Google Drive. O serviço indexa arquivos por scan e permite upload em repositórios locais. O isolamento é feito por `tenant_id` presente no JWT.

## Estrutura

- `app/main.py`: composição da aplicação e inicialização do schema existente.
- `app/api/routes/`: endpoints de repositórios e arquivos.
- `app/api/schemas/`: contratos Pydantic.
- `app/application/use_cases/`: apresentação de dados e scan de repositórios.
- `app/domain/entities/`: enums de tipo/status.
- `app/infrastructure/database/`: modelos SQLAlchemy e sessões.
- `app/api/dependencies.py`: validação JWT.
- `main.py`: compatibilidade com a inicialização atual do container.

## Persistência

O modelo `Repositorio` usa a tabela `repositorios`; `Arquivo` usa `arquivos`. Ambos armazenam `tenant_id`. O banco pode ser configurado pela URL SQLAlchemy ou pelas variáveis `KEALEX_DB_*`. `create_all()` cria tabelas ausentes, mas não migra tabelas existentes.

## Contratos

Os endpoints em `/k1/lex/repositorios` exigem Bearer JWT. As respostas mantêm os nomes camelCase existentes (`tenantId`, `caminhoLocal`, `gdriveFolder`, `createdAt`). O health check público retorna `{"status":"ok","service":"svc-repositorios"}`.

Tipos: `local`, `cdn`, `gdrive`. Status: `ativo`, `inativo`, `erro`. `GDRIVE_TOKEN` é necessário para scan autenticado do Google Drive. `STORAGE_PATH` define o destino do upload.

## Desenvolvimento

Dependências e versões estão em `requirements.txt`; a imagem usa Python 3.11. Configure banco e segredo JWT antes de iniciar. Execute os testes a partir da raiz do serviço com `python -m unittest discover -s tests -v`.
