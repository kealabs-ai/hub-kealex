from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.api.dependencies import auth_guard
from app.api.schemas.prazo_schema import PrazoIn, PrazoGetIn, PrazoByProcessoIn, PrazoVencendoIn, PrazoUpdate, PrazoDeleteIn
from app.application.use_cases.due_date_window import due_date_window
from app.application.use_cases.prazo_presenter import _to_dict
from app.domain.entities.prazo_status import StatusEnum
from app.infrastructure.database.models.prazo_model import Prazo
from app.infrastructure.database.session import get_db
router = APIRouter()

@router.get("/v1/lex/prazos")
def list_prazos(db: Session = Depends(get_db), payload=Depends(auth_guard)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    return [_to_dict(p) for p in db.query(Prazo).filter_by(tenant_id=tenant_id).all()]

@router.post("/v1/lex/prazos/get")
def get_prazo(body: PrazoGetIn, db: Session = Depends(get_db), payload=Depends(auth_guard)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    p = db.query(Prazo).filter_by(id=body.id, tenant_id=tenant_id).first()
    if not p:
        raise HTTPException(404, "Não encontrado")
    return _to_dict(p)

@router.post("/v1/lex/prazos/vencendo")
def vencendo(body: PrazoVencendoIn, db: Session = Depends(get_db), payload=Depends(auth_guard)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    hoje, limite = due_date_window(body.dias)
    rows = db.query(Prazo).filter(
        Prazo.tenant_id == tenant_id,
        Prazo.data_vencimento >= hoje,
        Prazo.data_vencimento <= limite,
        Prazo.status == StatusEnum.pendente
    ).all()
    return [_to_dict(p) for p in rows]

@router.post("/v1/lex/prazos/by-processo")
def by_processo(body: PrazoByProcessoIn, db: Session = Depends(get_db), payload=Depends(auth_guard)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    return [_to_dict(p) for p in db.query(Prazo).filter_by(
        tenant_id=tenant_id, processo_id=body.processoId).all()]

@router.post("/v1/lex/prazos", status_code=201)
def create_prazo(body: PrazoIn, db: Session = Depends(get_db), payload=Depends(auth_guard)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    processo = db.execute(
        text("SELECT id, advogado_id, escritorio_id FROM processos WHERE id = :pid AND tenant_id = :tid"),
        {"pid": body.processoId, "tid": tenant_id},
    ).first()
    if not processo:
        raise HTTPException(404, "Processo não encontrado")
    p = Prazo(tenant_id=tenant_id, user_id=payload["sub"], escritorio_id=processo.escritorio_id,
              processo_id=body.processoId, advogado_id=processo.advogado_id, titulo=body.titulo,
              descricao=body.descricao, data_vencimento=body.dataVencimento)
    db.add(p); db.commit(); db.refresh(p)
    return _to_dict(p)

@router.post("/v1/lex/prazos/update")
def update_prazo(body: PrazoUpdate, db: Session = Depends(get_db), payload=Depends(auth_guard)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    p = db.query(Prazo).filter_by(id=body.id, tenant_id=tenant_id).first()
    if not p:
        raise HTTPException(404, "Não encontrado")
    data = body.model_dump(exclude_none=True, exclude={"id"})
    if "dataVencimento" in data:
        p.data_vencimento = data.pop("dataVencimento")
    for k, v in data.items():
        setattr(p, k, v)
    p.updated_at = datetime.utcnow()
    db.commit(); db.refresh(p)
    return _to_dict(p)

@router.post("/v1/lex/prazos/delete")
def delete_prazo(body: PrazoDeleteIn, db: Session = Depends(get_db), payload=Depends(auth_guard)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    p = db.query(Prazo).filter_by(id=body.id, tenant_id=tenant_id).first()
    if not p:
        raise HTTPException(404, "Não encontrado")
    db.delete(p); db.commit()
    return {"ok": True}
