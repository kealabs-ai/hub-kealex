# Instruções do agente — svc-financeiro

- Leia `knowledge.md` e `SERVICE.md` antes de alterar o serviço.
- Separe API, schemas, regras de aplicação, domínio, persistência e configuração nas camadas de `app/`.
- Preserve os contratos HTTP, o isolamento por tenant, status, enums e valores em centavos.
- Não altere schema sem migração versionada e não exponha dados financeiros de outro tenant.
- Preserve `main.py` na raiz como entrada `uvicorn main:app`.
- Adicione testes relevantes e atualize a documentação quando contratos ou regras mudarem.
