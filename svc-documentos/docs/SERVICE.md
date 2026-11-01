# svc-documentos

## Responsabilidade

Gerenciar metadados de documentos associados a processos e oferecer análise documental assistida, com conversas, uploads e consulta contextual.

## Camadas

- API e endpoints: `app/api/routes/`
- Schemas HTTP: `app/api/schemas/`
- Casos de uso e apresentação: `app/application/use_cases/`
- Entidades de domínio: `app/domain/entities/`
- Persistência: `app/infrastructure/database/`
- Segurança e JWT: `app/api/dependencies.py`
- Configuração: `app/core/config.py`

## Componentes

- `document_routes.py`: CRUD e consultas de documentos de processos.
- `document_analysis_routes.py`: análise documental, upload e extração de arquivos, conversas e interação com provedores de IA.
- `document_model.py` e `analysis_model.py`: modelos SQLAlchemy das tabelas existentes.
- `document_presenter.py`: formato de resposta do CRUD.
- `document.py`: enums de tipo e status dos documentos.

## Dependências

- Banco MySQL compartilhado via `KEALEX_DATABASE_URL` ou `KEALEX_DB_*`.
- JWT HS256 via `KEALEX_SECRET_KEY` ou `KEALEX_JWT_SECRET`.
- Provedores de IA e chaves configurados pelo serviço de configurações.
- Tesseract e `antiword` para OCR e compatibilidade com formatos suportados pela imagem Docker.

## Regras

- Consultas e alterações devem permanecer isoladas por tenant e usuário autenticado.
- O processo associado ao documento precisa pertencer ao tenant autenticado.
- Preserve enum names, tabelas, campos e relações lógicas existentes; mudanças de schema exigem migração versionada.
- A análise de conversas é restrita ao perfil advogado e ao proprietário/tenant dos registros.
- Preserve os caminhos `/v1/lex/documentos`, `/k1/lex/analise-documentos` e `GET /health`.
- Conteúdo enviado para extração e provedores externos não deve expor credenciais ou dados fora do escopo autorizado.

## Como alterar

- Endpoints CRUD: `app/api/routes/document_routes.py`.
- Endpoints de análise: `app/api/routes/document_analysis_routes.py`.
- Schemas HTTP: `app/api/schemas/`.
- Apresentação de documentos: `app/application/use_cases/document_presenter.py`.
- Enums de domínio: `app/domain/entities/document.py`.
- Modelos e sessões: `app/infrastructure/database/`.
- Configuração e autenticação: `app/core/config.py` e `app/api/dependencies.py`.

## Testes e build

O Dockerfile usa Python 3.12. Após instalar `requirements.txt`, execute a partir da raiz do serviço:

```powershell
python -m unittest discover -s tests -v
docker build -t svc-documentos:teste .
```
