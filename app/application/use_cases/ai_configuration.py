from datetime import datetime

from sqlalchemy.orm import Session

from app.infrastructure.database.models import CfgIa


def _get_or_create_cfg_ia(db: Session, tenant_id: str, user_id: str):
    row = db.get(CfgIa, tenant_id)
    if not row:
        row = CfgIa(tenant_id=tenant_id, user_id=user_id)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row

def _upsert_cfg_ia(db: Session, tenant_id: str, user_id: str, data: dict):
    row = db.get(CfgIa, tenant_id)
    if not row:
        row = CfgIa(tenant_id=tenant_id, user_id=user_id)
        db.add(row)
    for k, v in data.items():
        setattr(row, k, v)
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return row


__all__ = ["_get_or_create_cfg_ia", "_upsert_cfg_ia"]
