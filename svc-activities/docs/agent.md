# Instruções para agentes — `svc-activities`

Antes de alterar este microserviço, leia [`knowledge.md`](knowledge.md) e [`SERVICE.md`](SERVICE.md). A aplicação fica em `app/`; o `main.py` da raiz é uma entrada de compatibilidade para o Docker.

## Regras de trabalho

1. Preserve os métodos, aliases de rota, status HTTP, schemas e formatos de resposta existentes.
2. Mantenha o isolamento por `user_id` e `tenant_id` derivados do JWT validado. Não use valores enviados pelo cliente como autoridade de escopo.
3. Valide mudanças nas rotas e nos schemas com os contratos atuais, incluindo aliases camelCase/snake_case de datas e status.
4. Não altere schema sem migração versionada; `Base.metadata.create_all()` não atualiza tabelas existentes.
5. Mantenha configurações e segredos no ambiente. Não registre tokens ou acrescente logs de dados pessoais/sensíveis.
6. Preserve a configuração atual de CORS e o middleware de log ao mexer no `app/main.py` ou em `app/core/`.
7. Atualize [`knowledge.md`](knowledge.md) e [`SERVICE.md`](SERVICE.md) junto com mudanças em comportamento, configuração, rotas ou execução.
8. Execute os testes unitários e de integração pertinentes quando as dependências estiverem instaladas.

## Mapa do código

- Rotas: `app/api/routes/activity_routes.py`.
- Schemas: `app/api/schemas/activity_schema.py`.
- Regras de suporte: `app/application/use_cases/activity_support.py`.
- Modelos e banco: `app/infrastructure/database/`.
- JWT: `app/infrastructure/security/jwt_provider.py`.
- Configuração e middleware: `app/core/`.

O middleware atual registra corpos de requisição e resposta das rotas de atividades no stdout. Considere esse comportamento ao lidar com dados sensíveis e não amplie seu escopo sem necessidade.
