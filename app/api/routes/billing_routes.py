import httpx

from fastapi import APIRouter

from app.legacy_context import (
    ASAAS_BASE,
    Cobranca,
    Depends,
    HTTPException,
    HistoricoCobranca,
    KEALEX_ASAAS_API_KEY,
    PagamentoIn,
    Session,
    _cobranca_to_dict,
    _digits,
    datetime,
    get_db,
    uuid,
    verify_token,
)

router = APIRouter()


@router.get("/v1/lex/cobrancas")
@router.get("/k1/lex/cobrancas")
def list_cobrancas(db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    cobrancas = db.query(Cobranca).filter_by(tenant_id=tenant_id).order_by(Cobranca.created_at.desc()).all()
    return [_cobranca_to_dict(c) for c in cobrancas]


@router.post("/v1/lex/cobrancas", status_code=201)
@router.post("/k1/lex/cobrancas", status_code=201)
def create_cobranca(body: dict, db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    c = Cobranca(
        id=str(uuid.uuid4()), tenant_id=tenant_id, user_id=payload["sub"],
        processo_id=body.get("processoId"), cliente_id=body.get("clienteId"),
        valor_centavos=body.get("valorCentavos"), status="pendente", fase_atual=0,
        data_vencimento=datetime.fromisoformat(body["dataVencimento"]) if body.get("dataVencimento") else None,
    )
    db.add(c)
    db.flush()
    db.add(HistoricoCobranca(id=str(uuid.uuid4()), cobranca_id=c.id, acao="criada", status_novo="pendente", observacao="Cobrança criada"))
    db.commit()
    db.refresh(c)
    return _cobranca_to_dict(c)


@router.post("/v1/lex/cobrancas/get")
@router.post("/k1/lex/cobrancas/get")
def get_cobranca(body: dict, db: Session = Depends(get_db), payload=Depends(verify_token)):
    c = db.query(Cobranca).filter_by(id=body.get("id"), tenant_id=payload.get("tenant_id")).first()
    if not c: raise HTTPException(404, "Cobrança não encontrada")
    return _cobranca_to_dict(c)


@router.post("/v1/lex/cobrancas/proxima-fase")
@router.post("/k1/lex/cobrancas/proxima-fase")
def cobranca_proxima_fase(body: dict, db: Session = Depends(get_db), payload=Depends(verify_token)):
    c = db.query(Cobranca).filter_by(id=body.get("id"), tenant_id=payload.get("tenant_id")).first()
    if not c: raise HTTPException(404, "Cobrança não encontrada")
    if c.status in ("pago", "cancelado"): raise HTTPException(400, f"Status {c.status} não permite avançar fase")
    fases_labels = ["Pendente", "Aguardando Pagamento", "Vencida", "Em Cobrança", "Pago"]
    fase_ant = c.fase_atual
    c.fase_atual = min(c.fase_atual + 1, len(fases_labels) - 1)
    c.updated_at = datetime.utcnow()
    db.add(HistoricoCobranca(id=str(uuid.uuid4()), cobranca_id=c.id, acao="fase_avancada",
        fase_anterior=fase_ant, fase_nova=c.fase_atual,
        observacao=f"Avançado de {fases_labels[fase_ant]} para {fases_labels[c.fase_atual]}"))
    db.commit()
    return _cobranca_to_dict(c)


@router.post("/v1/lex/cobrancas/marcar-pago")
@router.post("/k1/lex/cobrancas/marcar-pago")
def cobranca_marcar_pago(body: dict, db: Session = Depends(get_db), payload=Depends(verify_token)):
    c = db.query(Cobranca).filter_by(id=body.get("id"), tenant_id=payload.get("tenant_id")).first()
    if not c: raise HTTPException(404, "Cobrança não encontrada")
    if c.status == "cancelado": raise HTTPException(400, "Cobrança cancelada não pode ser paga")
    status_ant = c.status
    c.status, c.fase_atual, c.data_pagamento, c.updated_at = "pago", 4, datetime.utcnow(), datetime.utcnow()
    db.add(HistoricoCobranca(id=str(uuid.uuid4()), cobranca_id=c.id, acao="marcado_pago",
        status_anterior=status_ant, status_novo="pago", observacao=body.get("observacao", "Marcado como pago")))
    db.commit()
    return _cobranca_to_dict(c)


@router.post("/v1/lex/cobrancas/cancelar")
@router.post("/k1/lex/cobrancas/cancelar")
def cobranca_cancelar(body: dict, db: Session = Depends(get_db), payload=Depends(verify_token)):
    c = db.query(Cobranca).filter_by(id=body.get("id"), tenant_id=payload.get("tenant_id")).first()
    if not c: raise HTTPException(404, "Cobrança não encontrada")
    if c.status == "pago": raise HTTPException(400, "Cobrança paga não pode ser cancelada")
    status_ant = c.status
    motivo = body.get("motivo", "Cancelado pelo usuário")
    c.status, c.motivo_cancelamento, c.updated_at = "cancelado", motivo, datetime.utcnow()
    db.add(HistoricoCobranca(id=str(uuid.uuid4()), cobranca_id=c.id, acao="cancelada",
        status_anterior=status_ant, status_novo="cancelado", observacao=motivo))
    db.commit()
    return _cobranca_to_dict(c)


@router.post("/v1/lex/cobrancas/timeline")
@router.post("/k1/lex/cobrancas/timeline")
def cobranca_timeline(body: dict, db: Session = Depends(get_db), payload=Depends(verify_token)):
    c = db.query(Cobranca).filter_by(id=body.get("id"), tenant_id=payload.get("tenant_id")).first()
    if not c: raise HTTPException(404, "Cobrança não encontrada")
    historico = db.query(HistoricoCobranca).filter_by(cobranca_id=c.id).order_by(HistoricoCobranca.created_at).all()
    fases = [{"ordem": i, "label": l, "descricao": d} for i, (l, d) in enumerate([
        ("Pendente", "Aguardando processamento"),
        ("Aguardando Pagamento", "Aguardando confirmação"),
        ("Vencida", "Prazo de pagamento vencido"),
        ("Em Cobrança", "Cobrança ativa em andamento"),
        ("Pago", "Pagamento recebido com sucesso"),
    ])]
    proximas_acoes = []
    if c.status not in ("pago", "cancelado"):
        proximas_acoes = [
            {"acao": "proxima_fase", "label": "Próxima Fase", "descricao": "Avançar fase de cobrança"},
            {"acao": "marcar_pago", "label": "Marcar como Pago", "descricao": "Registrar pagamento"},
            {"acao": "cancelar", "label": "Cancelar", "descricao": "Cancelar cobrança"},
        ]
    return {
        "cobranca_id": c.id, "status_atual": c.status, "fase_atual": c.fase_atual,
        "valor_centavos": c.valor_centavos,
        "data_vencimento": c.data_vencimento.isoformat() if c.data_vencimento else None,
        "data_pagamento": c.data_pagamento.isoformat() if c.data_pagamento else None,
        "fases": fases,
        "timeline": [{
            "id": h.id, "acao": h.acao, "fase_anterior": h.fase_anterior, "fase_nova": h.fase_nova,
            "status_anterior": h.status_anterior, "status_novo": h.status_novo,
            "observacao": h.observacao, "data": h.created_at.isoformat()
        } for h in historico],
        "proximas_acoes": proximas_acoes,
    }


@router.post("/v1/lex/cobrancas/pagamento")
@router.post("/k1/lex/cobrancas/pagamento")
def criar_pagamento(body: PagamentoIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    if body.billingType not in ("CREDIT_CARD", "PIX"):
        raise HTTPException(400, "billingType invalido. Use 'CREDIT_CARD' ou 'PIX'")
    if body.billingType == "CREDIT_CARD" and not body.creditCardToken and not body.creditCard:
        raise HTTPException(400, "Informe creditCardToken ou creditCard para pagamento com cartao")
    if body.billingType == "CREDIT_CARD" and body.creditCard and not body.creditCardHolderInfo:
        raise HTTPException(400, "creditCardHolderInfo e obrigatorio quando creditCard e informado")
    if not KEALEX_ASAAS_API_KEY:
        raise HTTPException(500, "KEALEX_ASAAS_API_KEY nao configurada")

    tenant_id = payload.get("tenant_id")
    c = db.query(Cobranca).filter_by(id=body.cobrancaId, tenant_id=tenant_id).first()
    if not c:
        raise HTTPException(404, "Cobranca nao encontrada")
    if c.status in ("pago", "cancelado"):
        raise HTTPException(400, f"Cobranca com status '{c.status}' nao pode ser paga")

    due_date = c.data_vencimento.date().isoformat() if c.data_vencimento else datetime.utcnow().date().isoformat()
    payload_asaas = {
        "billingType": body.billingType,
        "customer": body.customer,
        "value": round(c.valor_centavos / 100, 2),
        "dueDate": due_date,
        "description": body.description or f"Cobranca {c.id}",
        "externalReference": c.id,
    }
    if body.billingType == "CREDIT_CARD":
        if body.creditCardToken:
            payload_asaas["creditCardToken"] = body.creditCardToken
        else:
            payload_asaas["creditCard"] = body.creditCard.model_dump()
            payload_asaas["creditCardHolderInfo"] = {
                **body.creditCardHolderInfo.model_dump(exclude_none=True),
                "cpfCnpj": _digits(body.creditCardHolderInfo.cpfCnpj),
                "phone": _digits(body.creditCardHolderInfo.phone),
                "mobilePhone": _digits(body.creditCardHolderInfo.mobilePhone),
            }
            payload_asaas["remoteIp"] = body.remoteIp

    try:
        resp = httpx.post(
            f"{ASAAS_BASE}/payments",
            json=payload_asaas,
            headers={"accept": "application/json", "content-type": "application/json",
                     "access_token": KEALEX_ASAAS_API_KEY, "User-Agent": "HubKealex/1.0.0"},
            timeout=15,
        )
    except httpx.RequestError as e:
        raise HTTPException(502, f"Erro ao conectar com gateway de pagamento: {str(e)}")

    if resp.status_code not in (200, 201):
        raise HTTPException(502, f"Asaas recusou: {resp.json().get('errors', resp.text)}")

    asaas_data = resp.json()
    status_ant = c.status
    c.status = "aguardando_pagamento"
    c.fase_atual = max(c.fase_atual, 1)
    c.updated_at = datetime.utcnow()
    db.add(HistoricoCobranca(
        id=str(uuid.uuid4()), cobranca_id=c.id, acao="pagamento_iniciado",
        status_anterior=status_ant, status_novo="aguardando_pagamento",
        observacao=f"billingType={body.billingType}, asaas_id={asaas_data.get('id')}",
    ))
    db.commit()
    return {
        "cobrancaId": c.id,
        "asaasId": asaas_data.get("id"),
        "billingType": asaas_data.get("billingType"),
        "status": asaas_data.get("status"),
        "value": asaas_data.get("value"),
        "dueDate": asaas_data.get("dueDate"),
        "invoiceUrl": asaas_data.get("invoiceUrl"),
        "pixQrCodeUrl": asaas_data.get("pixQrCodeUrl"),
        "bankSlipUrl": asaas_data.get("bankSlipUrl"),
    }
