from datetime import datetime
from typing import Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.dependencies import get_activity_owner
from app.api.schemas.activity_schema import ActivityCreate, ActivityUpdate, ActivityColumnCreate, ActivityColumnUpdate, ActivityDelete, ActivityColumnDelete
from app.application.use_cases.activity_support import ensure_activity_columns, activity_column_to_dict, activity_to_dict
from app.infrastructure.database.models.activity_model import Activity, ActivityColumn
from app.infrastructure.database.session import get_db
from app.infrastructure.security.jwt_provider import verify_token

router = APIRouter()


@router.get("/activities/columns")
@router.get("/api/activities/columns")
@router.get("/k1/lex/activities/columns")
@router.get("/v1/lex/activities/columns")
def list_activity_columns(token: dict = Depends(verify_token), db: Session = Depends(get_db)):
    user_id, tenant_id = get_activity_owner(token)
    return [activity_column_to_dict(row) for row in ensure_activity_columns(db, user_id, tenant_id)]


@router.post("/activities/columns", status_code=201)
@router.post("/api/activities/columns", status_code=201)
@router.post("/k1/lex/activities/columns", status_code=201)
@router.post("/v1/lex/activities/columns", status_code=201)
def create_activity_column(body: ActivityColumnCreate, token: dict = Depends(verify_token), db: Session = Depends(get_db)):
    user_id, tenant_id = get_activity_owner(token)
    columns = ensure_activity_columns(db, user_id, tenant_id)
    title = body.title.strip()
    if not title:
        raise HTTPException(400, "O nome da coluna é obrigatório")
    row = ActivityColumn(id=uuid.uuid4().hex[:20], user_id=user_id, tenant_id=tenant_id, title=title,
                         color=body.color.upper(), position=max((item.position for item in columns), default=-1) + 1)
    db.add(row)
    db.commit()
    db.refresh(row)
    return activity_column_to_dict(row)


@router.post("/activities/columns/update")
@router.post("/api/activities/columns/update")
@router.post("/k1/lex/activities/columns/update")
@router.post("/v1/lex/activities/columns/update")
def update_activity_column(body: ActivityColumnUpdate, token: dict = Depends(verify_token), db: Session = Depends(get_db)):
    user_id, tenant_id = get_activity_owner(token)
    row = db.query(ActivityColumn).filter_by(id=body.id, user_id=user_id, tenant_id=tenant_id).first()
    if not row:
        raise HTTPException(404, "Coluna não encontrada")
    fields = body.model_dump(exclude_unset=True, exclude={"id"})
    if not fields:
        raise HTTPException(400, "Informe o nome ou a cor da coluna")
    for field, value in fields.items():
        if value is None:
            raise HTTPException(400, f"O campo {field} não pode ser nulo")
        if field == "title":
            value = value.strip()
            if not value:
                raise HTTPException(400, "O nome da coluna é obrigatório")
        if field == "color":
            value = value.upper()
        setattr(row, field, value)
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return activity_column_to_dict(row)


@router.post("/activities/columns/delete")
@router.post("/api/activities/columns/delete")
@router.post("/k1/lex/activities/columns/delete")
@router.post("/v1/lex/activities/columns/delete")
def delete_activity_column(body: ActivityColumnDelete, token: dict = Depends(verify_token), db: Session = Depends(get_db)):
    user_id, tenant_id = get_activity_owner(token)
    row = db.query(ActivityColumn).filter_by(id=body.id, user_id=user_id, tenant_id=tenant_id).first()
    if not row:
        raise HTTPException(404, "Coluna não encontrada")
    if db.query(ActivityColumn).filter_by(user_id=user_id, tenant_id=tenant_id).count() <= 1:
        raise HTTPException(409, "O quadro precisa manter pelo menos uma coluna")
    has_activities = db.query(Activity).filter_by(user_id=user_id, tenant_id=tenant_id, status=body.id).first()
    if has_activities:
        raise HTTPException(409, "Mova as atividades desta coluna antes de excluí-la")
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.get("/activities")
@router.get("/api/activities")
@router.get("/k1/lex/activities")
@router.get("/v1/lex/activities")
def list_activities(status: Optional[str] = None, token: dict = Depends(verify_token), db: Session = Depends(get_db)):
    user_id, tenant_id = get_activity_owner(token)
    if status is not None and not db.query(ActivityColumn).filter_by(id=status, user_id=user_id, tenant_id=tenant_id).first():
        raise HTTPException(400, "Status de atividade inválido")
    query = db.query(Activity).filter(Activity.user_id == user_id, Activity.tenant_id == tenant_id)
    if status:
        query = query.filter(Activity.status == status)
    return [activity_to_dict(row) for row in query.order_by(Activity.created_at.desc()).all()]


@router.post("/activities", status_code=201)
@router.post("/api/activities", status_code=201)
@router.post("/k1/lex/activities", status_code=201)
@router.post("/v1/lex/activities", status_code=201)
def create_activity(body: ActivityCreate, token: dict = Depends(verify_token), db: Session = Depends(get_db)):
    user_id, tenant_id = get_activity_owner(token)
    columns = ensure_activity_columns(db, user_id, tenant_id)
    if body.status not in {column.id for column in columns}:
        raise HTTPException(400, "Coluna de atividade inválida")
    title = body.title.strip()
    if not title:
        raise HTTPException(400, "O título da atividade é obrigatório")
    row = Activity(
        user_id=user_id,
        tenant_id=tenant_id,
        title=title,
        description=body.description.strip(),
        status=body.status,
        priority=body.priority,
        due_date=body.dueDate,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return activity_to_dict(row)


@router.post("/activities/update")
@router.post("/api/activities/update")
@router.post("/k1/lex/activities/update")
@router.post("/v1/lex/activities/update")
def update_activity(body: ActivityUpdate, token: dict = Depends(verify_token), db: Session = Depends(get_db)):
    user_id, tenant_id = get_activity_owner(token)
    row = db.query(Activity).filter(
        Activity.id == body.id,
        Activity.user_id == user_id,
        Activity.tenant_id == tenant_id,
    ).first()
    if not row:
        raise HTTPException(404, "Atividade não encontrada")
    for api_name, value in body.model_dump(exclude_unset=True, exclude={"id"}).items():
        if api_name != "dueDate" and value is None:
            raise HTTPException(400, f"O campo {api_name} não pode ser nulo")
        column = "due_date" if api_name == "dueDate" else api_name
        if api_name == "status":
            valid_column = db.query(ActivityColumn).filter_by(id=value, user_id=user_id, tenant_id=tenant_id).first()
            if not valid_column:
                raise HTTPException(400, "Coluna de atividade inválida")
        if api_name == "title":
            value = value.strip()
            if not value:
                raise HTTPException(400, "O título da atividade é obrigatório")
        elif api_name == "description" and value is not None:
            value = value.strip()
        setattr(row, column, value)
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return activity_to_dict(row)


@router.post("/activities/delete")
@router.post("/api/activities/delete")
@router.post("/k1/lex/activities/delete")
@router.post("/v1/lex/activities/delete")
def delete_activity(body: ActivityDelete, token: dict = Depends(verify_token), db: Session = Depends(get_db)):
    user_id, tenant_id = get_activity_owner(token)
    row = db.query(Activity).filter(
        Activity.id == body.id,
        Activity.user_id == user_id,
        Activity.tenant_id == tenant_id,
    ).first()
    if not row:
        raise HTTPException(404, "Atividade não encontrada")
    db.delete(row)
    db.commit()
    return {"ok": True}
