# Diretrizes para agentes — svc-configuracoes

Leia `agent.md`, `knowledge.md` e `SERVICE.md` antes de implementar mudanças. Preserve os contratos HTTP e o escopo multi-tenant. Mudanças de schema precisam de migração versionada; segredos não devem ser registrados, retornados ou incluídos nos documentos. Execute os testes pertinentes em `tests/` quando as dependências estiverem instaladas.
