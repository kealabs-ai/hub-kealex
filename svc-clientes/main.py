import os, uuid
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from jose import jwt, JWTError
from sqlalchemy import create_engine, Column, String, DateTime, Text
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

class Cliente(Base):
    __tablename__ = "clientes"
    id            = Column(String(36),  primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id     = Column(String(36),  nullable=False)
    advogado_id   = Column(String(36),  nullable=False)   # usuario com role=advogado responsável
    nome          = Column(String(255), nullable=False)
    email         = Column(String(255), nullable=False)
    telefone      = Column(String(50),  nullable=True)
    cpf_cnpj      = Column(String(20),  nullable=True)
    endereco      = Column(String(500), nullable=True)
    observacoes   = Column(Text,        nullable=True)
    created_at    = Column(DateTime,    default=datetime.utcnow)
    updated_at    = Column(DateTime,    default=datetime.utcnow, onupdate=datetime.utcnow)

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

def require_admin_or_advogado(payload=Depends(verify_token)):
    if payload.get("role") not in ("admin", "advogado"):
        raise HTTPException(403, "Acesso negado")
    return payload

app = FastAPI(title="svc-clientes")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
def health():
    return {"status": "ok", "service": "svc-clientes"}

class ClienteIn(BaseModel):
    nome:        str
    email:       EmailStr
    telefone:    Optional[str] = None
    cpfCnpj:     Optional[str] = None
    endereco:    Optional[str] = None
    observacoes: Optional[str] = None

class ClienteUpdate(BaseModel):
    id:          str
    nome:        Optional[str]      = None
    email:       Optional[EmailStr] = None
    telefone:    Optional[str]      = None
    cpfCnpj:     Optional[str]      = None
    endereco:    Optional[str]      = None
    observacoes: Optional[str]      = None

class ClienteGetIn(BaseModel):
    id: str

class ClienteDeleteIn(BaseModel):
    id: str

def _to_dict(c: Cliente):
    return {
        "id": c.id, "tenantId": c.tenant_id, "advogadoId": c.advogado_id,
        "nome": c.nome, "email": c.email, "telefone": c.telefone,
        "cpfCnpj": c.cpf_cnpj, "endereco": c.endereco, "observacoes": c.observacoes,
        "createdAt": c.created_at.isoformat(), "updatedAt": c.updated_at.isoformat(),
    }

@app.get("/v1/lex/clientes")
def list_clientes(db: Session = Depends(get_db), payload=Depends(require_admin_or_advogado)):
    tid  = payload.get("tenant_id") or payload.get("sub")
    role = payload.get("role")
    uid  = payload.get("sub")
    q = db.query(Cliente).filter_by(tenant_id=tid)
    if role == "advogado":
        q = q.filter_by(advogado_id=uid)
    return [_to_dict(c) for c in q.all()]

@app.post("/v1/lex/clientes/get")
def get_cliente(body: ClienteGetIn, db: Session = Depends(get_db), payload=Depends(require_admin_or_advogado)):
    tid = payload.get("tenant_id") or payload.get("sub")
    c = db.query(Cliente).filter_by(id=body.id, tenant_id=tid).first()
    if not c:
        raise HTTPException(404, "Não encontrado")
    return _to_dict(c)

@app.post("/v1/lex/clientes", status_code=201)
def create_cliente(body: ClienteIn, db: Session = Depends(get_db), payload=Depends(require_admin_or_advogado)):
    tid = payload.get("tenant_id") or payload.get("sub")
    uid = payload.get("sub")
    if db.query(Cliente).filter_by(email=body.email, tenant_id=tid).first():
        raise HTTPException(409, "Email já cadastrado")
    c = Cliente(
        tenant_id=tid, advogado_id=uid,
        nome=body.nome, email=body.email, telefone=body.telefone,
        cpf_cnpj=body.cpfCnpj, endereco=body.endereco, observacoes=body.observacoes,
    )
    db.add(c); db.commit(); db.refresh(c)
    return _to_dict(c)

@app.post("/v1/lex/clientes/update")
def update_cliente(body: ClienteUpdate, db: Session = Depends(get_db), payload=Depends(require_admin_or_advogado)):
    tid = payload.get("tenant_id") or payload.get("sub")
    c = db.query(Cliente).filter_by(id=body.id, tenant_id=tid).first()
    if not c:
        raise HTTPException(404, "Não encontrado")
    data = body.model_dump(exclude_none=True, exclude={"id"})
    if "cpfCnpj" in data:
        c.cpf_cnpj = data.pop("cpfCnpj")
    for k, v in data.items():
        setattr(c, k, v)
    c.updated_at = datetime.utcnow()
    db.commit(); db.refresh(c)
    return _to_dict(c)

@app.post("/v1/lex/clientes/delete")
def delete_cliente(body: ClienteDeleteIn, db: Session = Depends(get_db), payload=Depends(require_admin_or_advogado)):
    tid = payload.get("tenant_id") or payload.get("sub")
    c = db.query(Cliente).filter_by(id=body.id, tenant_id=tid).first()
    if not c:
        raise HTTPException(404, "Não encontrado")
    db.delete(c); db.commit()
    return {"ok": True}
