from fastapi import APIRouter

from app.legacy_context import (
    Activity,
    ActivityColumn,
    ActivityColumnCreateIn,
    ActivityColumnUpdateIn,
    ActivityCreateIn,
    ActivityIdIn,
    ActivityUpdateIn,
    Depends,
    HTTPException,
    Session,
    _activity_column_json,
    _activity_json,
    _activity_owner,
    _ensure_activity_columns,
    datetime,
    get_db,
    uuid,
    verify_token,
)

router = APIRouter()


@router.get("/k1/lex/activities/columns")
def hub_list_activity_columns(payload=Depends(verify_token), db: Session = Depends(get_db)):
    user_id, tenant_id = _activity_owner(payload)
    return [_activity_column_json(row) for row in _ensure_activity_columns(db, user_id, tenant_id)]


@router.post("/k1/lex/activities/columns", status_code=201)
def hub_create_activity_column(body: ActivityColumnCreateIn, payload=Depends(verify_token), db: Session = Depends(get_db)):
    user_id, tenant_id = _activity_owner(payload)
    columns = _ensure_activity_columns(db, user_id, tenant_id)
    title = body.title.strip()
    if not title:
        raise HTTPException(400, "O nome da coluna é obrigatório")
    row = ActivityColumn(
        id=uuid.uuid4().hex[:20], user_id=user_id, tenant_id=tenant_id, title=title,
        color=body.color.upper(), position=max((column.position for column in columns), default=-1) + 1,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _activity_column_json(row)


@router.post("/k1/lex/activities/columns/update")
def hub_update_activity_column(body: ActivityColumnUpdateIn, payload=Depends(verify_token), db: Session = Depends(get_db)):
    user_id, tenant_id = _activity_owner(payload)
    row = db.query(ActivityColumn).filter_by(id=body.id, user_id=user_id, tenant_id=tenant_id).first()
    if not row:
        raise HTTPException(404, "Coluna não encontrada")
    fields = body.model_dump(exclude_unset=True, exclude={"id"})
    if not fields:
        raise HTTPException(400, "Informe o nome ou a cor da coluna")
    for name, value in fields.items():
        if value is None:
            raise HTTPException(400, f"O campo {name} não pode ser nulo")
        if name == "title":
            value = value.strip()
            if not value:
                raise HTTPException(400, "O nome da coluna é obrigatório")
        if name == "color":
            value = value.upper()
        setattr(row, name, value)
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return _activity_column_json(row)


@router.post("/k1/lex/activities/columns/delete")
def hub_delete_activity_column(body: ActivityIdIn, payload=Depends(verify_token), db: Session = Depends(get_db)):
    user_id, tenant_id = _activity_owner(payload)
    row = db.query(ActivityColumn).filter_by(id=body.id, user_id=user_id, tenant_id=tenant_id).first()
    if not row:
        raise HTTPException(404, "Coluna não encontrada")
    if db.query(ActivityColumn).filter_by(user_id=user_id, tenant_id=tenant_id).count() <= 1:
        raise HTTPException(409, "O quadro precisa manter pelo menos uma coluna")
    if db.query(Activity).filter_by(user_id=user_id, tenant_id=tenant_id, status=body.id).first():
        raise HTTPException(409, "Mova as atividades desta coluna antes de excluí-la")
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.get("/k1/lex/activities")
def hub_list_activities(status: str | None = None, payload=Depends(verify_token), db: Session = Depends(get_db)):
    user_id, tenant_id = _activity_owner(payload)
    _ensure_activity_columns(db, user_id, tenant_id)
    query = db.query(Activity).filter(Activity.user_id == user_id, Activity.tenant_id == tenant_id)
    if status is not None:
        if not db.query(ActivityColumn).filter_by(id=status, user_id=user_id, tenant_id=tenant_id).first():
            raise HTTPException(400, "Status de atividade inválido")
        query = query.filter(Activity.status == status)
    return [_activity_json(row) for row in query.order_by(Activity.created_at.desc()).all()]


@router.post("/k1/lex/activities", status_code=201)
def hub_create_activity(body: ActivityCreateIn, payload=Depends(verify_token), db: Session = Depends(get_db)):
    user_id, tenant_id = _activity_owner(payload)
    columns = _ensure_activity_columns(db, user_id, tenant_id)
    if body.status not in {column.id for column in columns}:
        raise HTTPException(400, "Coluna de atividade inválida")
    if body.priority not in {"baixa", "media", "alta"}:
        raise HTTPException(400, "Prioridade inválida")
    title = body.title.strip()
    if not title:
        raise HTTPException(400, "O título da atividade é obrigatório")
    row = Activity(
        user_id=user_id, tenant_id=tenant_id, title=title, description=body.description.strip(),
        status=body.status, priority=body.priority, due_date=body.dueDate,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _activity_json(row)


@router.post("/k1/lex/activities/update")
def hub_update_activity(body: ActivityUpdateIn, payload=Depends(verify_token), db: Session = Depends(get_db)):
    user_id, tenant_id = _activity_owner(payload)
    row = db.query(Activity).filter_by(id=body.id, user_id=user_id, tenant_id=tenant_id).first()
    if not row:
        raise HTTPException(404, "Atividade não encontrada")
    for name, value in body.model_dump(exclude_unset=True, exclude={"id"}).items():
        if name == "status" and value is not None:
            if not db.query(ActivityColumn).filter_by(id=value, user_id=user_id, tenant_id=tenant_id).first():
                raise HTTPException(400, "Coluna de atividade inválida")
        if name == "priority" and value is not None and value not in {"baixa", "media", "alta"}:
            raise HTTPException(400, "Prioridade inválida")
        if name == "title" and value is not None:
            value = value.strip()
            if not value:
                raise HTTPException(400, "O título da atividade é obrigatório")
        if name == "description" and value is not None:
            value = value.strip()
        setattr(row, "due_date" if name == "dueDate" else name, value)
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return _activity_json(row)


@router.post("/k1/lex/activities/delete")
def hub_delete_activity(body: ActivityIdIn, payload=Depends(verify_token), db: Session = Depends(get_db)):
    user_id, tenant_id = _activity_owner(payload)
    row = db.query(Activity).filter_by(id=body.id, user_id=user_id, tenant_id=tenant_id).first()
    if not row:
        raise HTTPException(404, "Atividade não encontrada")
    db.delete(row)
    db.commit()
    return {"ok": True}
