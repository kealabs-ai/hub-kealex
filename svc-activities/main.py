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
from sqlalchemy import Column, Date, DateTime, Index, String, Text, create_engine
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
    status = Column(String(20), nullable=False, default="todo")
    priority = Column(String(20), nullable=False, default="media")
    due_date = Column(Date, nullable=True)
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
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
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
    status: Literal["todo", "in_progress", "done"] = "todo"
    priority: Literal["baixa", "media", "alta"] = "media"
    dueDate: date | None = None


class ActivityUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=180)
    description: str | None = Field(default=None, max_length=5000)
    status: Literal["todo", "in_progress", "done"] | None = None
    priority: Literal["baixa", "media", "alta"] | None = None
    dueDate: date | None = None


_ACTIVITY_STATUSES = {"todo", "in_progress", "done"}


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


@app.get("/activities")
@app.get("/api/activities")
@app.get("/k1/lex/activities")
def list_activities(status: Optional[str] = None, token: dict = Depends(verify_token), db: Session = Depends(get_db)):
    user_id, tenant_id = _activity_owner(token)
    if status is not None and status not in _ACTIVITY_STATUSES:
        raise HTTPException(400, "Status de atividade inválido")
    query = db.query(Activity).filter(Activity.user_id == user_id, Activity.tenant_id == tenant_id)
    if status:
        query = query.filter(Activity.status == status)
    return [_activity_to_dict(row) for row in query.order_by(Activity.created_at.desc()).all()]


@app.post("/activities", status_code=201)
@app.post("/api/activities", status_code=201)
@app.post("/k1/lex/activities", status_code=201)
def create_activity(body: ActivityCreate, token: dict = Depends(verify_token), db: Session = Depends(get_db)):
    user_id, tenant_id = _activity_owner(token)
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


@app.put("/activities/{activity_id}")
@app.put("/api/activities/{activity_id}")
@app.put("/k1/lex/activities/{activity_id}")
def update_activity(activity_id: str, body: ActivityUpdate, token: dict = Depends(verify_token), db: Session = Depends(get_db)):
    user_id, tenant_id = _activity_owner(token)
    row = db.query(Activity).filter(
        Activity.id == activity_id,
        Activity.user_id == user_id,
        Activity.tenant_id == tenant_id,
    ).first()
    if not row:
        raise HTTPException(404, "Atividade não encontrada")
    for api_name, value in body.model_dump(exclude_unset=True).items():
        if api_name != "dueDate" and value is None:
            raise HTTPException(400, f"O campo {api_name} não pode ser nulo")
        column = "due_date" if api_name == "dueDate" else api_name
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


@app.delete("/activities/{activity_id}")
@app.delete("/api/activities/{activity_id}")
@app.delete("/k1/lex/activities/{activity_id}")
def delete_activity(activity_id: str, token: dict = Depends(verify_token), db: Session = Depends(get_db)):
    user_id, tenant_id = _activity_owner(token)
    row = db.query(Activity).filter(
        Activity.id == activity_id,
        Activity.user_id == user_id,
        Activity.tenant_id == tenant_id,
    ).first()
    if not row:
        raise HTTPException(404, "Atividade não encontrada")
    db.delete(row)
    db.commit()
    return {"ok": True}
