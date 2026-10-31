# Instruções para agentes — `svc-usuarios`

Antes de alterar o microserviço, leia [`knowledge.md`](knowledge.md) e [`SERVICE.md`](SERVICE.md). A aplicação fica em `app/`; `main.py` na raiz é uma entrada de compatibilidade para o Docker.

## Regras de trabalho

1. Preserve rotas, métodos, aliases, status HTTP e formatos de resposta existentes.
2. Mantenha isolamento por `tenant_id`; para escritórios, valide também `escritorio_id` obtido de claims confiáveis.
3. Preserve as regras de papéis: escritório gerencia somente os próprios advogados, e apenas admin exclui usuário.
4. Ao adicionar ou reativar advogado, valide capacidade do escritório e não introduza condições de corrida que ignorem o limite.
5. Não altere tabelas compartilhadas sem migração versionada e análise de compatibilidade com outros serviços.
6. Nunca exponha senha, JWT, segredo ou chave pública em logs ou respostas desnecessárias.
7. Para DataJud, preserve validação de tribunal/número CNJ, timeout e tratamento de erros do provedor.
8. Atualize [`knowledge.md`](knowledge.md) e [`SERVICE.md`](SERVICE.md) quando mudar rotas, regras, configuração ou execução.
9. Execute testes unitários e de integração pertinentes quando as dependências estiverem disponíveis.

## Mapa do código

- CRUD e identidade: `app/api/routes/user_routes.py`.
- Chaves públicas: `app/api/routes/public_key_routes.py`.
- DataJud: `app/api/routes/datajud_routes.py`.
- Schemas: `app/api/schemas/user_schema.py`.
- Casos de uso: `app/application/use_cases/`.
- Modelos e banco: `app/infrastructure/database/`.
- JWT e bcrypt: `app/infrastructure/security/`.
