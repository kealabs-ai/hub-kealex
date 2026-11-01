# Base de conhecimento — svc-documentos

## Visão geral

O serviço possui dois fluxos: metadados de documentos vinculados a processos e análise documental conversacional. `main.py` na raiz continua sendo o ponto de entrada compatível com `uvicorn main:app`.

## Modelo de dados

`documentos` armazena tenant, usuário, escritório, processo, nome, tipo, status, URL, tamanho e timestamps. A análise usa `analise_documentos_conversas`, `analise_documentos_arquivos` e `analise_documentos_mensagens`, com índices por proprietário e conversa. Os modelos preservam os nomes de tabela e campos legados.

## Contratos

- CRUD de documentos: `/v1/lex/documentos` e operações `/get`, `/by-processo`, `/update`, `/delete`.
- Análise documental: `/k1/lex/analise-documentos/conversas`, com recursos de upload, mensagens e remoção de documentos.
- Health check: `GET /health`, resposta `{"status":"ok","service":"svc-documentos"}`.
- Os schemas e caminhos atuais mantêm os nomes camelCase de entrada/saída e os enums `tipo_doc_enum` e `status_doc_enum`.

## Segurança e processamento

As rotas autenticadas usam JWT e o guard de acesso/trial disponível no ambiente. O fluxo de análise restringe acesso ao advogado e filtra conversas/documentos por `tenant_id` e `user_id`. Uploads aplicam limites de bytes, páginas e conteúdo. PDF pode usar extração textual ou OCR; DOCX, TXT e Markdown usam os leitores implementados no roteador.

As chaves pessoais de IA são obtidas do banco compartilhado e descriptografadas conforme `KEALEX_API_KEYS_ENCRYPTION_KEY`, `KEALEX_JWT_SECRET` ou `KEALEX_SECRET_KEY`, com o sufixo legado `:user-api-keys:v1` quando derivadas. Nunca registrar chaves, JWTs ou conteúdo confidencial dos documentos.

## Configuração e operação

O banco usa `KEALEX_DATABASE_URL` ou `KEALEX_DB_HOST`, `KEALEX_DB_NAME`, `KEALEX_DB_USER`, `KEALEX_DB_PASSWORD` e `KEALEX_DB_PORT` opcional. O segredo JWT obrigatório é `KEALEX_SECRET_KEY` ou `KEALEX_JWT_SECRET`.

Use Python 3.12, conforme o Dockerfile. Instale `requirements.txt`, rode `python -m unittest discover -s tests -v` e gere a imagem com `docker build -t svc-documentos:teste .` no diretório do serviço.
