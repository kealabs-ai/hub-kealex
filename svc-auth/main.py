import os, uuid, enum
from datetime import datetime, timedelta
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

DATABASE_URL        = _get_database_url(
    "mysql+pymysql://u549746795_kealex:Sally2026%40%21%40@srv1078.hstgr.io:3306/u549746795_kealex"
)
SECRET_KEY          = os.getenv("SECRET_KEY", "changeme-secret-key")
ALGORITHM           = "HS256"
TOKEN_EXPIRE_MINUTES = 60 * 8

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

def _verify(p: str, h: str) -> bool:
    try:
        return bcrypt.checkpw(p.encode(), h.encode())
    except Exception:
        return False

class Base(DeclarativeBase): pass

class RoleEnum(str, enum.Enum):
    admin    = "admin"
    advogado = "advogado"
    cliente  = "cliente"

class Tenant(Base):
    __tablename__ = "tenants"
    id         = Column(String(36),  primary_key=True, default=lambda: str(uuid.uuid4()))
    nome       = Column(String(255), nullable=False)
    slug       = Column(String(100), unique=True, nullable=False)
    ativo      = Column(Boolean,     default=True)
    created_at = Column(DateTime,    default=datetime.utcnow)
    updated_at = Column(DateTime,    default=datetime.utcnow, onupdate=datetime.utcnow)

class Usuario(Base):
    __tablename__ = "usuarios"
    id         = Column(String(36),  primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id  = Column(String(36),  nullable=False)
    nome       = Column(String(255), nullable=False)
    email      = Column(String(255), nullable=False)
    senha_hash = Column(String(255), nullable=False)
    role       = Column(SAEnum(RoleEnum, name="role_enum_auth"), nullable=False)
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

def _seed():
    try:
        with SessionLocal() as db:
            tenant = db.query(Tenant).filter_by(slug="kealex").first()
            if not tenant:
                tenant = Tenant(nome="Kealex", slug="kealex")
                db.add(tenant)
                db.flush()
            
            # Verificar se já existe um usuário admin com este email (globalmente)
            admin = db.query(Usuario).filter_by(email="admin@kealex.com").first()
            if not admin:
                admin = Usuario(tenant_id=tenant.id, nome="Admin Kealex",
                               email="admin@kealex.com", senha_hash=_hash("admin123"),
                               role=RoleEnum.admin)
                db.add(admin)
                db.commit()
            else:
                # Atualizar tenant_id se estiver vazio e atualizar senha se necessário
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
        # Ignorar erros de seed - o usuário pode já existir

_seed()

app = FastAPI(title="svc-auth")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class LoginIn(BaseModel):
    email: EmailStr
    senha: str

class AuthUser(BaseModel):
    nome:        str
    role:        str
    tenantId:    str
    accessToken: str

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

@app.get("/health")
def health_simple():
    return {"status": "healthy", "service": "svc-auth"}

@app.get("/k1/lex/health")
def health():
    return {"status": "ok", "service": "svc-auth"}
