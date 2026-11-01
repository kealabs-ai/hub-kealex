from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.dependencies import auth_guard
from app.api.schemas.honorario_schema import HonorarioIn, HonorarioGetIn, HonorarioUpdate, HonorarioDeleteIn
from app.application.use_cases.financial_dashboard import calculate_totals
from app.application.use_cases.honorario_presenter import _to_dict
from app.domain.entities.honorario_status import StatusEnum
from app.infrastructure.database.models.honorario_model import Honorario
from app.infrastructure.database.session import get_db
router = APIRouter()

@router.get("/v1/lex/financeiro")
def list_honorarios(db: Session = Depends(get_db), payload=Depends(auth_guard)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    return [_to_dict(h) for h in db.query(Honorario).filter_by(tenant_id=tenant_id).all()]

@router.get("/v1/lex/financeiro/dashboard")
def dashboard(db: Session = Depends(get_db), payload=Depends(auth_guard)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    rows = db.query(Honorario).filter_by(tenant_id=tenant_id).all()
    return calculate_totals(rows)

@router.post("/v1/lex/financeiro/get")
def get_honorario(body: HonorarioGetIn, db: Session = Depends(get_db), payload=Depends(auth_guard)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    h = db.query(Honorario).filter_by(id=body.id, tenant_id=tenant_id).first()
    if not h:
        raise HTTPException(404, "Não encontrado")
    return _to_dict(h)

@router.post("/v1/lex/financeiro", status_code=201)
def create_honorario(body: HonorarioIn, db: Session = Depends(get_db), payload=Depends(auth_guard)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    h = Honorario(tenant_id=tenant_id, user_id=payload["sub"], escritorio_id=body.escritorioId,
                  processo_id=body.processoId, cliente_id=body.clienteId, advogado_id=payload["sub"],
                  descricao=body.descricao, valor_centavos=body.valorCentavos,
                  data_vencimento=body.dataVencimento)
    db.add(h); db.commit(); db.refresh(h)
    return _to_dict(h)

@router.post("/v1/lex/financeiro/update")
def update_honorario(body: HonorarioUpdate, db: Session = Depends(get_db), payload=Depends(auth_guard)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    h = db.query(Honorario).filter_by(id=body.id, tenant_id=tenant_id).first()
    if not h:
        raise HTTPException(404, "Não encontrado")
    data = body.model_dump(exclude_none=True, exclude={"id"})
    mapping = {"valorCentavos": "valor_centavos", "dataVencimento": "data_vencimento", "dataPagamento": "data_pagamento"}
    for k, v in data.items():
        setattr(h, mapping.get(k, k), v)
    h.updated_at = datetime.utcnow()
    db.commit(); db.refresh(h)
    return _to_dict(h)

@router.post("/v1/lex/financeiro/delete")
def delete_honorario(body: HonorarioDeleteIn, db: Session = Depends(get_db), payload=Depends(auth_guard)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    h = db.query(Honorario).filter_by(id=body.id, tenant_id=tenant_id).first()
    if not h:
        raise HTTPException(404, "Não encontrado")
    db.delete(h); db.commit()
    return {"ok": True}
