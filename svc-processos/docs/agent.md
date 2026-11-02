# Instruções do agente — svc-processos

- Leia `knowledge.md` e `SERVICE.md` antes de alterar o serviço.
- Separe API, schemas, casos de uso, domínio, persistência e configuração dentro de `app/`.
- Preserve contratos, dados compartilhados, isolamento por tenant, regras por papel e fases padrão.
- Não altere schema sem migração versionada; não exponha dados de outros tenants.
- Preserve o ponto de entrada raiz `main.py` para `uvicorn main:app`.
- Mantenha os endpoints de diagnóstico existentes, sujeitos à autenticação atual.
- Adicione testes relevantes e atualize os documentos quando contratos ou regras mudarem.
