import os, uuid, enum
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
import bcrypt
from jose import jwt, JWTError
from sqlalchemy import create_engine, Column, String, Boolean, DateTime, Enum as SAEnum
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

def _hash(p: str) -> str:
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()

class Base(DeclarativeBase): pass

class RoleEnum(str, enum.Enum):
    admin    = "admin"
    advogado = "advogado"
    cliente  = "cliente"

class Usuario(Base):
    __tablename__ = "usuarios"
    id           = Column(String(36),  primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id    = Column(String(36),  nullable=False)
    escritorio_id = Column(String(36), nullable=True)
    nome         = Column(String(255), nullable=False)
    email        = Column(String(255), nullable=False)
    senha_hash   = Column(String(255), nullable=False)
    role         = Column(SAEnum(RoleEnum, name="role_enum_auth"), nullable=False)
    ativo        = Column(Boolean,     default=True)
    created_at   = Column(DateTime,    default=datetime.utcnow)
    updated_at   = Column(DateTime,    default=datetime.utcnow, onupdate=datetime.utcnow)

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

app = FastAPI(title="svc-usuarios")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
def health():
    return {"status": "ok", "service": "svc-usuarios"}

class UsuarioIn(BaseModel):
    nome:         str
    email:        EmailStr
    senha:        str
    role:         RoleEnum
    escritorioId: Optional[str] = None

class UsuarioListIn(BaseModel):
    role: Optional[RoleEnum] = None

class UsuarioGetIn(BaseModel):
    id: str

class UsuarioUpdate(BaseModel):
    id:           str
    nome:         Optional[str]      = None
    email:        Optional[EmailStr] = None
    senha:        Optional[str]      = None
    role:         Optional[RoleEnum] = None
    ativo:        Optional[bool]     = None
    escritorioId: Optional[str]      = None

class UsuarioDeleteIn(BaseModel):
    id: str

def _to_dict(u: Usuario):
    return {
        "id": u.id, "tenantId": u.tenant_id, "escritorioId": u.escritorio_id,
        "nome": u.nome, "email": u.email, "role": u.role, "ativo": u.ativo,
        "createdAt": u.created_at.isoformat(), "updatedAt": u.updated_at.isoformat()
    }

@app.get("/v1/lex/usuarios")
def list_usuarios(db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    return [_to_dict(u) for u in db.query(Usuario).filter_by(tenant_id=tenant_id).all()]

@app.post("/v1/lex/usuarios/list")
def list_usuarios_filtered(body: UsuarioListIn, db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    q = db.query(Usuario).filter_by(tenant_id=tenant_id)
    if body.role:
        q = q.filter_by(role=body.role)
    return [_to_dict(u) for u in q.all()]

@app.post("/v1/lex/usuarios/get")
def get_usuario(body: UsuarioGetIn, db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    u = db.query(Usuario).filter_by(id=body.id, tenant_id=tenant_id).first()
    if not u:
        raise HTTPException(404, "Não encontrado")
    return _to_dict(u)

@app.post("/v1/lex/usuarios", status_code=201)
def create_usuario(body: UsuarioIn, db: Session = Depends(get_db), payload=Depends(require_admin)):
    tid = payload.get("tenant_id") or payload.get("sub")
    if db.query(Usuario).filter_by(email=body.email, tenant_id=tid).first():
        raise HTTPException(409, "Email já cadastrado")
    u = Usuario(tenant_id=tid, escritorio_id=body.escritorioId, nome=body.nome, email=body.email,
                senha_hash=_hash(body.senha), role=body.role)
    db.add(u); db.commit(); db.refresh(u)
    return _to_dict(u)

@app.post("/v1/lex/usuarios/update")
def update_usuario(body: UsuarioUpdate, db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    u = db.query(Usuario).filter_by(id=body.id, tenant_id=tenant_id).first()
    if not u:
        raise HTTPException(404, "Não encontrado")
    data = body.model_dump(exclude_none=True, exclude={"id"})
    if "senha" in data:
        u.senha_hash = _hash(data.pop("senha"))
    if "escritorioId" in data:
        u.escritorio_id = data.pop("escritorioId")
    for k, v in data.items():
        setattr(u, k, v)
    u.updated_at = datetime.utcnow()
    db.commit(); db.refresh(u)
    return _to_dict(u)

@app.post("/v1/lex/usuarios/delete")
def delete_usuario(body: UsuarioDeleteIn, db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    u = db.query(Usuario).filter_by(id=body.id, tenant_id=tenant_id).first()
    if not u:
        raise HTTPException(404, "Não encontrado")
    db.delete(u); db.commit()
    return {"ok": True}
