# Instruções para agentes — `svc-clientes`

Antes de alterar o microserviço, leia [`knowledge.md`](knowledge.md) e [`SERVICE.md`](SERVICE.md). O código está em `app/`; `main.py` na raiz permanece como entrada compatível com Docker.

## Regras de trabalho

1. Preserve métodos, caminho, status HTTP, schemas e nomes de campos das respostas.
2. Restrinja operações pelo `tenant_id` do token; para advogados, filtre também pelo `advogado_id` do token.
3. Preserve a autorização de `admin` e `advogado` e as regras de duplicidade de e-mail por tenant.
4. Não altere schema sem migração versionada; o banco é compartilhado com outros serviços.
5. Mantenha segredos no ambiente e não os registre em logs.
6. Atualize [`knowledge.md`](knowledge.md) e [`SERVICE.md`](SERVICE.md) quando mudar contratos, regras, configuração ou execução.
7. Execute testes unitários e de integração pertinentes quando as dependências estiverem disponíveis.

## Mapa do código

- Rotas: `app/api/routes/clientes_routes.py`.
- Schemas: `app/api/schemas/client_schema.py`.
- Autorização: `app/api/dependencies.py`.
- Respostas: `app/application/use_cases/client_presenter.py`.
- Modelo e banco: `app/infrastructure/database/`.
- JWT: `app/infrastructure/security/jwt_provider.py`.
- Configuração: `app/core/config.py`.
