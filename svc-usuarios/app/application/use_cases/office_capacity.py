from typing import Optional
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

OFFICE_LIMIT_MESSAGE = "Limite de {limit} advogados atingido para este escrit\u00f3rio. Entre em contato com o suporte/admin para alterar o limite."

def ensure_escritorio_capacity(db: Session, tenant_id: str, escritorio_id: str, exclude_user_id: Optional[str] = None):
    office = db.execute(
        text("SELECT limite_advogados FROM escritorios WHERE id = :eid AND tenant_id = :tid FOR UPDATE"),
        {"eid": escritorio_id, "tid": tenant_id},
    ).mappings().first()
    if not office:
        raise HTTPException(404, "Escritório não encontrado")

    query = "SELECT COUNT(*) FROM usuarios WHERE escritorio_id = :eid AND tenant_id = :tid AND ativo = 1 AND role = 'advogado'"
    params = {"eid": escritorio_id, "tid": tenant_id}
    if exclude_user_id:
        query += " AND id <> :uid"
        params["uid"] = exclude_user_id
    count = db.execute(text(query), params).scalar_one()
    limit = int(office["limite_advogados"])
    if count >= limit:
        raise HTTPException(400, OFFICE_LIMIT_MESSAGE.format(limit=limit))
