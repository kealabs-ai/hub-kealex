# Instruções do agente — svc-cobrancas

- Leia `docs/knowledge.md` e `docs/SERVICE.md` antes de alterar o serviço.
- Analise somente os arquivos diretamente relacionados à mudança.
- Mantenha a separação entre API, contratos, configuração, autenticação e persistência já adotada em `app/`.
- Preserve as rotas legadas, os formatos de request/response e os estados de cobrança existentes.
- Não altere schema de banco sem migração versionada, nem exponha credenciais do Asaas ou segredos JWT.
- Não modifique outros microserviços sem necessidade técnica demonstrável.
- Adicione testes unitários ou de integração relevantes e execute-os quando o ambiente permitir.
- Mantenha `main.py` na raiz como ponto de entrada compatível com `uvicorn main:app` e atualize este guia e `SERVICE.md` quando os componentes mudarem.
