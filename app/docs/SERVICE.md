# app — API central Kealex

## Responsabilidade

Backend FastAPI central do hub Kealex. O módulo atual agrega endpoints usados por vários domínios, como autenticação e assinatura, processos, clientes, documentos, financeiro, prazos, audiências, intimações, atividades, configurações e recursos de IA.

## Camadas

- API: `app/api/routes/`, `app/api/schemas/` e `app/api/dependencies.py`.
- Casos de uso e presenters: `app/application/use_cases/`.
- Modelos de persistência: `app/infrastructure/database/models.py`.
- Banco e inicialização: `app/infrastructure/database/session.py` e `initialize.py`.
- Segurança: `app/infrastructure/security/`.
- Configuração: `app/core/config.py`.
- `app/legacy_context.py` ainda reúne helpers compartilhados legados usados pelos routers; novas regras devem ir para sua camada correspondente.

O banco MySQL é compartilhado com os microserviços `svc-*`. Os modelos representam tabelas já utilizadas pelo sistema; alterações no schema precisam ser avaliadas junto aos consumidores e aplicadas por migração versionada.

## Componentes

- `app/main.py`: composição FastAPI, CORS e registro de routers.
- `app/api/routes/`: routers separados por domínio.
- `app/api/schemas/schemas.py`: contratos Pydantic existentes.
- `app/infrastructure/database/models.py`: enums e modelos SQLAlchemy.
- `app/infrastructure/security/jwt_provider.py`: emissão e verificação de JWT.
- `app/api/dependencies.py`: autorização administrativa.
- Integrações: Asaas, provedores de IA e APIs externas para modelos.

## Rotas

Os principais grupos de rotas estão em `app/api/routes/`:

- `/auth/*` e `/k1/lex/auth/*`
- `/k1/lex/processos*`, `/k1/lex/clientes*`, `/k1/lex/documentos*`
- `/k1/lex/financeiro*`, `/k1/lex/prazos*`, `/k1/lex/cobrancas*`
- `/k1/lex/audiencias*`, `/k1/lex/intimacoes*`, `/k1/lex/activities*`
- `/k1/lex/configuracoes/*`, `/k1/lex/ia/*`, `/k1/lex/agentes*`
- `/health`, `/k1/lex/health` e `/debug/db-status`

Os 102 handlers extraídos mantêm os decorators e aliases originais, incluindo caminhos sem prefixo e `/v1/lex/*`. Consulte os decorators para métodos e status HTTP exatos.

## Carteira KeaCredits

- `GET /k1/lex/kea-store/carteira`: saldo de KeaCredits da organização autenticada (`saldoKeaCredits`).
- `GET /k1/lex/kea-store/pacotes`: pacotes disponíveis e preço em centavos.
- `POST /k1/lex/kea-store/recargas` com `Idempotency-Key` e `{ "packageId": "essencial|escritorio|pro" }`: cria uma cobrança PIX avulsa no Asaas e retorna QR Code/copia e cola.
- `GET /k1/lex/kea-store/recargas/{id}`: consulta situação da recarga e o saldo atualizado.
- O saldo só é creditado ao receber `PAYMENT_RECEIVED` no webhook Asaas existente (`/k1/lex/auth/asaas-webhook`). Configure também os eventos de recebimento, estorno, vencimento e exclusão de cobrança.
- Execute `migrations/create_kea_credits.sql` antes de publicar o backend; `create_all()` não altera bancos já existentes.
- Pacotes iniciais: 100 KeaCredits por R$ 10, 300 por R$ 30 e 600 por R$ 60. Ajuste esses valores no caso de uso e na interface antes de qualquer alteração comercial.
- A consulta CND oficial reserva 10 créditos antes da chamada ao Conecta; o lançamento é confirmado quando a API responde. Falha de conexão devolve a reserva. Emissores via portal manual não debitam créditos.

## Integração FiscalAPI

A integração FiscalAPI roda em svc-integracoes, publicada pelo gateway na rota /api/v1/certidoes. Habilite FISCALAPI_ENABLED=true e configure FISCALAPI_API_KEY no ambiente desse serviço. FISCALAPI_BASE_URL deve permanecer em HTTPS no host oficial api.fiscalapi.com.br; FISCALAPI_TIMEOUT aceita segundos de 1 a 120 (padrão 75). A API key nunca é retornada ao cliente nem escrita em logs.

Todas as rotas exigem JWT, role autorizada e tenant autenticado. Cada POST também exige `Idempotency-Key`; reutilizar a chave com o mesmo corpo devolve a consulta armazenada, e reutilizá-la com outro corpo retorna 409 para evitar cobrança duplicada.

- `POST /api/v1/certidoes/consulta-ie`: `{ "uf": "SP", "cnpj": "11222333000181" }`; informe exatamente um entre `cpf`, `cnpj` e `ie`. A rota externa documentada é `GET /api/consultar`, com uma UF por chamada e suporte às 27 UFs.
- `POST /api/v1/certidoes/enriquecimento`: `{ "tipo": "cnpj", "cnpj": "11222333000181", "force_fresh": false }` ou `tipo: "simples_nacional"`. São expostas somente as duas modalidades documentadas nesta integração.
- `POST /api/v1/certidoes/cnd-estadual`: `{ "uf": "SP", "cnpj": "11222333000181" }` ou CPF; a API oficial exige CPF ou CNPJ e UF.
- `POST /api/v1/certidoes/federais`: `tipo` aceita `cndt`, `crf_fgts` e `cnd_federal`. A documentação oficial confirma a rota RFB/PGFN individual por CNPJ; `emitir_nova` só é enviado para esse tipo.
- `POST /api/v1/certidoes/sigef`: informe exatamente um `cpf` ou `cnpj` do detentor.
- `GET /api/v1/certidoes/consultas/{id}` e `GET /api/v1/certidoes/consultas/{id}/documento`: consulta e baixa de resultado/PDF do próprio usuário e tenant.

As respostas POST seguem `{ success, data, metadata, error }`. A área `data` preserva os campos da FiscalAPI úteis ao serviço; JSON de resultado e resposta original sem PDF são cifrados em repouso e guardados para auditoria. PDFs também são cifrados e baixados somente pela rota autenticada. Identificadores de entrada são armazenados apenas mascarados e com hash HMAC. A operação, usuário, tenant, fornecedor, status, identificador externo, horário e custo conhecido (nullable) ficam registrados. Nenhum custo é assumido nem debitado em KeaCredits.

Execute `migrations/create_fiscalapi_consultas.sql` uma vez nos bancos existentes antes de publicar o backend. HTTP 404 é apresentado como registro não encontrado; credenciais/limite da conta do fornecedor viram erro 503 sanitizado, 429 preserva `Retry-After`, timeout retorna 504 e falha temporária do fornecedor retorna 503. Resultados 200 com `source_status` de erro ficam salvos como `FALHA_FONTE` sem repetir a consulta.

## Arquitetura desejada para alterações futuras

- API: `app/api/routes/`, `app/api/schemas/` e `app/api/dependencies.py`.
- Casos de uso: `app/application/use_cases/` e portas em `app/application/ports/`.
- Entidades e regras: `app/domain/`.
- SQLAlchemy e integrações: `app/infrastructure/`.
- Configuração compartilhada: `app/core/`.

Novas extrações devem preservar métodos, caminhos, aliases, autenticação, schemas, respostas, tabelas e inicialização. Migre gradualmente os helpers de `legacy_context.py` para casos de uso, dependências e infraestrutura.

## Dependências

As versões estão em `../requirements.txt` (arquivo `requirements.txt` na raiz do repositório). Entre as principais estão FastAPI, Pydantic, SQLAlchemy, PyMySQL, python-jose, bcrypt, cryptography e clientes Google.

## Testes

Os testes do backend central ficam atualmente em arquivos `test_*.py` na raiz do repositório. Há testes de processos, intimações e chaves públicas. Preserve-os e acrescente cobertura direcionada às rotas e regras extraídas.

## Execução

O Dockerfile da raiz copia o pacote `app/` e inicia `uvicorn app.main:app --host 0.0.0.0 --port 8000`. Instale as dependências do `requirements.txt` na raiz antes da execução local.
