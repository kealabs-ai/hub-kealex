# Instruções para agentes — `svc-auth`

Estas instruções se aplicam ao trabalho realizado dentro do microserviço `svc-auth`. Antes de alterar comportamento, leia também [`knowledge.md`](knowledge.md) e [`SERVICE.md`](SERVICE.md). A aplicação está em `app/`; `main.py` na raiz é uma entrada de compatibilidade.

## Responsabilidade do serviço

`svc-auth` é uma API FastAPI que cuida de cadastro e login, emissão/verificação de JWT, associação de usuários a tenants e escritórios, controle de trial/acesso e operações de assinatura integradas ao Asaas. O banco MySQL é compartilhado com outros serviços; preserve os contratos e os dados existentes.

## Regras para alterações

1. **Entenda o fluxo inteiro antes de editar.** Localize a rota, schema Pydantic, dependências de autorização, modelos afetados e consumidores. Pesquise também gateway, Compose e frontend quando a mudança afetar URL, payload, headers ou configuração.
2. **Preserve contratos existentes.** Campos camelCase nas respostas e prefixos de rota podem ser consumidos por outros componentes. Não renomeie, remova ou torne campos obrigatórios sem atualizar os consumidores pertinentes.
3. **Mantenha o isolamento por tenant.** Consultas e atualizações de usuários/escritórios devem validar `tenant_id` além do identificador do registro. Não confie apenas em valores enviados pelo cliente; prefira claims validados do JWT.
4. **Proteja credenciais.** Nunca grave senhas em claro, registre tokens/segredos/chaves Asaas nos logs, nem inclua valores reais de `.env` na documentação. Use bcrypt para senhas e o mecanismo JWT já adotado, salvo migração planejada de forma compatível.
5. **Aplique autorização adequada a cada rota.** Diferencie `verify_token` (identidade autenticada, inclusive para regularização de cobrança) de `require_active_trial` (acesso à plataforma sujeito ao estado do tenant). Não bloqueie login ou os fluxos necessários para regularizar uma assinatura vencida.
6. **Trate cobrança como fluxo idempotente.** Webhooks podem ser reenviados. Preserve deduplicação por ID do evento e concessão de período uma única vez por pagamento. Não ative assinaturas apenas com dados enviados pelo navegador; use resposta autenticada do Asaas ou webhook validado.
7. **Não altere schema somente com `create_all()`.** Essa chamada cria tabelas ausentes, mas não migra tabelas existentes. Mudanças de schema precisam de migração compatível com o banco compartilhado e análise do impacto nos demais serviços.
8. **Não introduza credenciais de desenvolvimento em produção.** A inicialização atual cria um administrador padrão quando ausente. Não replique essa senha ou contas de teste em novas rotas, scripts ou documentação operacional.
9. **Mantenha configuração por ambiente.** Banco, segredo JWT e Asaas devem vir do ambiente. Não fixe segredos, URLs de produção, chaves ou dados pessoais no código.
10. **Atualize a documentação junto com o comportamento.** Se mudar endpoint, schema, variáveis de ambiente, regra de autorização, trial ou assinatura, atualize [`knowledge.md`](knowledge.md) e demais referências afetadas.

## Convenções e implementação

- Rotas ficam em `app/api/routes/`, schemas em `app/api/schemas/`, casos de uso em `app/application/use_cases/`, dependências web em `app/api/dependencies.py`, modelos/sessões em `app/infrastructure/database/`, segurança em `app/infrastructure/security/` e configuração em `app/core/`.
- Dependências Python estão em `requirements.txt`; imagem e comando do container estão em `Dockerfile`.
- Use os schemas Pydantic existentes para validar entrada e manter respostas previsíveis. Evite retornar detalhes internos de exceções ou respostas do provedor que exponham dados sensíveis.
- Use sessões com `get_db()` e deixe rollback/fechamento seguir o padrão existente. Em alterações com múltiplas gravações, considere atomicidade e falhas intermediárias.
- A API usa timestamps UTC ingênuos (`datetime.utcnow()`) no código atual. Ao trabalhar com datas, mantenha consistência com os campos existentes e avalie explicitamente as conversões de fuso nas integrações.
- As chamadas ao Asaas usam `httpx` com timeout. Preserve timeouts e traduza falhas externas em respostas HTTP adequadas; não assuma que a resposta externa sempre contém JSON válido.
- CORS atualmente aceita qualquer origem, método e header. Não amplie permissões; mudanças para restringir CORS devem considerar todos os clientes legítimos.

## Verificações ao concluir uma mudança

- Confira o diff e procure por segredos, credenciais, dados pessoais ou alterações acidentais.
- Para mudanças de rota, valide método, caminho, autenticação, status HTTP e formato do payload.
- Para mudanças de banco, revise compatibilidade com registros existentes e serviços que compartilham as tabelas.
- Para mudanças de cobrança, considere eventos duplicados, pagamentos pendentes/vencidos, timeouts e falhas parciais no Asaas.
- Execute somente verificações pertinentes ao escopo solicitado e informe claramente o que foi ou não verificado.

## Pontos conhecidos que exigem atenção

- `KEALEX_SECRET_KEY` (ou `KEALEX_JWT_SECRET`) é necessário para importar/iniciar o serviço; o segredo assina todos os tokens.
- `KEALEX_ASAAS_BASE_URL` também é validada durante a importação. Cobrança requer ainda `KEALEX_ASAAS_API_KEY`; webhook requer `KEALEX_ASAAS_WEBHOOK_TOKEN`.
- A regra geral do `api-gateway/nginx.conf` encaminha caminhos sem regra específica para `hubkealex`; confirme o roteamento efetivo do prefixo `/k1/lex/auth` antes de alterar exposição ou URLs.
- `seed_users.py` é utilitário de desenvolvimento e deve ser conferido contra o schema atual antes do uso; não o execute automaticamente.
- Consulte `knowledge.md` para o resumo atualizado dos modelos, endpoints e regras documentadas.


