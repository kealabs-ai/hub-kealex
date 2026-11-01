# Instruções do agente — svc-documentos

- Leia `knowledge.md` e `SERVICE.md` antes de modificar o serviço.
- Mantenha rotas, schemas, regras de aplicação, entidades e persistência nas respectivas camadas em `app/`.
- Preserve contratos, estados, enums, nomes de tabela e limites de upload existentes.
- Reforce o isolamento por tenant e usuário em qualquer consulta ou alteração.
- Não exponha segredos de IA, tokens, dados de documentos ou credenciais em logs e respostas.
- Não altere schema sem migração versionada.
- Preserve `main.py` na raiz como entrada `uvicorn main:app` e o shim de `analysis_router.py` para compatibilidade.
- Adicione testes pertinentes e atualize os documentos se alterar comportamento ou configuração.
