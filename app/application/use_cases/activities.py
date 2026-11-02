from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.infrastructure.database.models import ActivityColumn

_ACTIVITY_DEFAULT_COLUMNS = [
    {"id": "todo", "title": "A Fazer", "color": "#087E96"},
    {"id": "in_progress", "title": "Em Andamento", "color": "#D97706"},
    {"id": "done", "title": "Concluído", "color": "#16834F"},
]


def _ensure_activity_columns(db: Session, user_id: str, tenant_id: str):
    columns = db.query(ActivityColumn).filter_by(user_id=user_id, tenant_id=tenant_id).order_by(ActivityColumn.position).all()
    if columns:
        return columns
    now = datetime.utcnow()
    columns = [
        ActivityColumn(**definition, user_id=user_id, tenant_id=tenant_id, position=position, created_at=now, updated_at=now)
        for position, definition in enumerate(_ACTIVITY_DEFAULT_COLUMNS)
    ]
    db.add_all(columns)
    db.commit()
    return db.query(ActivityColumn).filter_by(user_id=user_id, tenant_id=tenant_id).order_by(ActivityColumn.position).all()

def _activity_owner(payload: dict) -> tuple[str, str]:
    user_id, tenant_id = payload.get("sub"), payload.get("tenant_id")
    if not user_id or not tenant_id:
        raise HTTPException(401, "Token sem usuário ou escritório associado")
    return str(user_id), str(tenant_id)


__all__ = [name for name in globals() if not name.startswith("__")]
