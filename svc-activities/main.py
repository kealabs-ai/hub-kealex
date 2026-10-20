from dotenv import load_dotenv

load_dotenv()

import os
import uuid
from datetime import date, datetime
from typing import Literal, Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel, Field
from sqlalchemy import Column, Date, DateTime, Index, Integer, PrimaryKeyConstraint, String, Text, create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


def _get_database_url():
    host = os.getenv("KEALEX_DB_HOST")
    database = os.getenv("KEALEX_DB_NAME")
    username = os.getenv("KEALEX_DB_USER")
    password = os.getenv("KEALEX_DB_PASSWORD")
    if host and database and username and password is not None:
        return URL.create(
            drivername="mysql+pymysql",
            username=username,
            password=password,
            host=host,
            port=int(os.getenv("KEALEX_DB_PORT", "3306")),
            database=database,
        )
    raw = os.getenv("KEALEX_DATABASE_URL")
    if raw is None or raw.strip().lower() in ("", "null", "none"):
        raise RuntimeError(
            "Configure KEALEX_DB_HOST, KEALEX_DB_NAME, KEALEX_DB_USER e "
            "KEALEX_DB_PASSWORD (ou KEALEX_DATABASE_URL)"
        )
    return make_url(raw.strip())


DATABASE_URL = _get_database_url()
SECRET_KEY = os.getenv("KEALEX_SECRET_KEY") or os.getenv("KEALEX_JWT_SECRET")
if not SECRET_KEY:
    raise RuntimeError("KEALEX_SECRET_KEY ou KEALEX_JWT_SECRET precisa estar configurada no ambiente")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=280,
    pool_size=5,
    max_overflow=10,
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
bearer = HTTPBearer()


class Base(DeclarativeBase):
    pass


class Activity(Base):
    __tablename__ = "activities"
    __table_args__ = (
        Index("ix_activities_user_id", "user_id"),
        Index("ix_activities_status", "status"),
        Index("ix_activities_user_status", "user_id", "status"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=False)
    tenant_id = Column(String(36), nullable=False)
    title = Column(String(180), nullable=False)
    description = Column(Text, nullable=False, default="")
    status = Column(String(36), nullable=False, default="todo")
    priority = Column(String(20), nullable=False, default="media")
    due_date = Column(Date, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class ActivityColumn(Base):
    __tablename__ = "activity_columns"
    __table_args__ = (
        PrimaryKeyConstraint("user_id", "id", name="pk_activity_columns_user_id_id"),
        Index("ix_activity_columns_tenant_user_position", "tenant_id", "user_id", "position"),
    )

    id = Column(String(36), nullable=False)
    user_id = Column(String(36), nullable=False)
    tenant_id = Column(String(36), nullable=False)
    title = Column(String(80), nullable=False)
    color = Column(String(7), nullable=False, default="#087E96")
    position = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def verify_token(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    try:
        return jwt.decode(creds.credentials, SECRET_KEY, algorithms=["HS256"])
    except JWTError:
        raise HTTPException(401, "Token inválido")


app = FastAPI(title="svc-activities")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv("KEALEX_CORS_ALLOWED_ORIGINS", "").split(",") if origin.strip()],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    allow_credentials=True,
)


@app.on_event("startup")
def startup_event():
    try:
        Base.metadata.create_all(engine)
    except Exception as exc:
        print(f"[ERRO] Database init falhou: {type(exc).__name__}: {exc}")


@app.get("/health")
def health():
    return {"status": "ok", "service": "svc-activities"}


class ActivityCreate(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    description: str = Field(default="", max_length=5000)
    status: str = Field(default="todo", min_length=1, max_length=36)
    priority: Literal["baixa", "media", "alta"] = "media"
    dueDate: date | None = None


class ActivityUpdate(BaseModel):
    id: str
    title: str | None = Field(default=None, min_length=1, max_length=180)
    description: str | None = Field(default=None, max_length=5000)
    status: str | None = Field(default=None, min_length=1, max_length=36)
    priority: Literal["baixa", "media", "alta"] | None = None
    dueDate: date | None = None


class ActivityColumnCreate(BaseModel):
    title: str = Field(min_length=1, max_length=80)
    color: str = Field(default="#087E96", pattern=r"^#[0-9A-Fa-f]{6}$")


class ActivityColumnUpdate(BaseModel):
    id: str
    title: str | None = Field(default=None, min_length=1, max_length=80)
    color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")


class ActivityDelete(BaseModel):
    id: str


class ActivityColumnDelete(BaseModel):
    id: str


_DEFAULT_ACTIVITY_COLUMNS = [
    {"id": "todo", "title": "A Fazer", "color": "#087E96"},
    {"id": "in_progress", "title": "Em Andamento", "color": "#D97706"},
    {"id": "done", "title": "Concluído", "color": "#16834F"},
]


def _activity_column_to_dict(column: ActivityColumn):
    return {
        "id": column.id, "title": column.title, "color": column.color,
        "position": column.position, "createdAt": column.created_at.isoformat(),
        "updatedAt": column.updated_at.isoformat(),
    }


def _ensure_activity_columns(db: Session, user_id: str, tenant_id: str):
    columns = db.query(ActivityColumn).filter_by(user_id=user_id, tenant_id=tenant_id).order_by(ActivityColumn.position).all()
    if columns:
        return columns
    now = datetime.utcnow()
    columns = [ActivityColumn(**definition, user_id=user_id, tenant_id=tenant_id, position=index, created_at=now, updated_at=now)
               for index, definition in enumerate(_DEFAULT_ACTIVITY_COLUMNS)]
    db.add_all(columns)
    db.commit()
    return db.query(ActivityColumn).filter_by(user_id=user_id, tenant_id=tenant_id).order_by(ActivityColumn.position).all()


def _activity_to_dict(activity: Activity):
    return {
        "id": activity.id,
        "userId": activity.user_id,
        "title": activity.title,
        "description": activity.description,
        "status": activity.status,
        "priority": activity.priority,
        "dueDate": activity.due_date.isoformat() if activity.due_date else None,
        "createdAt": activity.created_at.isoformat(),
        "updatedAt": activity.updated_at.isoformat(),
    }


def _activity_owner(token: dict):
    user_id, tenant_id = token.get("sub"), token.get("tenant_id")
    if not user_id or not tenant_id:
        raise HTTPException(401, "Token sem usuário ou escritório associado")
    return str(user_id), str(tenant_id)


@app.get("/activities/columns")
@app.get("/api/activities/columns")
@app.get("/k1/lex/activities/columns")
@app.get("/v1/lex/activities/columns")
def list_activity_columns(token: dict = Depends(verify_token), db: Session = Depends(get_db)):
    user_id, tenant_id = _activity_owner(token)
    return [_activity_column_to_dict(row) for row in _ensure_activity_columns(db, user_id, tenant_id)]


@app.post("/activities/columns", status_code=201)
@app.post("/api/activities/columns", status_code=201)
@app.post("/k1/lex/activities/columns", status_code=201)
@app.post("/v1/lex/activities/columns", status_code=201)
def create_activity_column(body: ActivityColumnCreate, token: dict = Depends(verify_token), db: Session = Depends(get_db)):
    user_id, tenant_id = _activity_owner(token)
    columns = _ensure_activity_columns(db, user_id, tenant_id)
    title = body.title.strip()
    if not title:
        raise HTTPException(400, "O nome da coluna é obrigatório")
    row = ActivityColumn(id=uuid.uuid4().hex[:20], user_id=user_id, tenant_id=tenant_id, title=title,
                         color=body.color.upper(), position=max((item.position for item in columns), default=-1) + 1)
    db.add(row)
    db.commit()
    db.refresh(row)
    return _activity_column_to_dict(row)


@app.post("/activities/columns/update")
@app.post("/api/activities/columns/update")
@app.post("/k1/lex/activities/columns/update")
@app.post("/v1/lex/activities/columns/update")
def update_activity_column(body: ActivityColumnUpdate, token: dict = Depends(verify_token), db: Session = Depends(get_db)):
    user_id, tenant_id = _activity_owner(token)
    row = db.query(ActivityColumn).filter_by(id=body.id, user_id=user_id, tenant_id=tenant_id).first()
    if not row:
        raise HTTPException(404, "Coluna não encontrada")
    fields = body.model_dump(exclude_unset=True)
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
    return _activity_column_to_dict(row)


@app.post("/activities/columns/delete")
@app.post("/api/activities/columns/delete")
@app.post("/k1/lex/activities/columns/delete")
@app.post("/v1/lex/activities/columns/delete")
def delete_activity_column(body: ActivityColumnDelete, token: dict = Depends(verify_token), db: Session = Depends(get_db)):
    user_id, tenant_id = _activity_owner(token)
    row = db.query(ActivityColumn).filter_by(id=body.id, user_id=user_id, tenant_id=tenant_id).first()
    if not row:
        raise HTTPException(404, "Coluna não encontrada")
    if db.query(ActivityColumn).filter_by(user_id=user_id, tenant_id=tenant_id).count() <= 1:
        raise HTTPException(409, "O quadro precisa manter pelo menos uma coluna")
    has_activities = db.query(Activity).filter_by(user_id=user_id, tenant_id=tenant_id, status=column_id).first()
    if has_activities:
        raise HTTPException(409, "Mova as atividades desta coluna antes de excluí-la")
    db.delete(row)
    db.commit()
    return {"ok": True}

@app.get("/activities")
@app.get("/api/activities")
@app.get("/k1/lex/activities")
@app.get("/v1/lex/activities")
def list_activities(status: Optional[str] = None, token: dict = Depends(verify_token), db: Session = Depends(get_db)):
    user_id, tenant_id = _activity_owner(token)
    if status is not None and not db.query(ActivityColumn).filter_by(id=status, user_id=user_id, tenant_id=tenant_id).first():
        raise HTTPException(400, "Status de atividade inválido")
    query = db.query(Activity).filter(Activity.user_id == user_id, Activity.tenant_id == tenant_id)
    if status:
        query = query.filter(Activity.status == status)
    return [_activity_to_dict(row) for row in query.order_by(Activity.created_at.desc()).all()]


@app.post("/activities", status_code=201)
@app.post("/api/activities", status_code=201)
@app.post("/k1/lex/activities", status_code=201)
@app.post("/v1/lex/activities", status_code=201)
def create_activity(body: ActivityCreate, token: dict = Depends(verify_token), db: Session = Depends(get_db)):
    user_id, tenant_id = _activity_owner(token)
    columns = _ensure_activity_columns(db, user_id, tenant_id)
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
    return _activity_to_dict(row)


@app.post("/activities/update")
@app.post("/api/activities/update")
@app.post("/k1/lex/activities/update")
@app.post("/v1/lex/activities/update")
def update_activity(body: ActivityUpdate, token: dict = Depends(verify_token), db: Session = Depends(get_db)):
    user_id, tenant_id = _activity_owner(token)
    row = db.query(Activity).filter(
        Activity.id == body.id,
        Activity.user_id == user_id,
        Activity.tenant_id == tenant_id,
    ).first()
    if not row:
        raise HTTPException(404, "Atividade não encontrada")
    for api_name, value in body.model_dump(exclude_unset=True).items():
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
    return _activity_to_dict(row)


@app.post("/activities/delete")
@app.post("/api/activities/delete")
@app.post("/k1/lex/activities/delete")
@app.post("/v1/lex/activities/delete")
def delete_activity(body: ActivityDelete, token: dict = Depends(verify_token), db: Session = Depends(get_db)):
    user_id, tenant_id = _activity_owner(token)
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
