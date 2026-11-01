# Instruções do agente — svc-prazos

- Leia `knowledge.md` e `SERVICE.md` antes de alterar o serviço.
- Separe rotas, schemas, casos de uso, domínio, persistência e configuração nas camadas existentes em `app/`.
- Preserve contratos HTTP, isolamento por tenant, status, enum e formato ISO das datas.
- Não altere tabelas compartilhadas sem migração versionada.
- Preserve `main.py` na raiz como entrada `uvicorn main:app`.
- Adicione testes relevantes e atualize os documentos quando contratos ou regras mudarem.
