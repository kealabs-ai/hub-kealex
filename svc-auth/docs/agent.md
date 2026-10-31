# InstruÃ§Ãµes para agentes â€” `svc-auth`

Estas instruÃ§Ãµes se aplicam ao trabalho realizado dentro do microserviÃ§o `svc-auth`. Antes de alterar comportamento, leia tambÃ©m [`knowledge.md`](knowledge.md) e [`docs/SERVICE.md`](SERVICE.md). A aplicaÃ§Ã£o estÃ¡ em `app/`; `main.py` na raiz Ã© uma entrada de compatibilidade.

## Responsabilidade do serviÃ§o

`svc-auth` Ã© uma API FastAPI que cuida de cadastro e login, emissÃ£o/verificaÃ§Ã£o de JWT, associaÃ§Ã£o de usuÃ¡rios a tenants e escritÃ³rios, controle de trial/acesso e operaÃ§Ãµes de assinatura integradas ao Asaas. O banco MySQL Ã© compartilhado com outros serviÃ§os; preserve os contratos e os dados existentes.

## Regras para alteraÃ§Ãµes

1. **Entenda o fluxo inteiro antes de editar.** Localize a rota, schema Pydantic, dependÃªncias de autorizaÃ§Ã£o, modelos afetados e consumidores. Pesquise tambÃ©m gateway, Compose e frontend quando a mudanÃ§a afetar URL, payload, headers ou configuraÃ§Ã£o.
2. **Preserve contratos existentes.** Campos camelCase nas respostas e prefixos de rota podem ser consumidos por outros componentes. NÃ£o renomeie, remova ou torne campos obrigatÃ³rios sem atualizar os consumidores pertinentes.
3. **Mantenha o isolamento por tenant.** Consultas e atualizaÃ§Ãµes de usuÃ¡rios/escritÃ³rios devem validar `tenant_id` alÃ©m do identificador do registro. NÃ£o confie apenas em valores enviados pelo cliente; prefira claims validados do JWT.
4. **Proteja credenciais.** Nunca grave senhas em claro, registre tokens/segredos/chaves Asaas nos logs, nem inclua valores reais de `.env` na documentaÃ§Ã£o. Use bcrypt para senhas e o mecanismo JWT jÃ¡ adotado, salvo migraÃ§Ã£o planejada de forma compatÃ­vel.
5. **Aplique autorizaÃ§Ã£o adequada a cada rota.** Diferencie `verify_token` (identidade autenticada, inclusive para regularizaÃ§Ã£o de cobranÃ§a) de `require_active_trial` (acesso Ã  plataforma sujeito ao estado do tenant). NÃ£o bloqueie login ou os fluxos necessÃ¡rios para regularizar uma assinatura vencida.
6. **Trate cobranÃ§a como fluxo idempotente.** Webhooks podem ser reenviados. Preserve deduplicaÃ§Ã£o por ID do evento e concessÃ£o de perÃ­odo uma Ãºnica vez por pagamento. NÃ£o ative assinaturas apenas com dados enviados pelo navegador; use resposta autenticada do Asaas ou webhook validado.
7. **NÃ£o altere schema somente com `create_all()`.** Essa chamada cria tabelas ausentes, mas nÃ£o migra tabelas existentes. MudanÃ§as de schema precisam de migraÃ§Ã£o compatÃ­vel com o banco compartilhado e anÃ¡lise do impacto nos demais serviÃ§os.
8. **NÃ£o introduza credenciais de desenvolvimento em produÃ§Ã£o.** A inicializaÃ§Ã£o atual cria um administrador padrÃ£o quando ausente. NÃ£o replique essa senha ou contas de teste em novas rotas, scripts ou documentaÃ§Ã£o operacional.
9. **Mantenha configuraÃ§Ã£o por ambiente.** Banco, segredo JWT e Asaas devem vir do ambiente. NÃ£o fixe segredos, URLs de produÃ§Ã£o, chaves ou dados pessoais no cÃ³digo.
10. **Atualize a documentaÃ§Ã£o junto com o comportamento.** Se mudar endpoint, schema, variÃ¡veis de ambiente, regra de autorizaÃ§Ã£o, trial ou assinatura, atualize [`knowledge.md`](knowledge.md) e demais referÃªncias afetadas.

## ConvenÃ§Ãµes e implementaÃ§Ã£o

- Rotas ficam em `app/api/routes/`, schemas em `app/api/schemas/`, casos de uso em `app/application/use_cases/`, dependÃªncias web em `app/api/dependencies.py`, modelos/sessÃµes em `app/infrastructure/database/`, seguranÃ§a em `app/infrastructure/security/` e configuraÃ§Ã£o em `app/core/`.
- DependÃªncias Python estÃ£o em `requirements.txt`; imagem e comando do container estÃ£o em `Dockerfile`.
- Use os schemas Pydantic existentes para validar entrada e manter respostas previsÃ­veis. Evite retornar detalhes internos de exceÃ§Ãµes ou respostas do provedor que exponham dados sensÃ­veis.
- Use sessÃµes com `get_db()` e deixe rollback/fechamento seguir o padrÃ£o existente. Em alteraÃ§Ãµes com mÃºltiplas gravaÃ§Ãµes, considere atomicidade e falhas intermediÃ¡rias.
- A API usa timestamps UTC ingÃªnuos (`datetime.utcnow()`) no cÃ³digo atual. Ao trabalhar com datas, mantenha consistÃªncia com os campos existentes e avalie explicitamente as conversÃµes de fuso nas integraÃ§Ãµes.
- As chamadas ao Asaas usam `httpx` com timeout. Preserve timeouts e traduza falhas externas em respostas HTTP adequadas; nÃ£o assuma que a resposta externa sempre contÃ©m JSON vÃ¡lido.
- CORS atualmente aceita qualquer origem, mÃ©todo e header. NÃ£o amplie permissÃµes; mudanÃ§as para restringir CORS devem considerar todos os clientes legÃ­timos.

## VerificaÃ§Ãµes ao concluir uma mudanÃ§a

- Confira o diff e procure por segredos, credenciais, dados pessoais ou alteraÃ§Ãµes acidentais.
- Para mudanÃ§as de rota, valide mÃ©todo, caminho, autenticaÃ§Ã£o, status HTTP e formato do payload.
- Para mudanÃ§as de banco, revise compatibilidade com registros existentes e serviÃ§os que compartilham as tabelas.
- Para mudanÃ§as de cobranÃ§a, considere eventos duplicados, pagamentos pendentes/vencidos, timeouts e falhas parciais no Asaas.
- Execute somente verificaÃ§Ãµes pertinentes ao escopo solicitado e informe claramente o que foi ou nÃ£o verificado.

## Pontos conhecidos que exigem atenÃ§Ã£o

- `KEALEX_SECRET_KEY` (ou `KEALEX_JWT_SECRET`) Ã© necessÃ¡rio para importar/iniciar o serviÃ§o; o segredo assina todos os tokens.
- `KEALEX_ASAAS_BASE_URL` tambÃ©m Ã© validada durante a importaÃ§Ã£o. CobranÃ§a requer ainda `KEALEX_ASAAS_API_KEY`; webhook requer `KEALEX_ASAAS_WEBHOOK_TOKEN`.
- A regra geral do `api-gateway/nginx.conf` encaminha caminhos sem regra especÃ­fica para `hubkealex`; confirme o roteamento efetivo do prefixo `/k1/lex/auth` antes de alterar exposiÃ§Ã£o ou URLs.
- `seed_users.py` Ã© utilitÃ¡rio de desenvolvimento e deve ser conferido contra o schema atual antes do uso; nÃ£o o execute automaticamente.
- Consulte `knowledge.md` para o resumo atualizado dos modelos, endpoints e regras documentadas.


