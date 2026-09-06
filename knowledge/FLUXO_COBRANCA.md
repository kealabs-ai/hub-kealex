# INSTRUÇÕES PARA IMPLEMENTAR FLUXO DE COBRANÇA

## 1. ADICIONAR MODELOS (após a classe Fase, antes de Honorario)

```python
class Cobranca(Base):
    __tablename__ = "cobrancas"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False)
    user_id = Column(String(36), nullable=False)
    processo_id = Column(String(36), nullable=False)
    cliente_id = Column(String(36), nullable=False)
    valor_centavos = Column(Integer, nullable=False)
    status = Column(String(50), default="pendente")
    fase_atual = Column(Integer, default=0)
    data_vencimento = Column(DateTime, nullable=True)
    data_pagamento = Column(DateTime, nullable=True)
    motivo_cancelamento = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class HistoricoCobranca(Base):
    __tablename__ = "historico_cobrancas"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    cobranca_id = Column(String(36), nullable=False)
    acao = Column(String(100), nullable=False)
    fase_anterior = Column(Integer, nullable=True)
    fase_nova = Column(Integer, nullable=True)
    status_anterior = Column(String(50), nullable=True)
    status_novo = Column(String(50), nullable=True)
    observacao = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

## 2. ADICIONAR FUNÇÕES HELPER (antes dos endpoints de cobrança)

```python
def _get_proximas_acoes(cobranca):
    acoes = []
    if cobranca.status != "pago" and cobranca.status != "cancelado":
        acoes.append({"acao": "proxima_fase", "label": "Proxima Fase", "descricao": "Avancar para a proxima fase de cobranca"})
        acoes.append({"acao": "marcar_pago", "label": "Marcar como Pago", "descricao": "Registrar pagamento recebido"})
        acoes.append({"acao": "cancelar", "label": "Cancelar", "descricao": "Cancelar esta cobranca"})
    return acoes

def _cobranca_to_dict(cobranca, db=None):
    fases_cobranca = ["Pendente", "Aguardando Pagamento", "Vencida", "Em Cobranca", "Pago"]
    return {
        "id": cobranca.id,
        "tenantId": cobranca.tenant_id,
        "processoId": cobranca.processo_id,
        "clienteId": cobranca.cliente_id,
        "valorCentavos": cobranca.valor_centavos,
        "status": cobranca.status,
        "faseAtual": cobranca.fase_atual,
        "faseLabel": fases_cobranca[cobranca.fase_atual] if cobranca.fase_atual < len(fases_cobranca) else "Desconhecida",
        "dataVencimento": cobranca.data_vencimento.isoformat() if cobranca.data_vencimento else None,
        "dataPagamento": cobranca.data_pagamento.isoformat() if cobranca.data_pagamento else None,
        "motivoCancelamento": cobranca.motivo_cancelamento,
        "createdAt": cobranca.created_at.isoformat(),
        "updatedAt": cobranca.updated_at.isoformat()
    }
```

## 3. ENDPOINTS DISPONÍVEIS

### Criar Cobrança
POST /k1/lex/cobrancas
Body: {
  "processoId": "uuid",
  "clienteId": "uuid",
  "valorCentavos": 10000,
  "dataVencimento": "2024-12-31T23:59:59"
}

### Listar Cobrancas
GET /k1/lex/cobrancas

### Obter Cobrança
GET /k1/lex/cobrancas/{cobranca_id}

### Timeline da Cobrança
GET /k1/lex/cobrancas/{cobranca_id}/timeline

### Próxima Fase
POST /k1/lex/cobrancas/{cobranca_id}/proxima-fase

### Marcar como Pago
POST /k1/lex/cobrancas/{cobranca_id}/marcar-pago
Body: {
  "observacao": "Pagamento recebido em dinheiro"
}

### Cancelar Cobrança
POST /k1/lex/cobrancas/{cobranca_id}/cancelar
Body: {
  "motivo": "Cliente solicitou cancelamento"
}

## 4. FASES DE COBRANÇA

0. Pendente - Cobranca criada e aguardando processamento
1. Aguardando Pagamento - Aguardando confirmacao de pagamento
2. Vencida - Prazo de pagamento vencido
3. Em Cobranca - Em processo de cobranca ativa
4. Pago - Cobranca paga com sucesso

## 5. STATUS POSSÍVEIS

- pendente: Cobranca criada
- pago: Cobranca paga
- cancelado: Cobranca cancelada

## 6. TIMELINE

Cada ação registra um histórico com:
- acao: tipo de ação (criada, fase_avancada, marcado_pago, cancelada)
- fase_anterior/fase_nova: transição de fases
- status_anterior/status_novo: transição de status
- observacao: detalhes da ação
- data: timestamp da ação
