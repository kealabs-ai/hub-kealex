import os, uuid
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import jwt, JWTError
from sqlalchemy import create_engine, Column, String, Boolean, DateTime
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

def _get_database_url(default: str) -> str:
    raw = os.getenv("DATABASE_URL")
    if raw is None or raw.strip().lower() in ("", "null", "none"):
        return default
    return raw.strip()

DATABASE_URL = _get_database_url(
    "mysql+pymysql://u549746795_kealex:Sally2026%40%21%40@srv1078.hstgr.io:3306/u549746795_kealex"
)
SECRET_KEY   = os.getenv("SECRET_KEY", "changeme-secret-key")
ALGORITHM    = "HS256"

engine       = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=280,
    pool_size=5,
    max_overflow=10,
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
bearer       = HTTPBearer()

class Base(DeclarativeBase): pass

class Escritorio(Base):
    __tablename__ = "escritorios"
    id         = Column(String(36),  primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id  = Column(String(36),  nullable=False)
    nome       = Column(String(255), nullable=False)
    cnpj       = Column(String(18),  nullable=True)
    endereco   = Column(String(500), nullable=True)
    telefone   = Column(String(20),  nullable=True)
    email      = Column(String(255), nullable=True)
    ativo      = Column(Boolean,     default=True)
    created_at = Column(DateTime,    default=datetime.utcnow)
    updated_at = Column(DateTime,    default=datetime.utcnow, onupdate=datetime.utcnow)

Base.metadata.create_all(engine)

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
        return jwt.decode(creds.credentials, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(401, "Token inválido")

def require_admin(payload=Depends(verify_token)):
    if payload.get("role") != "admin":
        raise HTTPException(403, "Acesso negado")
    return payload

app = FastAPI(title="svc-escritorios")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class EscritorioIn(BaseModel):
    nome:     str
    cnpj:     Optional[str] = None
    endereco: Optional[str] = None
    telefone: Optional[str] = None
    email:    Optional[str] = None

class EscritorioGetIn(BaseModel):
    id: str

class EscritorioUpdate(BaseModel):
    id:       str
    nome:     Optional[str]  = None
    cnpj:     Optional[str]  = None
    endereco: Optional[str]  = None
    telefone: Optional[str]  = None
    email:    Optional[str]  = None
    ativo:    Optional[bool] = None

class EscritorioDeleteIn(BaseModel):
    id: str

def _to_dict(e: Escritorio):
    return {
        "id": e.id, "tenantId": e.tenant_id, "nome": e.nome, "cnpj": e.cnpj,
        "endereco": e.endereco, "telefone": e.telefone, "email": e.email, "ativo": e.ativo,
        "createdAt": e.created_at.isoformat(), "updatedAt": e.updated_at.isoformat()
    }

@app.get("/escritorios")
def list_escritorios(db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    return [_to_dict(e) for e in db.query(Escritorio).filter_by(tenant_id=tenant_id).all()]

@app.post("/escritorios/get")
def get_escritorio(body: EscritorioGetIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    e = db.query(Escritorio).filter_by(id=body.id, tenant_id=tenant_id).first()
    if not e:
        raise HTTPException(404, "Não encontrado")
    return _to_dict(e)

@app.post("/escritorios", status_code=201)
def create_escritorio(body: EscritorioIn, db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    e = Escritorio(tenant_id=tenant_id, nome=body.nome, cnpj=body.cnpj,
                   endereco=body.endereco, telefone=body.telefone, email=body.email)
    db.add(e); db.commit(); db.refresh(e)
    return _to_dict(e)

@app.post("/escritorios/update")
def update_escritorio(body: EscritorioUpdate, db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    e = db.query(Escritorio).filter_by(id=body.id, tenant_id=tenant_id).first()
    if not e:
        raise HTTPException(404, "Não encontrado")
    for k, v in body.model_dump(exclude_none=True, exclude={"id"}).items():
        setattr(e, k, v)
    e.updated_at = datetime.utcnow()
    db.commit(); db.refresh(e)
    return _to_dict(e)

@app.post("/escritorios/delete")
def delete_escritorio(body: EscritorioDeleteIn, db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    e = db.query(Escritorio).filter_by(id=body.id, tenant_id=tenant_id).first()
    if not e:
        raise HTTPException(404, "Não encontrado")
    db.delete(e); db.commit()
    return {"ok": True}