# Endpoints de Cobrança - Adicionar ao app/main.py após o endpoint debug_fases

@app.post("/k1/lex/cobrancas", status_code=201)
def criar_cobranca(body: dict, db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    processo_id = body.get("processoId")
    cliente_id = body.get("clienteId")
    valor_centavos = body.get("valorCentavos", 0)
    data_vencimento = body.get("dataVencimento")
    
    if not processo_id or not cliente_id or not valor_centavos:
        raise HTTPException(400, "processoId, clienteId e valorCentavos sao obrigatorios")
    
    p = db.query(Processo).filter_by(id=processo_id, tenant_id=tenant_id).first()
    if not p:
        raise HTTPException(404, "Processo nao encontrado")
    
    cobranca = Cobranca(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        user_id=payload["sub"],
        processo_id=processo_id,
        cliente_id=cliente_id,
        valor_centavos=valor_centavos,
        data_vencimento=datetime.fromisoformat(data_vencimento) if data_vencimento else None,
        status="pendente",
        fase_atual=0
    )
    db.add(cobranca)
    db.commit()
    db.refresh(cobranca)
    
    historico = HistoricoCobranca(
        id=str(uuid.uuid4()),
        cobranca_id=cobranca.id,
        acao="criada",
        status_novo="pendente",
        observacao="Cobranca criada"
    )
    db.add(historico)
    db.commit()
    
    return _cobranca_to_dict(cobranca)

@app.get("/k1/lex/cobrancas/{cobranca_id}")
def get_cobranca(cobranca_id: str, db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    cobranca = db.query(Cobranca).filter_by(id=cobranca_id, tenant_id=tenant_id).first()
    if not cobranca:
        raise HTTPException(404, "Cobranca nao encontrada")
    
    return _cobranca_to_dict(cobranca, db)

@app.get("/k1/lex/cobrancas")
def listar_cobrancas(db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    cobrancas = db.query(Cobranca).filter_by(tenant_id=tenant_id).order_by(Cobranca.created_at.desc()).all()
    return [_cobranca_to_dict(c, db) for c in cobrancas]

@app.post("/k1/lex/cobrancas/{cobranca_id}/proxima-fase")
def proxima_fase_cobranca(cobranca_id: str, db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    cobranca = db.query(Cobranca).filter_by(id=cobranca_id, tenant_id=tenant_id).first()
    if not cobranca:
        raise HTTPException(404, "Cobranca nao encontrado")
    
    if cobranca.status == "pago" or cobranca.status == "cancelado":
        raise HTTPException(400, f"Nao e possivel avancar fase de cobranca com status {cobranca.status}")
    
    fases_cobranca = [
        "Pendente",
        "Aguardando Pagamento",
        "Vencida",
        "Em Cobranca",
        "Pago"
    ]
    
    fase_anterior = cobranca.fase_atual
    nova_fase = min(cobranca.fase_atual + 1, len(fases_cobranca) - 1)
    
    cobranca.fase_atual = nova_fase
    cobranca.updated_at = datetime.utcnow()
    db.add(cobranca)
    
    historico = HistoricoCobranca(
        id=str(uuid.uuid4()),
        cobranca_id=cobranca.id,
        acao="fase_avancada",
        fase_anterior=fase_anterior,
        fase_nova=nova_fase,
        observacao=f"Avancado de {fases_cobranca[fase_anterior]} para {fases_cobranca[nova_fase]}"
    )
    db.add(historico)
    db.commit()
    
    return _cobranca_to_dict(cobranca, db)

@app.post("/k1/lex/cobrancas/{cobranca_id}/marcar-pago")
def marcar_pago(cobranca_id: str, body: dict = None, db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    cobranca = db.query(Cobranca).filter_by(id=cobranca_id, tenant_id=tenant_id).first()
    if not cobranca:
        raise HTTPException(404, "Cobranca nao encontrado")
    
    if cobranca.status == "cancelado":
        raise HTTPException(400, "Nao e possivel marcar como pago uma cobranca cancelada")
    
    status_anterior = cobranca.status
    cobranca.status = "pago"
    cobranca.fase_atual = 4
    cobranca.data_pagamento = datetime.utcnow()
    cobranca.updated_at = datetime.utcnow()
    db.add(cobranca)
    
    historico = HistoricoCobranca(
        id=str(uuid.uuid4()),
        cobranca_id=cobranca.id,
        acao="marcado_pago",
        status_anterior=status_anterior,
        status_novo="pago",
        observacao=body.get("observacao", "Marcado como pago") if body else "Marcado como pago"
    )
    db.add(historico)
    db.commit()
    
    return _cobranca_to_dict(cobranca, db)

@app.post("/k1/lex/cobrancas/{cobranca_id}/cancelar")
def cancelar_cobranca(cobranca_id: str, body: dict, db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    cobranca = db.query(Cobranca).filter_by(id=cobranca_id, tenant_id=tenant_id).first()
    if not cobranca:
        raise HTTPException(404, "Cobranca nao encontrado")
    
    if cobranca.status == "pago":
        raise HTTPException(400, "Nao e possivel cancelar uma cobranca ja paga")
    
    motivo = body.get("motivo", "Cancelado pelo usuario")
    status_anterior = cobranca.status
    
    cobranca.status = "cancelado"
    cobranca.motivo_cancelamento = motivo
    cobranca.updated_at = datetime.utcnow()
    db.add(cobranca)
    
    historico = HistoricoCobranca(
        id=str(uuid.uuid4()),
        cobranca_id=cobranca.id,
        acao="cancelada",
        status_anterior=status_anterior,
        status_novo="cancelado",
        observacao=motivo
    )
    db.add(historico)
    db.commit()
    
    return _cobranca_to_dict(cobranca, db)

@app.get("/k1/lex/cobrancas/{cobranca_id}/timeline")
def timeline_cobranca(cobranca_id: str, db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    cobranca = db.query(Cobranca).filter_by(id=cobranca_id, tenant_id=tenant_id).first()
    if not cobranca:
        raise HTTPException(404, "Cobranca nao encontrado")
    
    fases_cobranca = [
        {"ordem": 0, "label": "Pendente", "descricao": "Cobranca criada e aguardando processamento"},
        {"ordem": 1, "label": "Aguardando Pagamento", "descricao": "Aguardando confirmacao de pagamento"},
        {"ordem": 2, "label": "Vencida", "descricao": "Prazo de pagamento vencido"},
        {"ordem": 3, "label": "Em Cobranca", "descricao": "Em processo de cobranca ativa"},
        {"ordem": 4, "label": "Pago", "descricao": "Cobranca paga com sucesso"}
    ]
    
    historico = db.query(HistoricoCobranca).filter_by(cobranca_id=cobranca_id).order_by(HistoricoCobranca.created_at).all()
    
    timeline = []
    for h in historico:
        timeline.append({
            "id": h.id,
            "acao": h.acao,
            "fase_anterior": h.fase_anterior,
            "fase_nova": h.fase_nova,
            "status_anterior": h.status_anterior,
            "status_novo": h.status_novo,
            "observacao": h.observacao,
            "data": h.created_at.isoformat()
        })
    
    return {
        "cobranca_id": cobranca_id,
        "status_atual": cobranca.status,
        "fase_atual": cobranca.fase_atual,
        "valor_centavos": cobranca.valor_centavos,
        "data_vencimento": cobranca.data_vencimento.isoformat() if cobranca.data_vencimento else None,
        "data_pagamento": cobranca.data_pagamento.isoformat() if cobranca.data_pagamento else None,
        "fases": fases_cobranca,
        "timeline": timeline,
        "proximas_acoes": _get_proximas_acoes(cobranca)
    }

def _get_proximas_acoes(cobranca: Cobranca):
    acoes = []
    if cobranca.status != "pago" and cobranca.status != "cancelado":
        acoes.append({"acao": "proxima_fase", "label": "Proxima Fase", "descricao": "Avancar para a proxima fase de cobranca"})
        acoes.append({"acao": "marcar_pago", "label": "Marcar como Pago", "descricao": "Registrar pagamento recebido"})
        acoes.append({"acao": "cancelar", "label": "Cancelar", "descricao": "Cancelar esta cobranca"})
    return acoes

def _cobranca_to_dict(cobranca: Cobranca, db: Session = None):
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
