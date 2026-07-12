# svc-cobrancas - Microserviço de Cobrança

Microserviço FastAPI para gerenciar o fluxo completo de cobrança com timeline, fases e histórico.

## Endpoints

### Criar Cobrança
```
POST /k1/lex/cobrancas
Body: {
  "processoId": "uuid",
  "clienteId": "uuid",
  "valorCentavos": 10000,
  "dataVencimento": "2024-12-31T23:59:59"
}
Response: Cobranca object
```

### Listar Cobrancas
```
GET /k1/lex/cobrancas
Response: Array of Cobranca objects
```

### Obter Cobrança
```
POST /k1/lex/cobrancas/get
Body: {
  "id": "cobranca_id"
}
Response: Cobranca object
```

### Próxima Fase
```
POST /k1/lex/cobrancas/proxima-fase
Body: {
  "id": "cobranca_id"
}
Response: Cobranca object com fase avançada
```

### Marcar como Pago
```
POST /k1/lex/cobrancas/marcar-pago
Body: {
  "id": "cobranca_id",
  "observacao": "Pagamento recebido em dinheiro"
}
Response: Cobranca object com status "pago"
```

### Cancelar Cobrança
```
POST /k1/lex/cobrancas/cancelar
Body: {
  "id": "cobranca_id",
  "motivo": "Cliente solicitou cancelamento"
}
Response: Cobranca object com status "cancelado"
```

### Timeline da Cobrança
```
POST /k1/lex/cobrancas/timeline
Body: {
  "id": "cobranca_id"
}
Response: {
  "cobranca_id": "uuid",
  "status_atual": "pendente",
  "fase_atual": 0,
  "valor_centavos": 10000,
  "data_vencimento": "2024-12-31T23:59:59",
  "data_pagamento": null,
  "fases": [...],
  "timeline": [...],
  "proximas_acoes": [...]
}
```

## Fases de Cobrança

0. **Pendente** - Cobrança criada e aguardando processamento
1. **Aguardando Pagamento** - Aguardando confirmação de pagamento
2. **Vencida** - Prazo de pagamento vencido
3. **Em Cobrança** - Em processo de cobrança ativa
4. **Pago** - Cobrança paga com sucesso

## Status Possíveis

- `pendente` - Cobrança criada
- `pago` - Cobrança paga
- `cancelado` - Cobrança cancelada

## Estrutura de Resposta

```json
{
  "id": "uuid",
  "tenantId": "uuid",
  "processoId": "uuid",
  "clienteId": "uuid",
  "valorCentavos": 10000,
  "status": "pendente",
  "faseAtual": 0,
  "faseLabel": "Pendente",
  "dataVencimento": "2024-12-31T23:59:59",
  "dataPagamento": null,
  "motivoCancelamento": null,
  "createdAt": "2024-01-01T10:00:00",
  "updatedAt": "2024-01-01T10:00:00"
}
```

## Timeline

Cada ação registra um histórico com:
- `acao`: tipo de ação (criada, fase_avancada, marcado_pago, cancelada)
- `fase_anterior`/`fase_nova`: transição de fases
- `status_anterior`/`status_novo`: transição de status
- `observacao`: detalhes da ação
- `data`: timestamp da ação

## Próximas Ações

Retorna as ações disponíveis baseado no status atual:
- `proxima_fase` - Avançar para próxima fase
- `marcar_pago` - Registrar pagamento
- `cancelar` - Cancelar cobrança

## Variáveis de Ambiente

```
DATABASE_URL=mysql+pymysql://user:pass@host:3306/db
SECRET_KEY=sua_chave_secreta
```

## Build e Deploy

```bash
# Build da imagem
docker build -t svc-cobrancas .

# Executar localmente
docker run -p 8000:8000 \
  -e DATABASE_URL="mysql+pymysql://..." \
  -e SECRET_KEY="..." \
  svc-cobrancas
```

## Health Check

```
GET /health
Response: {"status": "healthy", "service": "svc-cobrancas"}
```
