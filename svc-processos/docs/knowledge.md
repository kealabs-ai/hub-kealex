# Base de conhecimento — svc-processos

## Visão geral

API FastAPI para processos jurídicos e seu fluxo de fases. `main.py` na raiz continua sendo compatível com `uvicorn main:app`.

## Modelo de dados

- `processos`: tenant, usuário, escritório, número, título, descrição, status, advogado, cliente, vara, tribunal e fase atual.
- `fases`: fases ordenadas do processo, com estado, data de conclusão e relação com `processos`.
- `clientes`: modelo local usado para enriquecer respostas; os dados são compartilhados com `svc-clientes`.
- `processo_clientes`: relação entre processos e clientes existentes, com posição/polo processual, cliente principal e snapshot cadastral.
- `processo_partes`: demais partes envolvidas, sem exigir cadastro de cliente.

Os nomes de tabelas, colunas, enums e relacionamento devem permanecer compatíveis com os serviços que consomem o banco compartilhado.

## Contratos existentes

- CRUD e listagem: `/k1/lex/processos`, `/get`, `/update` e `/delete`.
- Avanço de fase: `POST /k1/lex/processos/avancar-fase`.
- Clientes vinculados: `GET/POST/PUT /k1/lex/processos/{id}/clients`, `PATCH/DELETE /k1/lex/processos/{id}/clients/{clientId}`.
- Demais partes: `GET/POST/PUT /k1/lex/processos/{id}/parties`.
- Próximas fases: `POST /k1/lex/processos/{processo_id}/proximas-fases`.
- Diagnóstico autenticado: `/k1/lex/processos/{processo_id}/debug-fases`, `/k1/lex/debug/todas-fases`, `/k1/lex/debug/todos-processos` e `/k1/lex/debug/status-completo`.
- Health check: `GET /health`, resposta `{"status":"healthy","service":"svc-processos"}`.

As respostas usam camelCase nos campos públicos. A criação verifica o cliente no tenant e gera as fases padrão: Protocolo, Citação, Contestação, Audiência, Sentença, Recurso e Encerrado.

## Autorização

As rotas validam JWT e o estado atual do tenant no MySQL. O escopo do processo depende do papel: administradores têm acesso no tenant, advogados aos processos de sua autoria/atribuição e clientes aos próprios processos. Não remova o filtro por tenant.

Os vínculos a clientes filtram também por tenant e, para advogados, pelo advogado responsável. O cadastro original não é duplicado nem excluído ao desvincular. Antes de publicar, aplique primeiro `migrations/20261125_client_qualification_fields.sql` no banco compartilhado e depois `migrations/process_client_link.sql`; a segunda migração cria os relacionamentos e converte os vínculos antigos de `processos.cliente_id` em cliente principal.

## Configuração e execução

Configure o banco com `KEALEX_DATABASE_URL` ou `KEALEX_DB_HOST`, `KEALEX_DB_NAME`, `KEALEX_DB_USER`, `KEALEX_DB_PASSWORD` e `KEALEX_DB_PORT` opcional. Configure `KEALEX_SECRET_KEY` ou `KEALEX_JWT_SECRET`. `KEALEX_DEBUG=true` habilita logs DEBUG.

Use Python 3.12 conforme o Dockerfile. Instale `requirements.txt`, rode `python -m unittest discover -s tests -v` e construa a imagem com `docker build -t svc-processos:teste .` nesta pasta.

## Acompanhamento externo de processos

A tabela processos_acompanhados guarda um snapshot Escavador por tenant e escopo (advogado ou organiza??o), com unicidade por n?mero CNJ normalizado. historico_consultas_processuais registra sucesso e falha sem armazenar credenciais. A integra??o ? chamada pelo servi?o svc-integracoes com o JWT do usu?rio; a fase s? ? exibida quando a fonte a informa.

Endpoints protegidos: GET /k1/lex/processos-acompanhados, POST /consultar, GET /{id}, POST /{id}/atualizar e GET /{id}/historico. Aplicar migrations/20261123_processos_acompanhados.sql em bancos existentes antes da publica??o.
