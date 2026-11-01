from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.infrastructure.database.models.processo_model import Processo

def _scoped_process(db: Session, processo_id: str, payload):
    role, uid = payload.get("role"), payload.get("sub")
    query = db.query(Processo).filter_by(id=processo_id, tenant_id=payload.get("tenant_id"))
    if role == "advogado":
        query = query.filter_by(advogado_id=uid, user_id=uid)
    elif role == "cliente":
        query = query.filter_by(cliente_id=uid)
    elif role != "admin":
        raise HTTPException(403, "Acesso negado")
    return query.first()

