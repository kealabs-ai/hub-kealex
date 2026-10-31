# Base de conhecimento — `svc-auth`

## 1. Visão geral

`svc-auth` é uma API FastAPI responsável por cadastro e autenticação de usuários, emissão e validação de JWT, associação de usuários a tenants e escritórios, controle do trial/acesso por assinatura e integração de cobrança com o Asaas. A aplicação está em `app/`; `main.py` na raiz mantém compatibilidade com o comando atual do container.

O serviço usa SQLAlchemy com MySQL/PyMySQL. O banco é compartilhado com os demais serviços: as tabelas não têm chaves estrangeiras declaradas no modelo deste serviço, então `tenant_id` e `escritorio_id` são vínculos lógicos importantes para filtrar dados.

## 2. Arquivos

| Arquivo | Finalidade |
|---|---|
| `app/main.py` | Criação da aplicação FastAPI, registro dos routers e health checks. |
| `app/api/routes/auth_routes.py` | Endpoints de cadastro, login, pré-cadastro e ativação legada. |
| `app/api/routes/user_routes.py` | Consulta da identidade autenticada. |
| `app/api/routes/billing_routes.py` | Endpoints de assinatura, faturamento e webhook Asaas. |
| `app/api/schemas/` | Schemas de entrada e resposta da API. |
| `app/api/dependencies.py` | Dependências HTTP para autenticação e validação de acesso do tenant. |
| `app/application/use_cases/` | Regras de acesso de tenant e concessão de período de assinatura. |
| `app/domain/exceptions.py` | Exceções de domínio para acesso negado. |
| `app/infrastructure/database/` | Sessões e modelos SQLAlchemy. |
| `app/infrastructure/security/` | Hash de senha e JWT. |
| `app/core/` | Configuração de ambiente e normalização. |
| `main.py` | Compatibilidade com `uvicorn main:app` usado pelo Docker. |
| `requirements.txt` | Dependências Python fixadas em versões específicas. |
| `Dockerfile` | Imagem Python 3.12, instalação de dependências e inicialização via Uvicorn na porta 8000. |
| `scripts/seed_users.py` | Script auxiliar para inserir usuários de teste. |
| `scripts/fix_hash.py` | Utilitário de manutenção de hash de senha. |
| `tests/` | Testes unitários e de integração. |

## 3. Inicialização e configuração

O módulo carrega `.env` com `python-dotenv`. Na inicialização da aplicação, `startup_event` chama `_init_db()`, que executa `Base.metadata.create_all()` e garante a existência do tenant `kealex` e do usuário administrador padrão. Falhas de conexão ou criação de tabelas impedem o serviço de iniciar.

Configurações lidas pelo serviço:

| Variável | Obrigatória | Uso |
|---|---:|---|
| `KEALEX_DB_HOST` | Alternativa | Host do MySQL; deve ser usado junto com `KEALEX_DB_NAME`, `KEALEX_DB_USER` e `KEALEX_DB_PASSWORD`. |
| `KEALEX_DB_NAME` | Alternativa | Nome do banco. |
| `KEALEX_DB_USER` | Alternativa | Usuário do banco. |
| `KEALEX_DB_PASSWORD` | Alternativa | Senha do banco. |
| `KEALEX_DB_PORT` | Não | Porta do MySQL, padrão `3306`. |
| `KEALEX_DATABASE_URL` | Alternativa | URL SQLAlchemy completa, usada se o conjunto de variáveis separadas não estiver completo. |
| `KEALEX_SECRET_KEY` | Sim | Segredo para assinar/verificar JWT; se ausente, usa `KEALEX_JWT_SECRET`. |
| `KEALEX_JWT_SECRET` | Alternativa | Nome legado/alternativo do segredo JWT. |
| `KEALEX_ASAAS_BASE_URL` | Sim | URL base da API Asaas (incluindo a versão `/v3`, quando aplicável). Validada durante a importação do módulo. |
| `KEALEX_ASAAS_API_KEY` | Para cobrança | Chave enviada ao Asaas no header `access_token`. O código declara valor vazio se não configurada, mas operações de cobrança não funcionarão corretamente. |
| `KEALEX_ASAAS_WEBHOOK_TOKEN` | Para webhook | Valor esperado no header `asaas-access-token`; webhook é rejeitado se não configurado. |

Não registrar valores de segredo, tokens ou dados de cobrança em logs. Configure valores fortes e diferentes por ambiente. A inicialização cria `admin@kealex.com` com senha `admin123` quando o usuário não existe; altere a credencial imediatamente e trate isso como comportamento de bootstrap a revisar antes de produção.

## 4. Modelo de domínio

- **Tenant** (`tenants`): organização/conta de cobrança e isolamento lógico. Guarda slug, plano, datas de trial, estado de assinatura, identificadores Asaas e perfil de faturamento.
- **Usuario** (`usuarios`): identidade autenticável, vinculada a `tenant_id`, opcionalmente a `escritorio_id`, com e-mail, hash bcrypt, papel e estado ativo.
- **Escritorio** (`escritorios`): escritório vinculado a um tenant, com código único e limite de advogados.
- **AsaasWebhookEvent** (`asaas_webhook_events`): IDs de eventos processados para deduplicação do webhook.

Papéis declarados: `admin`, `escritorio`, `advogado`, `juridico` e `cliente`. No cadastro público, os perfis aceitos são `advogado`, `escritorio`, `juridico` e `corporativo` (mapeado para o papel `juridico`).

## 5. Autenticação e autorização

- Senhas novas são armazenadas com bcrypt; comparação inválida ou hash corrompido resulta em falha de autenticação.
- JWT usa `HS256`, expira após 8 horas e contém `sub` (ID do usuário), `role`, `tenant_id`, `escritorio_id` e `exp`.
- Rotas protegidas recebem `Authorization: Bearer <accessToken>`. Token inválido/expirado gera HTTP 401.
- `verify_token` verifica assinatura e validade do JWT. `require_active_trial` também carrega o tenant e aplica a regra de acesso à plataforma.
- Usuário `admin` ignora a checagem de assinatura. Para demais papéis, tenant ausente/inativo, trial expirado ou assinatura não ativa gera HTTP 403 nas rotas que exigem acesso.
- Login não bloqueia contas cujo trial venceu: permite obter token para consultar/regularizar cobrança. Endpoints de cobrança usam `verify_token`, enquanto `/me` exige tenant com acesso liberado.

## 6. API

Prefixo funcional observado no código: `/k1/lex/auth`. Os nomes/formatos abaixo refletem as rotas em `app/api/routes/`; consulte os schemas em `app/api/schemas/` para os campos completos e obrigatórios.

| Método e rota | Autenticação | Finalidade |
|---|---|---|
| `POST /k1/lex/auth/register` | Pública | Cria tenant em trial e usuário; perfil escritório também cria registro de escritório. CPF/CNPJ é normalizado e validado por quantidade de dígitos. Retorna `AuthUser` com token. |
| `POST /k1/lex/auth/login` | Pública | Autentica e retorna dados do usuário, plano e token. Usuário inativo ou credenciais inválidas: 401. |
| `GET /k1/lex/auth/me` | Bearer + acesso ativo | Retorna claims e dados do escritório/modalidade do usuário. |
| `POST /k1/lex/auth/pre-register` | Pública | Cria usuário e tenant para o fluxo de assinatura e retorna token temporário de 2 horas. |
| `POST /k1/lex/auth/ativar` | Bearer | Endpoint legado desativado; retorna HTTP 410. O webhook é responsável por alterar entitlement. |
| Operações de assinatura com cartão | Bearer | Função `assinar`; cria/atualiza assinatura e cobrança no Asaas. |
| Operações de assinatura PIX | Bearer | Função `assinar_pix`; retorna dados do QR Code/copia e cola e vencimento. |
| `POST /k1/lex/auth/criar-cliente-asaas` | Bearer | Cria ou atualiza o customer Asaas associado ao tenant e persiste dados de faturamento. |
| `GET /k1/lex/auth/billing-profile` | Bearer | Retorna perfil de faturamento; pode completar dados consultando customer no Asaas. |
| `POST /k1/lex/auth/asaas-webhook` | Header `asaas-access-token` | Valida token do webhook, deduplica evento e atualiza status da assinatura. |
| `GET /k1/lex/auth/billing-status` | Bearer | Calcula status apresentado para trial/assinatura. |
| `POST /k1/lex/auth/assinatura/reativar` | Bearer | Consulta pagamentos no Asaas e reativa período quando pagamento estiver confirmado/recebido. |
| `GET /k1/lex/auth/assinatura` | Bearer | Retorna assinatura local e tenta completar detalhes/PIX via Asaas. |
| `GET /health` | Pública | Health check: `{"status":"healthy","service":"svc-auth"}`. |
| `GET /k1/lex/health` | Pública | Health check: `{"status":"ok","service":"svc-auth"}`. |

FastAPI também publica documentação OpenAPI nos caminhos padrão (`/docs`, `/openapi.json`), a menos que configuração externa os restrinja.

## 7. Trial, planos e webhook

- Trial padrão: 7 dias (`TRIAL_DAYS`). Cadastro inicia trial imediatamente.
- A criação do banco garante tenant inicial `kealex` e administrador padrão, se ausentes.
- O guard de acesso permite plano `trial` enquanto não expirado e planos `starter`, `professional` ou `enterprise` quando `subscription_status == active` e não expirados.
- `grant_subscription_period` evita conceder período repetido para o mesmo `payment_id`; ciclo trimestral concede 90 dias, os demais ciclos considerados concedem 30.
- Webhook exige header `asaas-access-token`, registra o ID do evento e ignora duplicatas. `PAYMENT_CONFIRMED`/`PAYMENT_RECEIVED` concedem período; `PAYMENT_OVERDUE` marca `past_due` e desativa tenant; `SUBSCRIPTION_DELETED` marca `canceled` e desativa tenant.
- O webhook registra eventos válidos sem assinatura associada como ignorados, evitando reprocessamento do mesmo evento.

## 8. Execução local e container

Instale as dependências de `requirements.txt` e defina as variáveis obrigatórias de banco, JWT e Asaas antes de iniciar. O comando do container é equivalente a:

```sh
uvicorn main:app --host 0.0.0.0 --port 8000
```

O `Dockerfile` usa Python 3.12 slim, expõe a porta 8000 e copia o conteúdo do diretório para `/app`. Em execução via Compose, verifique a seção do serviço `svc-auth` e o `.env` correspondente; o código precisa conseguir alcançar o banco e a API configurada do Asaas.

## 9. Dependências principais

FastAPI/Uvicorn (API), Pydantic EmailStr (validação), SQLAlchemy e PyMySQL (persistência), bcrypt (senhas), `python-jose` (JWT), `httpx` (Asaas) e `python-dotenv` (ambiente). As versões exatas estão em `requirements.txt`.

## 10. Cuidados operacionais e pontos de atenção

1. **Credencial bootstrap:** a senha padrão do administrador está escrita no código. Não exponha essa conta; substitua a senha e considere retirar/parametrizar o bootstrap em ambientes de produção.
2. **CORS:** a aplicação permite qualquer origem, método e header (`*`). Restringir origens conforme os domínios usados pelo frontend antes de uma implantação pública.
3. **Segredos:** `KEALEX_SECRET_KEY` assina tokens de todos os usuários. Rotacioná-la invalida tokens existentes; mantenha o valor fora do repositório.
4. **Escopo multi-tenant:** operações internas devem sempre filtrar por `tenant_id`; relacionamentos são em grande parte lógicos no modelo local.
5. **Provisionamento de schema:** `create_all()` cria tabelas ausentes, mas não substitui migrações para alterações em tabelas existentes.
6. **Script de seed:** `seed_users.py` insere contas de teste e tem formato de URL de banco próprio. Revise compatibilidade de colunas e `tenant_id` com o schema atual antes de executá-lo; não é parte do startup normal.
7. **Rotas pelo gateway:** confirme o roteamento do prefixo de autenticação na configuração de gateway do ambiente. O `api-gateway/nginx.conf` atualmente não tem um `location` explícito para `/k1/lex/auth`; a regra geral encaminha para `hubkealex`.
8. **Contrato de API:** respostas usam nomes camelCase em diversos campos, embora os modelos internos usem snake_case. Preserve o contrato consumido pelo frontend e pelos outros serviços.

## 11. Referências internas

- Implementação: [`../app/main.py`](../app/main.py)
- Dependências: [`../requirements.txt`](../requirements.txt)
- Container: [`../Dockerfile`](../Dockerfile)
- Seed de desenvolvimento: [`../scripts/seed_users.py`](../scripts/seed_users.py)
- Gateway: [`../../api-gateway/nginx.conf`](../../api-gateway/nginx.conf)

## 12. Testes locais e build Docker

Use Python 3.12 no ambiente local, alinhado ao `Dockerfile` e às versões fixadas das dependências. No PowerShell, a partir da raiz de `svc-auth`:

```powershell
py -3.12 -m venv .venv312
.\.venv312\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m unittest discover -s tests/unit -v
python -m unittest discover -s tests/integration -v
```

Para gerar a imagem Docker a partir da raiz de `svc-auth`:

```powershell
docker build -t svc-auth:teste .
docker image ls svc-auth
```
