import os, uuid, enum
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
import bcrypt
from jose import jwt, JWTError
from sqlalchemy import create_engine, Column, String, Boolean, DateTime, Enum as SAEnum, Text, Integer, Numeric
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

def _get_database_url(default: str) -> str:
    raw = os.getenv("DATABASE_URL")
    if raw is None or raw.strip().lower() in ("", "null", "none"):
        return default
    return raw.strip()

DATABASE_URL = _get_database_url(
    "mysql+pymysql://u549746795_kealex:Sally2026%40%21%40@srv1078.hstgr.io:3306/u549746795_kealex"
)
SECRET_KEY = os.getenv("SECRET_KEY", "changeme-secret-key")
ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 60 * 8

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=280,
    pool_size=5,
    max_overflow=10,
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
bearer = HTTPBearer()

def _hash(p: str) -> str:
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()

def _verify(p: str, h: str) -> bool:
    try:
        return bcrypt.checkpw(p.encode(), h.encode())
    except Exception:
        return False

class Base(DeclarativeBase): pass

# Enums
class RoleEnum(str, enum.Enum):
    admin = "admin"
    advogado = "advogado"
    cliente = "cliente"

class StatusEnum(str, enum.Enum):
    ativo = "ativo"
    arquivado = "arquivado"
    encerrado = "encerrado"

# Models
class Tenant(Base):
    __tablename__ = "tenants"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    nome = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False)
    nome = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    senha_hash = Column(String(255), nullable=False)
    role = Column(SAEnum(RoleEnum, name="role_enum_auth"), nullable=False)
    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Cliente(Base):
    __tablename__ = "clientes"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False)
    advogado_id = Column(String(36), nullable=False)
    nome = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    telefone = Column(String(50), nullable=True)
    cpf_cnpj = Column(String(20), nullable=True)
    endereco = Column(String(500), nullable=True)
    observacoes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Processo(Base):
    __tablename__ = "processos"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False)
    user_id = Column(String(36), nullable=False)
    escritorio_id = Column(String(36), nullable=True)
    numero = Column(String(100), nullable=False)
    titulo = Column(String(255), nullable=False)
    descricao = Column(String(1000), default="")
    status = Column(SAEnum(StatusEnum, name="status_processo_enum"), default=StatusEnum.ativo)
    advogado_id = Column(String(36), nullable=False)
    cliente_id = Column(String(36), nullable=False)
    vara = Column(String(255), default="")
    tribunal = Column(String(255), default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

def _init_db():
    try:
        Base.metadata.create_all(engine)
        try:
            with SessionLocal() as db:
                tenant = db.query(Tenant).filter_by(slug="kealex").first()
                if not tenant:
                    tenant = Tenant(nome="Kealex", slug="kealex")
                    db.add(tenant)
                    db.flush()
                
                admin = db.query(Usuario).filter_by(email="admin@kealex.com").first()
                if not admin:
                    admin = Usuario(tenant_id=tenant.id, nome="Admin Kealex",
                                   email="admin@kealex.com", senha_hash=_hash("admin123"),
                                   role=RoleEnum.admin)
                    db.add(admin)
                    db.commit()
                else:
                    updated = False
                    if not admin.tenant_id or admin.tenant_id == "":
                        admin.tenant_id = tenant.id
                        updated = True
                    if not admin.senha_hash.startswith("$2b$"):
                        admin.senha_hash = _hash("admin123")
                        updated = True
                    if updated:
                        db.commit()
        except Exception as e:
            print(f"Seed error (ignorando): {e}")
    except Exception as e:
        print(f"Database init error (ignorando): {e}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def _make_token(user: Usuario) -> str:
    exp = datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": user.id, "role": user.role, "tenant_id": user.tenant_id, "exp": exp},
        SECRET_KEY, ALGORITHM
    )

def verify_token(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    try:
        return jwt.decode(creds.credentials, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(401, "Token inválido")

# Helper functions
def _processo_to_dict(p: Processo, cliente: Cliente = None):
    return {
        "id": p.id, "tenantId": p.tenant_id, "userId": p.user_id, "escritorioId": p.escritorio_id,
        "numero": p.numero, "titulo": p.titulo, "descricao": p.descricao, "status": p.status,
        "advogadoId": p.advogado_id, "clienteId": p.cliente_id,
        "clienteNome": cliente.nome if cliente else None,
        "clienteEmail": cliente.email if cliente else None,
        "vara": p.vara, "tribunal": p.tribunal,
        "createdAt": p.created_at.isoformat(), "updatedAt": p.updated_at.isoformat()
    }

def _enrich_processos(db: Session, processos: list[Processo]):
    ids = list({p.cliente_id for p in processos})
    clientes = {c.id: c for c in db.query(Cliente).filter(Cliente.id.in_(ids)).all()}
    return [_processo_to_dict(p, clientes.get(p.cliente_id)) for p in processos]

# Pydantic models
class LoginIn(BaseModel):
    email: EmailStr
    senha: str

class AuthUser(BaseModel):
    nome: str
    role: str
    tenantId: str
    accessToken: str

class ProcessoIn(BaseModel):
    numero: str
    titulo: str
    descricao: str = ""
    clienteId: str
    vara: str = ""
    tribunal: str = ""
    escritorioId: Optional[str] = None

class ProcessoGetIn(BaseModel):
    id: str

class ProcessoUpdate(BaseModel):
    id: str
    numero: Optional[str] = None
    titulo: Optional[str] = None
    descricao: Optional[str] = None
    status: Optional[StatusEnum] = None
    vara: Optional[str] = None
    tribunal: Optional[str] = None

class ProcessoDeleteIn(BaseModel):
    id: str

app = FastAPI(title="HubKealex API")
app.add_middleware(CORSMiddleware, allow_origins=["*", "https://darkorange-raven-554257.hostingersite.com"], allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def startup_event():
    _init_db()

# Health endpoints
@app.get("/health")
def health_simple():
    return {"status": "healthy", "service": "hubkealex"}

@app.get("/k1/lex/health")
def health():
    return {"status": "ok", "service": "hubkealex"}

# Auth endpoints
@app.post("/k1/lex/auth/login", response_model=AuthUser)
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.query(Usuario).filter_by(email=body.email, ativo=True).first()
    if not user or not _verify(body.senha, user.senha_hash):
        raise HTTPException(401, "Credenciais inválidas")
    return AuthUser(nome=user.nome, role=user.role,
                    tenantId=user.tenant_id, accessToken=_make_token(user))

@app.get("/k1/lex/auth/me")
def me(payload=Depends(verify_token)):
    return payload

# Processos endpoints
@app.get("/k1/lex/processos")
def list_processos(db: Session = Depends(get_db), payload=Depends(verify_token)):
    role, uid, tid = payload.get("role"), payload.get("sub"), payload.get("tenant_id")
    q = db.query(Processo).filter_by(tenant_id=tid)
    
    if role == "cliente":
        q = q.filter_by(cliente_id=uid)
    elif role == "advogado":
        q = q.filter_by(advogado_id=uid)
    
    return _enrich_processos(db, q.all())

@app.post("/k1/lex/processos/get")
def get_processo(body: ProcessoGetIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    p = db.query(Processo).filter_by(id=body.id, tenant_id=tenant_id).first()
    if not p:
        raise HTTPException(404, "Não encontrado")
    cliente = db.query(Cliente).filter_by(id=p.cliente_id).first()
    return _processo_to_dict(p, cliente)

@app.post("/k1/lex/processos", status_code=201)
def create_processo(body: ProcessoIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    cliente = db.query(Cliente).filter_by(id=body.clienteId, tenant_id=tenant_id).first()
    if not cliente:
        raise HTTPException(404, "Cliente não encontrado")
    p = Processo(tenant_id=tenant_id, user_id=payload["sub"], escritorio_id=body.escritorioId,
                 numero=body.numero, titulo=body.titulo, descricao=body.descricao,
                 advogado_id=payload["sub"], cliente_id=body.clienteId, vara=body.vara, tribunal=body.tribunal)
    db.add(p); db.commit(); db.refresh(p)
    return _processo_to_dict(p, cliente)

@app.post("/k1/lex/processos/update")
def update_processo(body: ProcessoUpdate, db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    p = db.query(Processo).filter_by(id=body.id, tenant_id=tenant_id).first()
    if not p:
        raise HTTPException(404, "Não encontrado")
    for k, v in body.model_dump(exclude_none=True, exclude={"id"}).items():
        setattr(p, k, v)
    p.updated_at = datetime.utcnow()
    db.commit(); db.refresh(p)
    cliente = db.query(Cliente).filter_by(id=p.cliente_id).first()
    return _processo_to_dict(p, cliente)

@app.post("/k1/lex/processos/delete")
def delete_processo(body: ProcessoDeleteIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    p = db.query(Processo).filter_by(id=body.id, tenant_id=tenant_id).first()
    if not p:
        raise HTTPException(404, "Não encontrado")
    db.delete(p); db.commit()
    return {"ok": True}

# Basic endpoints for other services (placeholder endpoints)
@app.get("/k1/lex/clientes")
def list_clientes(payload=Depends(verify_token)):
    return {"message": "Clientes endpoint - implementar conforme necessário"}

@app.get("/k1/lex/documentos")
def list_documentos(payload=Depends(verify_token)):
    return {"message": "Documentos endpoint - implementar conforme necessário"}

@app.get("/k1/lex/financeiro")
def list_financeiro(payload=Depends(verify_token)):
    return {"message": "Financeiro endpoint - implementar conforme necessário"}

@app.get("/k1/lex/prazos")
def list_prazos(payload=Depends(verify_token)):
    return {"message": "Prazos endpoint - implementar conforme necessário"}

@app.get("/k1/lex/usuarios")
def list_usuarios(payload=Depends(verify_token)):
    return {"message": "Usuários endpoint - implementar conforme necessário"}

@app.get("/k1/lex/escritorios")
def list_escritorios(payload=Depends(verify_token)):
    return {"message": "Escritórios endpoint - implementar conforme necessário"}

@app.get("/k1/lex/configuracoes/geral")
def get_configuracoes_geral(payload=Depends(verify_token)):
    return {"message": "Configurações gerais - implementar conforme necessário"}
