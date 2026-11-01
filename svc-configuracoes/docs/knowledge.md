# Base de conhecimento — svc-configuracoes

## Visão geral

API FastAPI multi-tenant para configurações gerais, CDN e banco, políticas de IA, chaves pessoais de provedores, agentes e contexto no Google Drive. `main.py` na raiz é mantido para compatibilidade com `uvicorn main:app`.

## Dados persistidos

O serviço conserva os modelos e tabelas atuais: `cfg_geral`, `cfg_cdn`, `cfg_database`, `cfg_ia`, `cfg_ia_providers`, `cfg_usuarios`, `cfg_seguranca`, `cfg_notificacoes`, `user_api_keys`, `agentes_ia`, políticas e uso de tokens de IA, `drive_sources` e `indexacao_arquivos`. Os modelos foram movidos para `app/infrastructure/database/models/configuration_model.py`; os nomes e colunas existentes devem ser preservados.

## Contratos e fluxos

- Configurações e preferências usam os endpoints em `/k1/lex/configuracoes/...`.
- Administração, agentes pessoais e políticas usam `/k1/lex/agentes/...` e `/k1/lex/ia/...`.
- Fontes e arquivos do Drive usam `/k1/lex/drive-sources/...`.
- A maioria das operações exige JWT com papel `admin`; rotas pessoais usam a identidade autenticada e tenant do token.
- Chaves pessoais são criptografadas no armazenamento e mascaradas na listagem. A chave completa não deve ser retornada.
- O contexto Drive é gerado a partir dos arquivos indexados vinculados a fontes ativas.
- Health check: `GET /health`, resposta `{"status":"ok","service":"svc-configuracoes"}`.

## Configuração

Banco: `KEALEX_DATABASE_URL` ou conjunto `KEALEX_DB_HOST`, `KEALEX_DB_NAME`, `KEALEX_DB_USER`, `KEALEX_DB_PASSWORD` e `KEALEX_DB_PORT` opcional.

Autenticação: `KEALEX_SECRET_KEY` ou `KEALEX_JWT_SECRET`.

Criptografia de chaves pessoais: `KEALEX_API_KEYS_ENCRYPTION_KEY` aceita chave Fernet. Sem ela, o código deriva a chave de `KEALEX_JWT_SECRET` ou `KEALEX_SECRET_KEY` com o sufixo estável `:user-api-keys:v1`. Alterar o segredo derivador torna os valores já armazenados impossíveis de descriptografar.

As credenciais de Google Drive são fornecidas pelo cliente no fluxo de cadastro de fonte e não devem ser copiadas para documentação ou logs.

## Desenvolvimento

Use Python 3.12, de acordo com o Dockerfile. Após instalar `requirements.txt`, rode `python -m unittest discover -s tests -v`. Gere a imagem com `docker build -t svc-configuracoes:teste .` a partir desta pasta.
