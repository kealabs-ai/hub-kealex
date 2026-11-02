from fastapi import APIRouter

from app.legacy_context import (
    CfgCdn,
    CfgDatabase,
    CfgNotificacoes,
    CfgSeguranca,
    CfgUsuarios,
    Depends,
    Session,
    _require_admin,
    _row,
    datetime,
    get_db,
)

router = APIRouter()


@router.get("/k1/lex/configuracoes/database")
def get_database(db: Session = Depends(get_db), payload=Depends(_require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    row = db.get(CfgDatabase, tenant_id)
    if not row:
        row = CfgDatabase(tenant_id=tenant_id, user_id=user_id)
        db.add(row)
        db.commit()
        db.refresh(row)
    return _row(row)


@router.post("/k1/lex/configuracoes/database")
def save_database(body: dict, db: Session = Depends(get_db), payload=Depends(_require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    row = db.get(CfgDatabase, tenant_id)
    if not row:
        row = CfgDatabase(tenant_id=tenant_id, user_id=user_id)
        db.add(row)
    for k, v in body.items():
        if hasattr(row, k) and k != "tenant_id" and v is not None:
            setattr(row, k, v)
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return _row(row)


@router.get("/k1/lex/configuracoes/cdn")
def get_cdn(db: Session = Depends(get_db), payload=Depends(_require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    row = db.get(CfgCdn, tenant_id)
    if not row:
        row = CfgCdn(tenant_id=tenant_id, user_id=user_id)
        db.add(row)
        db.commit()
        db.refresh(row)
    return _row(row)


@router.post("/k1/lex/configuracoes/cdn")
def save_cdn(body: dict, db: Session = Depends(get_db), payload=Depends(_require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    row = db.get(CfgCdn, tenant_id)
    if not row:
        row = CfgCdn(tenant_id=tenant_id, user_id=user_id)
        db.add(row)
    for k, v in body.items():
        if hasattr(row, k) and k != "tenant_id" and v is not None:
            setattr(row, k, v)
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return _row(row)


@router.get("/k1/lex/configuracoes/usuarios")
def get_usuarios_cfg(db: Session = Depends(get_db), payload=Depends(_require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    row = db.get(CfgUsuarios, tenant_id)
    if not row:
        row = CfgUsuarios(tenant_id=tenant_id, user_id=user_id)
        db.add(row)
        db.commit()
        db.refresh(row)
    return _row(row)


@router.post("/k1/lex/configuracoes/usuarios")
def save_usuarios_cfg(body: dict, db: Session = Depends(get_db), payload=Depends(_require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    row = db.get(CfgUsuarios, tenant_id)
    if not row:
        row = CfgUsuarios(tenant_id=tenant_id, user_id=user_id)
        db.add(row)
    for k, v in body.items():
        if hasattr(row, k) and k != "tenant_id" and v is not None:
            setattr(row, k, v)
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return _row(row)


@router.get("/k1/lex/configuracoes/seguranca")
def get_seguranca(db: Session = Depends(get_db), payload=Depends(_require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    row = db.get(CfgSeguranca, tenant_id)
    if not row:
        row = CfgSeguranca(tenant_id=tenant_id, user_id=user_id)
        db.add(row)
        db.commit()
        db.refresh(row)
    return _row(row)


@router.post("/k1/lex/configuracoes/seguranca")
def save_seguranca(body: dict, db: Session = Depends(get_db), payload=Depends(_require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    row = db.get(CfgSeguranca, tenant_id)
    if not row:
        row = CfgSeguranca(tenant_id=tenant_id, user_id=user_id)
        db.add(row)
    for k, v in body.items():
        if hasattr(row, k) and k != "tenant_id" and v is not None:
            setattr(row, k, v)
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return _row(row)


@router.get("/k1/lex/configuracoes/notificacoes")
def get_notificacoes(db: Session = Depends(get_db), payload=Depends(_require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    row = db.get(CfgNotificacoes, tenant_id)
    if not row:
        row = CfgNotificacoes(tenant_id=tenant_id, user_id=user_id)
        db.add(row)
        db.commit()
        db.refresh(row)
    return _row(row)


@router.post("/k1/lex/configuracoes/notificacoes")
def save_notificacoes(body: dict, db: Session = Depends(get_db), payload=Depends(_require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    row = db.get(CfgNotificacoes, tenant_id)
    if not row:
        row = CfgNotificacoes(tenant_id=tenant_id, user_id=user_id)
        db.add(row)
    for k, v in body.items():
        if hasattr(row, k) and k != "tenant_id" and v is not None:
            setattr(row, k, v)
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return _row(row)
