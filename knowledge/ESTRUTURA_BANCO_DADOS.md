# Estrutura do banco de dados e padronização de nomes

> Documento baseado nos modelos SQLAlchemy e nas migrações presentes no repositório. Não foi feita introspecção de uma instância ativa; portanto, migrações executadas fora do repositório podem alterar o esquema real. Tipos, nulabilidade e defaults devem ser conferidos no banco antes de qualquer alteração.

## Visão geral

O sistema usa tabelas relacionais com identificadores UUID armazenados como `String(36)`, separação multi-tenant por `tenant_id` em grande parte dos domínios e serviços organizados por contexto. Os modelos aparecem em `svc-* / app/infrastructure/database/models`; migrações SQL adicionais estão em `migrations/`.

### Convenções observadas

- Tabelas em plural e `snake_case` (por exemplo, `processos`, `historico_cobrancas`).
- Chave primária normalmente chamada `id`; referências usam sufixo `_id`.
- Campos de auditoria frequentemente chamados `created_at` e `updated_at`.
- Mistura de português e inglês, inclusive na mesma tabela (`valor_centavos`, `created_at`, `api_key_encrypted`).
- Datas representadas como `DateTime`, `Date` e também `String(10)`; alguns campos chamados `data_*` e outros `*_at`.
- Estados e categorias armazenados como `String`, `Enum` ou texto JSON, sem uniformidade.

## Inventário por domínio

As listas abaixo registram os campos declarados nos modelos. `PK` identifica a chave primária; campos não listados como opcionais são declarados obrigatórios nos modelos, salvo diferenças no default indicado. Restrições e índices são resumidos quando explícitos.

### Identidade, acesso e organizações

| Tabela | Campos |
|---|---|
| `tenants` | `id` (PK), `nome`, `slug` (único), `plano`, `trial_started_at`, `trial_expires_at`, `asaas_customer_id`, `billing_name`, `billing_email`, `billing_cpf_cnpj`, `billing_phone`, `billing_mobile_phone`, `billing_postal_code`, `billing_address`, `billing_address_number`, `billing_complement`, `billing_neighborhood`, `billing_city`, `billing_state`, `asaas_subscription_id`, `subscription_plan`, `subscription_cycle`, `subscription_expires_at`, `last_paid_payment_id`, `subscription_status`, `next_due_date`, `ativo`, `created_at`, `updated_at` |
| `usuarios` | `id` (PK), `tenant_id`, `escritorio_id` (opcional), `codigo` (opcional), `oab` (opcional, presente em modelo de serviço), `nome`, `email`, `senha_hash`, `role` (enum), `ativo`, `created_at`, `updated_at` |
| `escritorios` | `id` (PK), `tenant_id`, `nome`, `cnpj` (opcional), `endereco` (opcional), `telefone` (opcional), `email` (opcional), `limite_advogados`, `codigo` (único no modelo), `ativo`, `created_at`, `updated_at` |
| `usuarios_chaves_publicas` | `id` (PK), `user_id` (FK para `usuarios.id`, cascade delete), `orgao`, `chave_publica`, `created_at`, `updated_at`; único em (`user_id`, `orgao`) |
| `user_api_keys` | `id` (PK), `tenant_id`, `user_id`, `created_by`, `provider`, `model`, `api_key_encrypted`, `is_active`, `created_at`, `updated_at`; único em (`user_id`, `provider`, `model`) |
| `asaas_webhook_events` | `id` (PK), `event`, `received_at` |

### Clientes e processos

| Tabela | Campos |
|---|---|
| `clientes` | `id` (PK), `tenant_id`, `advogado_id`, `nome`, `email`, `telefone` (opcional), `cpf_cnpj` (opcional), `endereco` (opcional), `observacoes` (opcional), `created_at`, `updated_at` |
| `processos` | `id` (PK), `tenant_id`, `user_id`, `escritorio_id` (opcional), `numero`, `titulo`, `descricao`, `status` (enum), `advogado_id`, `cliente_id`, `vara`, `tribunal`, `fase_atual`, `created_at`, `updated_at` |
| `fases` | `id` (PK), `processo_id` (FK para `processos.id`), `label`, `ordem`, `status`, `data_conclusao` (opcional), `created_at`, `updated_at` |
| `documentos` | `id` (PK), `tenant_id`, `user_id`, `escritorio_id` (opcional), `processo_id`, `uploadado_por_id`, `nome`, `tipo` (enum), `status` (enum), `url_arquivo`, `tamanho_bytes`, `created_at`, `updated_at` |
| `prazos` | `id` (PK), `tenant_id`, `user_id`, `escritorio_id` (opcional), `processo_id`, `advogado_id`, `titulo`, `descricao`, `data_vencimento`, `status` (enum), `created_at`, `updated_at` |

### Financeiro

| Tabela | Campos |
|---|---|
| `honorarios` | `id` (PK), `tenant_id`, `user_id`, `escritorio_id` (opcional), `processo_id`, `cliente_id`, `advogado_id`, `descricao`, `valor_centavos`, `data_vencimento`, `data_pagamento` (opcional), `status` (enum), `created_at`, `updated_at` |
| `cobrancas` | `id` (PK), `tenant_id`, `user_id`, `processo_id`, `cliente_id`, `valor_centavos`, `status`, `fase_atual`, `data_vencimento` (opcional), `data_pagamento` (opcional), `motivo_cancelamento` (opcional), `created_at`, `updated_at` |
| `historico_cobrancas` | `id` (PK), `cobranca_id`, `acao`, `fase_anterior` (opcional), `fase_nova` (opcional), `status_anterior` (opcional), `status_novo` (opcional), `observacao` (opcional), `created_at` |

### Atividades

| Tabela | Campos |
|---|---|
| `activities` | `id` (PK), `user_id`, `tenant_id`, `title`, `description`, `status`, `status_entered_at` (opcional), `priority`, `due_date` (opcional), `created_at`, `updated_at`; índices por usuário, status e usuário+status |
| `activity_status_history` | `id` (PK), `activity_id`, `user_id`, `tenant_id`, `from_status` (opcional), `to_status`, `moved_at`; índice composto por tenant, usuário, atividade e data |
| `activity_columns` | PK composta (`user_id`, `id`), `tenant_id`, `title`, `color`, `position`, `created_at`, `updated_at`; índice por tenant+usuário+posição |

### Repositórios e análise documental

| Tabela | Campos |
|---|---|
| `repositorios` | `id` (PK), `tenant_id`, `user_id`, `nome`, `tipo` (enum), `status` (enum), `url` (opcional), `caminho_local` (opcional), `gdrive_folder_id` (opcional), `descricao` (opcional), `metadados` (opcional), `created_at`, `updated_at` |
| `arquivos` | `id` (PK), `tenant_id`, `repositorio_id`, `nome`, `caminho`, `tipo_mime` (opcional), `tamanho_bytes`, `hash_arquivo` (opcional), `metadados` (opcional), `created_at`, `updated_at` |
| `analise_documentos_conversas` | `id` (PK), `tenant_id`, `user_id`, `titulo`, `created_at`, `updated_at` |
| `analise_documentos_arquivos` | `id` (PK), `tenant_id`, `user_id`, `conversa_id`, `nome`, `extensao`, `tamanho_bytes`, `paginas` (opcional), `chunks_json`, `created_at` |
| `analise_documentos_mensagens` | `id` (PK), `tenant_id`, `user_id`, `conversa_id`, `role`, `content`, `created_at` |
| `drive_sources` | `id` (PK), `tenant_id`, `agente_id` (opcional), `pasta_id`, `nome_pasta`, `service_account`, `ultima_sync` (opcional), `ativo`, `created_at`, `updated_at` |
| `indexacao_arquivos` | `id` (PK), `tenant_id`, `source_id`, `arquivo_id`, `nome`, `tipo`, `palavras_chave` (opcional), `conteudo` (opcional), `tamanho_bytes` (opcional), `url` (opcional), `indexado_em`, `updated_at` |

### Configuração e IA

| Tabela | Campos |
|---|---|
| `cfg_geral` | PK `tenant_id`; `user_id`, `escritorio_id` (opcional), `nome_plataforma`, `url_base`, `email_suporte`, `descricao` (opcional), `fuso_horario`, `idioma`, `modo_manutencao`, `updated_at` |
| `cfg_cdn` | PK `tenant_id`; `user_id`, `escritorio_id` (opcional), `provider`, `bucket`, `region`, `access_key_id`, `secret_access_key`, `cdn_url`, `tamanho_max_mb`, `tipos_permitidos`, `retencao_arquivo`, `retencao_delete`, `updated_at` |
| `cfg_database` | PK `tenant_id`; `user_id`, `escritorio_id` (opcional), `tipo`, `connection_string`, `pool_size`, `timeout_segundos`, `ssl_enabled`, `query_logging`, `read_replicas`, `backup_frequencia`, `backup_retencao`, `updated_at` |
| `cfg_ia` | PK `tenant_id`; `user_id`, `escritorio_id` (opcional), `provider`, `api_key`, `modelo`, `max_tokens`, `system_prompt`, `ativo`, `updated_at` |
| `cfg_ia_providers` | PK composta (`tenant_id`, `provider`); `user_id`, `api_key`, `endpoint_url`, `modelo`, `max_tokens`, `system_prompt`, `ativo`, `updated_at` |
| `cfg_usuarios` | PK `tenant_id`; `user_id`, `escritorio_id` (opcional), `max_tentativas_login`, `bloqueio_minutos`, `senha_min_chars`, `senha_maiusculas`, `senha_numeros`, `senha_especiais`, `senha_expiracao_dias`, `sessao_inativa_min`, `registro_modo`, `updated_at` |
| `cfg_seguranca` | PK `tenant_id`; `user_id`, `escritorio_id` (opcional), `twofa_obrigatorio`, `oauth_google`, `oauth_microsoft`, `jwt_expiracao_horas`, `log_acoes`, `log_documentos`, `alerta_suspeito`, `ips_bloqueados`, `lgpd_consentimento`, `lgpd_esquecimento`, `lgpd_exportacao`, `updated_at` |
| `cfg_notificacoes` | PK `tenant_id`; `user_id`, `escritorio_id` (opcional), `email_provider`, `email_region`, `email_access_key`, `email_secret_key`, `email_remetente`, `notif_prazos`, `notif_honorarios`, `notif_documentos`, `notif_relatorio`, `notif_push`, `notif_sms`, `updated_at` |
| `agentes_ia` | `id` (PK), `tenant_id`, `owner_user_id` (opcional), `created_by` (opcional), `escritorio_id` (opcional), `nome`, `descricao` (opcional), `provider`, `api_key` (opcional), `modelo`, `max_tokens`, `system_prompt` (opcional), `ativo`, `publico`, `created_at`, `updated_at` |
| `ia_politicas_planos` | PK composta (`tenant_id`, `plan_key`); `can_create_agents`, `allowed_roles`, `max_agents`, `allowed_models`, `allowed_menus`, `monthly_token_limit`, `fallback_provider` (opcional), `fallback_model` (opcional), `updated_at` |
| `ia_politicas_usuarios` | PK composta (`tenant_id`, `user_id`); `can_create_agents`, `max_agents`, `allowed_models`, `allowed_menus`, `monthly_token_limit` (opcionais), `updated_at` |
| `ia_uso_tokens` | PK composta (`tenant_id`, `user_id`, `period`); `tokens_used`, `updated_at` |

## Sugestões de normalização dos nomes

Recomenda-se adotar **inglês em `snake_case`**, seguindo a convenção já predominante nos campos técnicos, e nomes consistentes por conceito. Outra opção válida seria português integral; o ganho principal vem de escolher uma convenção e aplicá-la uniformemente. A tabela abaixo sugere o destino para as principais divergências:

| Uso atual | Nome recomendado | Observação |
|---|---|---|
| `nome`, `titulo`, `label` | `name`, `title`, `label` | Preservar distinções semânticas; não transformar todos em um único nome genérico. |
| `descricao`, `observacoes` | `description`, `notes` | `notes` descreve texto livre de observação. |
| `tipo`, `role` (campo categórico) | `type`, `role` | Em cada tabela, explicitar o domínio se necessário, como `document_type`. |
| `ativo`, `publico` | `is_active`, `is_public` | Prefixo booleano uniforme; revisar também `retencao_arquivo` e `retencao_delete`. |
| `tamanho_bytes` | `size_bytes` | Unidade no nome; aplicar em arquivos e documentos. |
| `data_vencimento`, `data_pagamento` | `due_date`, `paid_at` ou `payment_date` | Usar `_at` para instante; `_date` para data civil sem horário. Escolher pelo tipo real. |
| `data_conclusao` | `completed_at` | Se guardar só dia, usar `completion_date`. |
| `ultima_sync`, `indexado_em` | `last_synced_at`, `indexed_at` | Padronizar instante como sufixo `_at`. |
| `fase_atual` | `current_phase` ou `current_phase_number` | Clarificar se é identificador, índice ou posição. |
| `valor_centavos` | `amount_cents` | Nome em inglês e unidade monetária explícita. |
| `cpf_cnpj` | `tax_id` (ou manter sigla local documentada) | Nome genérico funciona se a coluna aceitar CPF e CNPJ; definir validação/formato. |
| `advogado_id`, `escritorio_id`, `processo_id`, `cliente_id` | `lawyer_id`, `office_id`, `case_id`, `client_id` | Uma decisão de idioma precisa abranger tabelas, FKs e APIs em conjunto. |
| `modelo`, `provider`, `api_key` | `model`, `provider`, `api_key` | Já há `model` e `modelo` em tabelas relacionadas. |
| `metadados`, `palavras_chave`, `conteudo` | `metadata`, `keywords`, `content` | Definir também formato estruturado para JSON/listas. |
| `senha_hash` | `password_hash` | Expressar que se trata de hash, não senha em texto. |
| `twofa_obrigatorio` | `two_factor_required` | Evitar abreviações locais em campos persistidos. |
| `notif_*` | `notify_*` ou preferencialmente nomes de configuração explícitos | Por exemplo, `notify_deadlines`; manter o padrão entre todos os canais. |
| `max_tentativas_login`, `timeout_segundos` | `max_login_attempts`, `timeout_seconds` | Unidade e idioma previsíveis. |

### Regras sugeridas para novos campos

1. Nomes de tabela no plural, em `snake_case`; nomes de campo em `snake_case` e inglês.
2. Chaves primárias `id`; chaves estrangeiras `<entidade>_id` usando o mesmo vocabulário em todos os serviços.
3. Auditoria: `created_at`, `updated_at`, `deleted_at` (se houver exclusão lógica), sempre com tipo temporal apropriado.
4. Instantes terminam em `_at`; datas civis terminam em `_date`. Evitar datas armazenadas como texto.
5. Booleanos começam com `is_`, `has_`, `can_` ou `should_`, conforme significado.
6. Quantidades/unidades aparecem no nome (`size_bytes`, `amount_cents`, `timeout_seconds`).
7. Evitar abreviações (`cfg`, `notif`, `sessao_inativa_min`) em novas estruturas; expandi-las (`configuration`, `notification`, `inactive_session_minutes`).
8. Enums devem usar valores e nomes de coluna documentados; não armazenar listas em texto delimitado.

## Observações de normalização relacional

Estas observações tratam da organização dos dados, além da grafia dos campos:

- **Configurações por tenant:** tabelas `cfg_*` repetem `user_id` e `escritorio_id`, mas sua PK é só `tenant_id`. Confirmar se cada configuração é realmente única por tenant; se configurações puderem ser por usuário/escritório, a chave e as regras de unicidade não refletem esse escopo.
- **Campos de lista/JSON em texto:** `allowed_roles`, `allowed_models`, `allowed_menus`, `ips_bloqueados`, `tipos_permitidos`, `metadados`, `chunks_json` e `palavras_chave` podem conter múltiplos valores. Para valores consultáveis/relacionáveis, considerar tabelas filhas de associação; manter JSON quando o conteúdo for documento flexível e não exigir joins/constraints.
- **Dados de cobrança no tenant:** o conjunto `billing_*` é um grupo coerente e pode ser movido para uma tabela `tenant_billing_profiles` se tiver ciclo de vida, histórico ou múltiplos endereços independentes. Se for um único perfil mutável, colunas na tabela atual podem ser adequadas.
- **Estado duplicado de fases:** `processos.fase_atual`/`cobrancas.fase_atual` coexistem com tabela de fases/histórico. Definir uma fonte canônica e regras transacionais para impedir divergência.
- **Relações não declaradas como FK:** vários campos terminados em `_id` não possuem `ForeignKey` explícita nos modelos, como `tenant_id`, `user_id`, `processo_id` e `cliente_id` em muitos serviços. Validar dependências entre serviços e, quando compartilham o mesmo banco, aplicar FKs/índices conforme estratégia de exclusão e tenancy.
- **Chaves de escopo:** avaliar unicidade composta com `tenant_id` para `slug`, `codigo`, número do processo e identificadores externos, conforme regra de negócio. `codigo` em `escritorios` e unicidades de usuário atualmente podem ser globais nos modelos.
- **Campos de status:** valores livres em `String` (`status`, `priority`, `event`) podem receber valores inconsistentes. Aplicar enum/check constraint ou tabela de domínio, conforme frequência de mudança e compatibilidade entre serviços.
- **Segredos em tabelas de configuração:** credenciais aparecem como colunas (`api_key`, `secret_access_key`, `connection_string`, `service_account`). Preferir referência a cofre de segredos ou armazenamento cifrado com gestão de chaves; nunca documentar ou exportar valores reais.

## Divergências e pontos para validar

- `usuarios` e `escritorios` são modelados em mais de um serviço. Em `svc-usuarios`, `usuarios` inclui `oab`; o modelo em `svc-auth` não inclui esse campo. Os modelos repetem tabelas compartilhadas em bases declarativas diferentes; confirmar o esquema de produção e escolher uma definição canônica.
- `clientes` também aparece no serviço de processos e no de clientes, com diferenças pequenas de tipo/default e comentário. Unificar contrato de coluna entre serviços.
- `asaas_webhook_events` aparece tanto em `svc-auth` quanto em `svc-cobrancas`; manter uma definição de propriedade clara.
- `honorarios.data_vencimento` e campos de data equivalentes usam `String(10)`, enquanto `cobrancas.data_vencimento` usa `DateTime`. `prazos.data_vencimento` também é texto. Migrar para `Date` ou `DateTime` conforme semântica.
- `next_due_date` em `tenants` é `String(10)`, apesar de representar uma data; avaliar tipo temporal.
- `cfg_cdn.tipos_permitidos`, políticas de IA e `ips_bloqueados` armazenam coleções como texto. Determinar se são JSON válido, texto separado por vírgulas ou formato legado.
- Defaults variam entre definidos na aplicação e no servidor; modelos sem `server_default` podem gerar tabelas divergentes se criadas por outra ferramenta.
- Algumas tabelas de migração podem não estar representadas nos modelos carregados; comparar este inventário com `migrations/` e com o banco ativo antes de usá-lo como DDL oficial.

## Plano de adoção recomendado

1. Escolher formalmente o idioma padrão (recomendado aqui: inglês técnico em `snake_case`) e publicar glossário de domínio (`processo` → `case`, `escritório` → `office`, etc.).
2. Gerar inventário do banco ativo e comparar com modelos/migrações, incluindo tipo, nullability, defaults, índices e constraints.
3. Priorizar padronização de tipos temporais, FKs e duplicação de modelos; são mudanças com impacto funcional maior que renomear.
4. Para renomeações, criar migrações compatíveis em etapas: adicionar coluna nova, sincronizar escrita/leitura durante transição, backfill, migrar consumidores e só então remover coluna antiga. Considerar APIs, relatórios, integrações e dados históricos.
5. Atualizar modelos, consultas, schemas de API, documentação e testes de contrato em conjunto; monitorar consultas e erros após cada lote.

Este documento é um guia de análise. Ele não propõe renomear colunas diretamente nem substitui migrações revisadas contra os dados reais.
