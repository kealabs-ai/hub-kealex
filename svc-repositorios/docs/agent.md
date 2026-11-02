# Instruções do agente — svc-repositorios

Antes de alterar este serviço, leia `knowledge.md` e `SERVICE.md`.

- Preserve rotas, métodos HTTP, payloads, nomes camelCase, status e modelos existentes.
- Filtre todos os acessos aos repositórios pelo `tenant_id` do JWT.
- Mantenha endpoints em `app/api/routes/`, regras de aplicação em `app/application/use_cases/`, entidades em `app/domain/entities/` e persistência em `app/infrastructure/`.
- Não registre nem documente valores de tokens, senhas ou credenciais.
- Não altere schema sem migração versionada; o banco é compartilhado.
- Preserve o comando de container `uvicorn main:app` e atualize o Dockerfile quando adicionar módulos da aplicação.
- Atualize `knowledge.md` e `SERVICE.md` junto com mudanças de comportamento ou configuração.
- Execute verificações unitárias/de integração relevantes e informe dependências ausentes como bloqueio do ambiente.
