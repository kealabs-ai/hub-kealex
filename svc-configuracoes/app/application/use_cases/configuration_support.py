from datetime import datetime

def _row(obj) -> dict:
    d = {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
    for date_field in ["updated_at", "created_at", "indexado_em", "ultima_sync"]:
        if date_field in d and d[date_field]:
            d[date_field] = d[date_field].isoformat()
    return d

def _get_or_create(db, Model, tenant_id: str, user_id: str):
    row = db.get(Model, tenant_id)
    if not row:
        row = Model(tenant_id=tenant_id, user_id=user_id)
        # Para cfg_ia, definir escritorio_id como None explicitamente
        if Model.__tablename__ == 'cfg_ia':
            row.escritorio_id = None
        db.add(row)
        db.commit()
        db.refresh(row)
    return row

def _upsert(db, Model, tenant_id: str, user_id: str, data: dict):
    row = db.get(Model, tenant_id)
    if not row:
        row = Model(tenant_id=tenant_id, user_id=user_id)
        # Para cfg_ia, definir escritorio_id como None explicitamente
        if Model.__tablename__ == 'cfg_ia':
            row.escritorio_id = None
        db.add(row)
    for k, v in data.items():
        setattr(row, k, v)
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return row

