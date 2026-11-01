# Base de conhecimento — svc-cobrancas

## Contexto do domínio

Uma cobrança pertence a um tenant e referencia processo e cliente. Seu valor é representado por `valor_centavos`. O campo `fase_atual` percorre os rótulos Pendente, Aguardando Pagamento, Vencida, Em Cobrança e Pago. O `status` guarda o estado operacional (`pendente`, `aguardando_pagamento`, `vencida`, `pago` ou `cancelado`).

## Fluxos existentes

1. Criar cobrança e registrar a ação inicial no histórico.
2. Iniciar pagamento PIX ou cartão no Asaas usando o cliente já cadastrado no gateway.
3. Avançar fase, marcar pagamento ou cancelar, sempre registrando o histórico.
4. Consultar cobranças e timeline por tenant autenticado.
5. Receber webhook autenticado do Asaas, ignorando eventos duplicados e atualizando cobrança quando o evento é mapeado.

## Contratos de compatibilidade

As operações são servidas pelos prefixos `/k1/lex/cobrancas`, `/v1/lex/cobrancas` e pelos aliases curtos iniciados em `/cobrancas`. O health check é `GET /health`. Preserve métodos HTTP, nomes JSON camelCase da API e respostas atuais ao alterar os handlers.

## Configuração

Banco: `KEALEX_DATABASE_URL` ou `KEALEX_DB_HOST`, `KEALEX_DB_NAME`, `KEALEX_DB_USER`, `KEALEX_DB_PASSWORD` e opcionalmente `KEALEX_DB_PORT`.

Segurança e gateway: `KEALEX_SECRET_KEY` (ou `KEALEX_JWT_SECRET`), `KEALEX_ASAAS_API_KEY`, `KEALEX_ASAAS_BASE_URL` e `KEALEX_ASAAS_WEBHOOK_TOKEN`.

## Desenvolvimento

Use Python 3.11 para corresponder à imagem Docker do serviço. Instale `requirements.txt`, configure as variáveis necessárias e rode `python -m unittest discover -s tests -v`. Para build, execute `docker build -t svc-cobrancas .` no diretório do microserviço.
