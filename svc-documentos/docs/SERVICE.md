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
- `document_analysis_routes.py`: análise documental, upload e extração de arquivos, conversas, integração Google Drive e interação com provedores de IA.
- `analysis_model.py`: conversas, mensagens, arquivos processados, referências no Google Drive e credenciais criptografadas.
- `google_drive.py`: criptografia de credenciais, autenticação OAuth2/conta de serviço e operações de arquivo no Drive.
- `document_presenter.py`: formato de resposta do CRUD.
- `document.py`: enums de tipo e status dos documentos.

## Dependências

- Banco MySQL compartilhado via `KEALEX_DATABASE_URL` ou `KEALEX_DB_*`.
- JWT HS256 via `KEALEX_SECRET_KEY` ou `KEALEX_JWT_SECRET`.
- Provedores de IA e chaves configurados pelo serviço de configurações.
- Google Drive API habilitada; credenciais por usuário no Perfil (`authorized_user` OAuth2 ou `service_account`).
- `KEALEX_GOOGLE_DRIVE_ENCRYPTION_KEY` opcional (chave Fernet dedicada). Se ausente, as credenciais são criptografadas com chave derivada de `KEALEX_SECRET_KEY`/`KEALEX_JWT_SECRET`; a chave deve permanecer estável entre deploys.
- Tesseract e `antiword` para OCR e compatibilidade com formatos suportados pela imagem Docker.

## Regras

- Consultas e alterações devem permanecer isoladas por tenant e usuário autenticado.
- O processo associado ao documento precisa pertencer ao tenant autenticado.
- Preserve enum names, tabelas, campos e relações lógicas existentes; mudanças de schema exigem migração versionada.
- A análise de conversas é restrita ao perfil advogado e ao proprietário/tenant dos registros.
- Cada upload da análise é armazenado no Drive do usuário antes de registrar seus metadados. As credenciais nunca são retornadas pela API; remover arquivos da conversa também os remove do Drive.
- O pipeline de análise é processamento Python controlado (extração/OCR, recuperação de trechos e IA); o serviço não disponibiliza execução arbitrária de notebooks Jupyter.
- Preserve os caminhos `/v1/lex/documentos`, `/k1/lex/analise-documentos` e `GET /health`.
- Conteúdo enviado para extração e provedores externos não deve expor credenciais ou dados fora do escopo autorizado.

## Como alterar

- Endpoints CRUD: `app/api/routes/document_routes.py`.
- Endpoints de análise: `app/api/routes/document_analysis_routes.py`.
- Integração Google Drive: `app/infrastructure/google_drive.py` e schema `app/api/schemas/google_drive_schema.py`.
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

Antes de atualizar um banco existente, aplique `migrations/add_google_drive_analysis.sql` uma vez. Para gerar uma chave Fernet dedicada, use `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` e configure o resultado como segredo do ambiente.
