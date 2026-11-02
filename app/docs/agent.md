# Instruções do agente — app central Kealex

Antes de alterar este backend, leia `knowledge.md` e `SERVICE.md`.

- Trate `app/main.py` como composição da API central; handlers ficam em `app/api/routes/`.
- Preserve métodos, caminhos, aliases, autenticação, códigos HTTP, payloads, nomes de campos e respostas existentes.
- Mantenha o isolamento por tenant usando claims autenticados e valide o papel nas rotas administrativas.
- Não exponha tokens, chaves de API, dados pessoais ou credenciais em logs, código, documentação ou testes.
- O banco é compartilhado: não altere tabelas ou colunas sem migração versionada e análise de compatibilidade.
- Use rotas/schemas em `app/api/`, casos de uso em `app/application/`, modelos e integrações em `app/infrastructure/` e configuração em `app/core/`. `app/legacy_context.py` é uma ponte temporária; não adicione novas regras a esse módulo.
- Evite mudanças simultâneas em vários domínios. Preserve o startup `_init_db`, o import path `app.main:app` e o Dockerfile.
- Atualize os testes e os documentos desta pasta quando mudar comportamento ou contratos.
