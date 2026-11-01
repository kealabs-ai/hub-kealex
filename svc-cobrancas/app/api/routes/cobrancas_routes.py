import hmac
import json
import logging
import re
import uuid
from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.dependencies import auth_guard, verify_token
from app.application.use_cases.cobranca_support import (
    build_asaas_payload, get_next_actions, now_utc, serialize_charge,
)
from app.api.schemas.cobranca_schema import CobrancaIn, PagamentoIn
from app.core.config import ASAAS_API_KEY, ASAAS_BASE, ASAAS_WEBHOOK_TOKEN, PREFIX
from app.infrastructure.database.models.cobranca_model import AsaasWebhookEvent, Cobranca, HistoricoCobranca
from app.infrastructure.database.session import get_db

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/v1/lex/cobrancas", status_code=201)
@router.post("/k1/lex/cobrancas", status_code=201)
@router.post(PREFIX, status_code=201, include_in_schema=False)
def criar_cobranca(body: CobrancaIn, db: Session = Depends(get_db), payload=Depends(auth_guard)):
    try:
        safe_id = re.sub(r'[^a-zA-Z0-9\-]', '', body.processoId)
        logger.info(f"[CREATE_COBRANCA] Iniciando criacao de cobranca para processo: {safe_id}")
        tenant_id = payload.get("tenant_id")
        
        cobranca = Cobranca(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            user_id=payload["sub"],
            processo_id=body.processoId,
            cliente_id=body.clienteId,
            valor_centavos=body.valorCentavos,
            data_vencimento=datetime.fromisoformat(body.dataVencimento) if body.dataVencimento else None,
            status="pendente",
            fase_atual=0
        )
        db.add(cobranca)
        db.commit()
        db.refresh(cobranca)
        logger.info(f"[CREATE_COBRANCA] Cobranca criada: {cobranca.id}")
        
        historico = HistoricoCobranca(
            id=str(uuid.uuid4()),
            cobranca_id=cobranca.id,
            acao="criada",
            status_novo="pendente",
            observacao="Cobranca criada"
        )
        db.add(historico)
        db.commit()
        logger.info(f"[CREATE_COBRANCA] Historico registrado")
        
        return serialize_charge(cobranca)
    except Exception as e:
        logger.error(f"[CREATE_COBRANCA] ERRO: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(500, f"Erro ao criar cobranca: {str(e)}")

@router.post("/v1/lex/cobrancas/pagamento")
@router.post("/k1/lex/cobrancas/pagamento")
@router.post(f"{PREFIX}/pagamento", include_in_schema=False)
def criar_pagamento(body: PagamentoIn, db: Session = Depends(get_db), payload=Depends(auth_guard)):
    if body.billingType not in ("PIX", "CREDIT_CARD"):
        raise HTTPException(400, "billingType invalido. Use 'PIX' ou 'CREDIT_CARD'")
    if not body.customer.strip():
        raise HTTPException(400, "customer (ID do cliente no ASAAS) e obrigatorio")
    if body.billingType == "CREDIT_CARD" and not body.creditCardToken and not body.creditCard:
        raise HTTPException(400, "Informe creditCardToken ou creditCard para pagamento com cartao")
    if body.billingType == "CREDIT_CARD" and body.creditCard and not body.creditCardHolderInfo:
        raise HTTPException(400, "creditCardHolderInfo e obrigatorio quando creditCard e informado")
    if not ASAAS_API_KEY:
        raise HTTPException(500, "KEALEX_ASAAS_API_KEY nao configurada")

    cobranca = db.query(Cobranca).filter_by(
        id=body.cobrancaId, tenant_id=payload.get("tenant_id")
    ).first()
    if not cobranca:
        raise HTTPException(404, "Cobranca nao encontrada")
    if cobranca.status in ("pago", "cancelado"):
        raise HTTPException(400, f"Cobranca com status '{cobranca.status}' nao pode ser paga")

    payload_asaas = build_asaas_payload(body, cobranca)
    try:
        response = httpx.post(
            f"{ASAAS_BASE}/payments",
            json=payload_asaas,
            headers={
                "accept": "application/json",
                "content-type": "application/json",
                "access_token": ASAAS_API_KEY,
                "User-Agent": "Kealex/1.0.0",
            },
            timeout=15,
        )
    except httpx.RequestError as exc:
        logger.error("Falha de conexao com ASAAS: %s", exc)
        raise HTTPException(502, "Erro ao conectar com gateway de pagamento")

    if response.status_code not in (200, 201):
        logger.error("ASAAS recusou pagamento: status=%s body=%s", response.status_code, response.text)
        raise HTTPException(502, "ASAAS nao conseguiu criar o pagamento")

    asaas_data = response.json()
    status_anterior = cobranca.status
    cobranca.status = "aguardando_pagamento"
    cobranca.fase_atual = max(cobranca.fase_atual, 1)
    cobranca.updated_at = now_utc()
    db.add(HistoricoCobranca(
        id=str(uuid.uuid4()), cobranca_id=cobranca.id, acao="pagamento_iniciado",
        status_anterior=status_anterior, status_novo=cobranca.status,
        observacao=f"billingType={body.billingType}, asaas_id={asaas_data.get('id')}",
    ))
    db.commit()
    return {
        "cobrancaId": cobranca.id,
        "asaasId": asaas_data.get("id"),
        "billingType": asaas_data.get("billingType"),
        "status": asaas_data.get("status"),
        "value": asaas_data.get("value"),
        "dueDate": asaas_data.get("dueDate"),
        "invoiceUrl": asaas_data.get("invoiceUrl"),
        "pixQrCodeUrl": asaas_data.get("pixQrCodeUrl"),
    }

@router.get("/v1/lex/cobrancas")
@router.get("/k1/lex/cobrancas")
@router.get(PREFIX, include_in_schema=False)
def listar_cobrancas(db: Session = Depends(get_db), payload=Depends(auth_guard)):
    try:
        tenant_id = payload.get("tenant_id")
        cobrancas = db.query(Cobranca).filter_by(tenant_id=tenant_id).order_by(Cobranca.created_at.desc()).all()
        logger.info(f"[LIST_COBRANCAS] Total de cobrancas: {len(cobrancas)}")
        return [serialize_charge(c) for c in cobrancas]
    except Exception as e:
        logger.error(f"[LIST_COBRANCAS] ERRO: {str(e)}", exc_info=True)
        raise HTTPException(500, f"Erro ao listar cobrancas: {str(e)}")

@router.post("/v1/lex/cobrancas/get")
@router.post("/k1/lex/cobrancas/get")
@router.post(f"{PREFIX}/get", include_in_schema=False)
def get_cobranca(body: dict, db: Session = Depends(get_db), payload=Depends(auth_guard)):
    try:
        cobranca_id = body.get("id")
        if not cobranca_id:
            raise HTTPException(400, "ID obrigatorio")
        
        tenant_id = payload.get("tenant_id")
        cobranca = db.query(Cobranca).filter_by(id=cobranca_id, tenant_id=tenant_id).first()
        if not cobranca:
            raise HTTPException(404, "Cobranca nao encontrada")
        
        logger.info(f"[GET_COBRANCA] Cobranca recuperada: {cobranca_id}")
        return serialize_charge(cobranca)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[GET_COBRANCA] ERRO: {str(e)}", exc_info=True)
        raise HTTPException(500, f"Erro ao obter cobranca: {str(e)}")

@router.post("/v1/lex/cobrancas/proxima-fase")
@router.post("/k1/lex/cobrancas/proxima-fase")
@router.post(f"{PREFIX}/proxima-fase", include_in_schema=False)
def proxima_fase_cobranca(body: dict, db: Session = Depends(get_db), payload=Depends(auth_guard)):
    try:
        cobranca_id = body.get("id")
        if not cobranca_id:
            raise HTTPException(400, "ID obrigatorio")
        
        tenant_id = payload.get("tenant_id")
        cobranca = db.query(Cobranca).filter_by(id=cobranca_id, tenant_id=tenant_id).first()
        if not cobranca:
            raise HTTPException(404, "Cobranca nao encontrado")
        
        if cobranca.status == "pago" or cobranca.status == "cancelado":
            raise HTTPException(400, f"Nao e possivel avancar fase de cobranca com status {cobranca.status}")
        
        fases_cobranca = ["Pendente", "Aguardando Pagamento", "Vencida", "Em Cobranca", "Pago"]
        
        fase_anterior = cobranca.fase_atual
        nova_fase = min(cobranca.fase_atual + 1, len(fases_cobranca) - 1)
        
        cobranca.fase_atual = nova_fase
        cobranca.updated_at = now_utc()
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
        
        logger.info(f"[PROXIMA_FASE] Fase avancada de {fase_anterior} para {nova_fase}")
        return serialize_charge(cobranca)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[PROXIMA_FASE] ERRO: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(500, f"Erro ao avancar fase: {str(e)}")

@router.post("/v1/lex/cobrancas/marcar-pago")
@router.post("/k1/lex/cobrancas/marcar-pago")
@router.post(f"{PREFIX}/marcar-pago", include_in_schema=False)
def marcar_pago(body: dict, db: Session = Depends(get_db), payload=Depends(auth_guard)):
    try:
        cobranca_id = body.get("id")
        if not cobranca_id:
            raise HTTPException(400, "ID obrigatorio")
        
        tenant_id = payload.get("tenant_id")
        cobranca = db.query(Cobranca).filter_by(id=cobranca_id, tenant_id=tenant_id).first()
        if not cobranca:
            raise HTTPException(404, "Cobranca nao encontrado")
        
        if cobranca.status == "cancelado":
            raise HTTPException(400, "Nao e possivel marcar como pago uma cobranca cancelada")
        
        status_anterior = cobranca.status
        cobranca.status = "pago"
        cobranca.fase_atual = 4
        cobranca.data_pagamento = now_utc()
        cobranca.updated_at = now_utc()
        db.add(cobranca)
        
        historico = HistoricoCobranca(
            id=str(uuid.uuid4()),
            cobranca_id=cobranca.id,
            acao="marcado_pago",
            status_anterior=status_anterior,
            status_novo="pago",
            observacao=body.get("observacao", "Marcado como pago")
        )
        db.add(historico)
        db.commit()
        
        logger.info(f"[MARCAR_PAGO] Cobranca marcada como pago: {cobranca_id}")
        return serialize_charge(cobranca)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[MARCAR_PAGO] ERRO: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(500, f"Erro ao marcar como pago: {str(e)}")

@router.post("/v1/lex/cobrancas/cancelar")
@router.post("/k1/lex/cobrancas/cancelar")
@router.post(f"{PREFIX}/cancelar", include_in_schema=False)
def cancelar_cobranca(body: dict, db: Session = Depends(get_db), payload=Depends(auth_guard)):
    try:
        cobranca_id = body.get("id")
        if not cobranca_id:
            raise HTTPException(400, "ID obrigatorio")
        
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
        cobranca.updated_at = now_utc()
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
        
        logger.info(f"[CANCELAR] Cobranca cancelada: {cobranca_id}")
        return serialize_charge(cobranca)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[CANCELAR] ERRO: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(500, f"Erro ao cancelar cobranca: {str(e)}")

@router.post("/v1/lex/cobrancas/timeline")
@router.post("/k1/lex/cobrancas/timeline")
@router.post(f"{PREFIX}/timeline", include_in_schema=False)
def timeline_cobranca(body: dict, db: Session = Depends(get_db), payload=Depends(verify_token)):
    try:
        cobranca_id = body.get("id")
        if not cobranca_id:
            raise HTTPException(400, "ID obrigatorio")
        
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
        
        timeline = [
            {"id": h.id, "acao": h.acao, "fase_anterior": h.fase_anterior, "fase_nova": h.fase_nova,
             "status_anterior": h.status_anterior, "status_novo": h.status_novo,
             "observacao": h.observacao, "data": h.created_at.isoformat()}
            for h in historico
        ]
        
        logger.info(f"[TIMELINE] Timeline recuperada: {len(timeline)} eventos")
        return {
            "cobranca_id": cobranca_id,
            "status_atual": cobranca.status,
            "fase_atual": cobranca.fase_atual,
            "valor_centavos": cobranca.valor_centavos,
            "data_vencimento": cobranca.data_vencimento.isoformat() if cobranca.data_vencimento else None,
            "data_pagamento": cobranca.data_pagamento.isoformat() if cobranca.data_pagamento else None,
            "fases": fases_cobranca,
            "timeline": timeline,
            "proximas_acoes": get_next_actions(cobranca)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[TIMELINE] ERRO: {str(e)}", exc_info=True)
        raise HTTPException(500, f"Erro ao obter timeline: {str(e)}")

# ── Webhook ───────────────────────────────────────────────────────────────────

# Mapeamento evento Asaas → (status_interno, fase, acao_historico)
_EVENTO_MAP = {
    "PAYMENT_CONFIRMED":    ("pago",                4, "webhook_pago"),
    "PAYMENT_RECEIVED":     ("pago",                4, "webhook_pago"),
    "PAYMENT_OVERDUE":      ("vencida",             2, "webhook_vencida"),
    "PAYMENT_DELETED":      ("cancelado",           None, "webhook_cancelado"),
    "PAYMENT_REFUNDED":     ("cancelado",           None, "webhook_estornado"),
    "PAYMENT_CHARGEBACK_REQUESTED": ("cancelado",   None, "webhook_chargeback"),
}

def _verify_webhook_token(token: str | None) -> bool:
    if not ASAAS_WEBHOOK_TOKEN or not token:
        return False
    return hmac.compare_digest(
        token.encode("utf-8"),
        ASAAS_WEBHOOK_TOKEN.encode("utf-8"),
    )

@router.post("/v1/lex/cobrancas/webhook")
@router.post("/k1/lex/cobrancas/webhook")
@router.post(f"{PREFIX}/webhook", include_in_schema=False)
async def webhook_asaas(request: Request, db: Session = Depends(get_db)):
    import json as _json

    token = request.headers.get("asaas-access-token")
    if not _verify_webhook_token(token):
        logging.warning("[WEBHOOK] Token invalido ou ausente")
        raise HTTPException(401, "Token de webhook invalido")

    raw = await request.body()
    try:
        data = _json.loads(raw)
    except Exception:
        raise HTTPException(400, "Payload invalido")

    event_id = data.get("id")
    event_name = data.get("event", "")

    if not event_id:
        raise HTTPException(400, "Campo 'id' ausente no payload")

    # Idempotência
    if db.get(AsaasWebhookEvent, event_id):
        logging.info("[WEBHOOK] Evento duplicado ignorado event_id=%s", event_id)
        return {"ok": True, "duplicated": True}

    # Persiste o evento no schema compartilhado com svc-auth.
    db.add(AsaasWebhookEvent(id=event_id, event=event_name))

    # Atualiza a cobrança se o evento for mapeado
    payment = data.get("payment", {})
    external_ref = payment.get("externalReference")  # cobranca.id

    if event_name in _EVENTO_MAP and external_ref:
        novo_status, nova_fase, acao = _EVENTO_MAP[event_name]
        cobranca = db.query(Cobranca).filter_by(id=external_ref).first()
        if cobranca:
            status_anterior = cobranca.status
            cobranca.status = novo_status
            if nova_fase is not None:
                cobranca.fase_atual = nova_fase
            if novo_status == "pago":
                cobranca.data_pagamento = now_utc()
            cobranca.updated_at = now_utc()
            db.add(HistoricoCobranca(
                id=str(uuid.uuid4()),
                cobranca_id=cobranca.id,
                acao=acao,
                status_anterior=status_anterior,
                status_novo=novo_status,
                observacao=f"event_id={event_id} event={event_name}",
            ))
            logging.info(
                "[WEBHOOK] Cobranca atualizada cobranca_id=%s event=%s status=%s",
                cobranca.id, event_name, novo_status,
            )
        else:
            logging.warning("[WEBHOOK] Cobranca nao encontrada externalReference=%s", external_ref)
    else:
        logging.info("[WEBHOOK] Evento nao mapeado ignorado event=%s", event_name)

    db.commit()
    return {"ok": True}
