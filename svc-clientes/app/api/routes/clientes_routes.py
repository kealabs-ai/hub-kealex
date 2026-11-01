from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.dependencies import client_access_guard
from app.api.schemas.client_schema import ClienteIn, ClienteUpdate, ClienteGetIn, ClienteDeleteIn
from app.application.use_cases.client_presenter import client_to_dict
from app.infrastructure.database.models.client_model import Cliente
from app.infrastructure.database.session import get_db

router = APIRouter()

@router.get("/v1/lex/clientes")
def list_clientes(db: Session = Depends(get_db), payload=Depends(client_access_guard)):
    tid  = payload.get("tenant_id") or payload.get("sub")
    role = payload.get("role")
    uid  = payload.get("sub")
    q = db.query(Cliente).filter_by(tenant_id=tid)
    if role == "advogado":
        q = q.filter_by(advogado_id=uid)
    return [client_to_dict(c) for c in q.all()]


@router.post("/v1/lex/clientes/get")
def get_cliente(body: ClienteGetIn, db: Session = Depends(get_db), payload=Depends(client_access_guard)):
    tid = payload.get("tenant_id") or payload.get("sub")
    q = db.query(Cliente).filter_by(id=body.id, tenant_id=tid)
    if payload.get("role") == "advogado":
        q = q.filter_by(advogado_id=payload.get("sub"))
    c = q.first()
    if not c:
        raise HTTPException(404, "Não encontrado")
    return client_to_dict(c)


@router.post("/v1/lex/clientes", status_code=201)
def create_cliente(body: ClienteIn, db: Session = Depends(get_db), payload=Depends(client_access_guard)):
    tid = payload.get("tenant_id") or payload.get("sub")
    uid = payload.get("sub")
    if db.query(Cliente).filter_by(email=body.email, tenant_id=tid).first():
        raise HTTPException(409, "Email já cadastrado")
    c = Cliente(
        tenant_id=tid, advogado_id=uid,
        nome=body.nome, email=body.email, telefone=body.telefone,
        cpf_cnpj=body.cpfCnpj, endereco=body.endereco, observacoes=body.observacoes,
    )
    db.add(c); db.commit(); db.refresh(c)
    return client_to_dict(c)


@router.post("/v1/lex/clientes/update")
def update_cliente(body: ClienteUpdate, db: Session = Depends(get_db), payload=Depends(client_access_guard)):
    tid = payload.get("tenant_id") or payload.get("sub")
    q = db.query(Cliente).filter_by(id=body.id, tenant_id=tid)
    if payload.get("role") == "advogado":
        q = q.filter_by(advogado_id=payload.get("sub"))
    c = q.first()
    if not c:
        raise HTTPException(404, "Não encontrado")
    data = body.model_dump(exclude_none=True, exclude={"id"})
    if "cpfCnpj" in data:
        c.cpf_cnpj = data.pop("cpfCnpj")
    for k, v in data.items():
        setattr(c, k, v)
    c.updated_at = datetime.utcnow()
    db.commit(); db.refresh(c)
    return client_to_dict(c)


@router.post("/v1/lex/clientes/delete")
def delete_cliente(body: ClienteDeleteIn, db: Session = Depends(get_db), payload=Depends(client_access_guard)):
    tid = payload.get("tenant_id") or payload.get("sub")
    q = db.query(Cliente).filter_by(id=body.id, tenant_id=tid)
    if payload.get("role") == "advogado":
        q = q.filter_by(advogado_id=payload.get("sub"))
    c = q.first()
    if not c:
        raise HTTPException(404, "Não encontrado")
    db.delete(c); db.commit()
    return {"ok": True}
