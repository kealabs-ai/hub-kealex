# Instruções do agente — svc-escritorios

- Leia `knowledge.md` e `SERVICE.md` antes de modificar o serviço.
- Separe endpoints, schemas, regras reutilizáveis, domínio e persistência conforme `app/`.
- Preserve contratos HTTP, formatos camelCase, papéis, tenant e regras de quota.
- Mantenha o hash bcrypt das senhas; não exponha senhas, tokens ou dados sensíveis.
- Não altere tabelas compartilhadas sem migração versionada e avaliação de compatibilidade.
- Preserve `main.py` na raiz como entrada de `uvicorn main:app`.
- Adicione testes pertinentes e atualize a documentação quando houver mudanças nos componentes ou contratos.
