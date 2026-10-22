import os, uuid, secrets
import bcrypt
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import jwt, JWTError
from sqlalchemy import create_engine, Column, String, Boolean, DateTime, Integer, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from dotenv import load_dotenv

load_dotenv()

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
        raise RuntimeError("Configure KEALEX_DB_HOST, KEALEX_DB_NAME, KEALEX_DB_USER e KEALEX_DB_PASSWORD (ou KEALEX_DATABASE_URL)")
    return make_url(raw.strip())

KEALEX_DATABASE_URL = _get_database_url()
KEALEX_SECRET_KEY   = os.getenv("KEALEX_SECRET_KEY") or os.getenv("KEALEX_JWT_SECRET")
if not KEALEX_SECRET_KEY:
    raise RuntimeError("KEALEX_SECRET_KEY ou KEALEX_JWT_SECRET precisa estar configurada no ambiente")
ALGORITHM    = "HS256"

engine       = create_engine(
    KEALEX_DATABASE_URL,
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
    limite_advogados = Column(Integer, nullable=False, default=3, server_default="3")
    codigo = Column(String(16), nullable=False, unique=True)
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
        return jwt.decode(creds.credentials, KEALEX_SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(401, "Token inválido")

def require_admin(payload=Depends(verify_token)):
    if payload.get("role") != "admin":
        raise HTTPException(403, "Acesso negado")
    return payload

app = FastAPI(title="svc-escritorios")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
def health():
    return {"status": "ok", "service": "svc-escritorios"}

class EscritorioIn(BaseModel):
    nome:     str
    cnpj:     Optional[str] = None
    endereco: Optional[str] = None
    telefone: Optional[str] = None
    email:    Optional[str] = None
    emailAcesso: Optional[str] = None
    senhaInicial: Optional[str] = None
    limiteAdvogados: int = 3

class EscritorioGetIn(BaseModel):
    id: str

class CriarAcessoIn(BaseModel):
    escritorioId: str
    emailAcesso: str
    senhaInicial: str

class EscritorioUpdate(BaseModel):
    id:       str
    nome:     Optional[str]  = None
    cnpj:     Optional[str]  = None
    endereco: Optional[str]  = None
    telefone: Optional[str]  = None
    email:    Optional[str]  = None
    ativo:    Optional[bool] = None
    limiteAdvogados: Optional[int] = None

class EscritorioDeleteIn(BaseModel):
    id: str

def _usage_for_escritorio(db: Session, escritorio_id: str):
    usage = db.execute(
        text("""
            SELECT
                COALESCE(SUM(CASE WHEN ativo = 1 AND role = 'advogado' THEN 1 ELSE 0 END), 0) AS usuarios_ativos,
                COALESCE(SUM(CASE WHEN ativo = 1 AND role = 'advogado' THEN 1 ELSE 0 END), 0) AS advogados_ativos
            FROM usuarios
            WHERE escritorio_id = :eid
        """),
        {"eid": escritorio_id},
    ).mappings().first()
    return int(usage["usuarios_ativos"] or 0), int(usage["advogados_ativos"] or 0)


def _to_dict(e: Escritorio, usuarios_ativos: int = 0, advogados_ativos: int = 0, acesso_configurado: bool = False):
    return {
        "id": e.id, "tenantId": e.tenant_id, "nome": e.nome, "cnpj": e.cnpj,
        "endereco": e.endereco, "telefone": e.telefone, "email": e.email, "ativo": e.ativo,
        "limiteAdvogados": e.limite_advogados, "codigo": e.codigo,
        "acessoConfigurado": acesso_configurado,
        "usuariosAtivos": usuarios_ativos, "advogadosAtivos": advogados_ativos,
        "createdAt": e.created_at.isoformat(), "updatedAt": e.updated_at.isoformat()
    }

@app.get("/v1/lex/escritorios")
def list_escritorios(db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    query = db.query(Escritorio).filter_by(tenant_id=tenant_id)
    if payload.get("role") == "escritorio":
        query = query.filter_by(id=payload.get("escritorio_id"))
    escritorios = query.all()
    result = []
    for escritorio in escritorios:
        usuarios_ativos, advogados_ativos = _usage_for_escritorio(db, escritorio.id)
        access = db.execute(text("SELECT id FROM usuarios WHERE escritorio_id = :eid AND tenant_id = :tid AND role = 'escritorio' LIMIT 1"), {"eid": escritorio.id, "tid": tenant_id}).first()
        result.append(_to_dict(escritorio, usuarios_ativos, advogados_ativos, bool(access)))
    return result

@app.post("/v1/lex/escritorios/get")
def get_escritorio(body: EscritorioGetIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    query = db.query(Escritorio).filter_by(id=body.id, tenant_id=tenant_id)
    if payload.get("role") == "escritorio":
        query = query.filter_by(id=payload.get("escritorio_id"))
    e = query.first()
    if not e:
        raise HTTPException(404, "Não encontrado")
    usuarios_ativos, advogados_ativos = _usage_for_escritorio(db, e.id)
    access = db.execute(text("SELECT id FROM usuarios WHERE escritorio_id = :eid AND tenant_id = :tid AND role = 'escritorio' LIMIT 1"), {"eid": e.id, "tid": tenant_id}).first()
    return _to_dict(e, usuarios_ativos, advogados_ativos, bool(access))

@app.post("/v1/lex/escritorios/criar-acesso", status_code=201)
def create_escritorio_access(body: CriarAcessoIn, db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    if len(body.senhaInicial) < 6:
        raise HTTPException(400, "A senha inicial precisa ter pelo menos 6 caracteres")
    office = db.query(Escritorio).filter_by(id=body.escritorioId, tenant_id=tenant_id).first()
    if not office:
        raise HTTPException(404, "Escritório não encontrado")
    if db.execute(text("SELECT id FROM usuarios WHERE escritorio_id = :eid AND tenant_id = :tid AND role = 'escritorio'"), {"eid": office.id, "tid": tenant_id}).first():
        raise HTTPException(409, "Este escritório já possui credenciais de acesso")
    if db.execute(text("SELECT id FROM usuarios WHERE email = :email"), {"email": body.emailAcesso}).first():
        raise HTTPException(409, "E-mail já cadastrado")
    db.execute(text("""
        INSERT INTO usuarios (id, tenant_id, escritorio_id, nome, email, senha_hash, role, ativo, created_at, updated_at)
        VALUES (:id, :tenant_id, :escritorio_id, :nome, :email, :senha_hash, 'escritorio', 1, :now, :now)
    """), {
        "id": str(uuid.uuid4()), "tenant_id": tenant_id, "escritorio_id": office.id,
        "nome": office.nome, "email": body.emailAcesso,
        "senha_hash": bcrypt.hashpw(body.senhaInicial.encode(), bcrypt.gensalt()).decode(), "now": datetime.utcnow(),
    })
    db.commit()
    return {"ok": True, "escritorioId": office.id, "email": body.emailAcesso}

@app.post("/v1/lex/escritorios", status_code=201)
def create_escritorio(body: EscritorioIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    if payload.get("role") == "admin":
        if not body.emailAcesso or not body.senhaInicial:
            raise HTTPException(400, "Informe o e-mail e a senha inicial da conta do escritÃ³rio")
        if len(body.senhaInicial) < 6:
            raise HTTPException(400, "A senha inicial precisa ter pelo menos 6 caracteres")
        if body.limiteAdvogados < 1:
            raise HTTPException(400, "O limite de advogados precisa ser maior que zero")
        if db.execute(text("SELECT id FROM usuarios WHERE email = :email"), {"email": body.emailAcesso}).first():
            raise HTTPException(409, "E-mail jÃ¡ cadastrado")
    if payload.get("role") != "admin":
        if payload.get("role") != "advogado":
            raise HTTPException(403, "Acesso negado")
        tenant = db.execute(
            text("SELECT plano, trial_expires_at FROM tenants WHERE id = :tid"),
            {"tid": tenant_id},
        ).mappings().first()
        if not tenant or tenant["plano"] != "trial":
            raise HTTPException(403, "A criação de escritório pelo titular está disponível durante o trial")
        expires_at = tenant["trial_expires_at"]
        if expires_at and expires_at < datetime.utcnow():
            raise HTTPException(403, "Trial expirado. Assine um plano para criar o escritório")
        if db.query(Escritorio).filter_by(tenant_id=tenant_id).first():
            raise HTTPException(403, "Este tenant já possui um escritório cadastrado")
    codigo = None
    for _ in range(10):
        candidate = "KX-" + secrets.token_hex(6).upper()
        exists = db.execute(text("SELECT id FROM escritorios WHERE codigo = :codigo"), {"codigo": candidate}).first()
        if not exists:
            codigo = candidate
            break
    if not codigo:
        raise HTTPException(503, "Não foi possível gerar um código para o escritório. Tente novamente.")
    e = Escritorio(tenant_id=tenant_id, codigo=codigo, nome=body.nome, cnpj=body.cnpj,
                   endereco=body.endereco, telefone=body.telefone, email=body.email,
                   limite_advogados=body.limiteAdvogados if payload.get("role") == "admin" else 3)
    db.add(e); db.flush()
    if payload.get("role") == "admin":
        db.execute(text("""
            INSERT INTO usuarios (id, tenant_id, escritorio_id, nome, email, senha_hash, role, ativo, created_at, updated_at)
            VALUES (:id, :tenant_id, :escritorio_id, :nome, :email, :senha_hash, 'escritorio', 1, :now, :now)
        """), {
            "id": str(uuid.uuid4()), "tenant_id": tenant_id, "escritorio_id": e.id,
            "nome": body.nome, "email": body.emailAcesso,
            "senha_hash": bcrypt.hashpw(body.senhaInicial.encode(), bcrypt.gensalt()).decode(), "now": datetime.utcnow(),
        })
    db.commit(); db.refresh(e)
    return _to_dict(e)

@app.post("/v1/lex/escritorios/update")
def update_escritorio(body: EscritorioUpdate, db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    e = db.query(Escritorio).filter_by(id=body.id, tenant_id=tenant_id).first()
    if not e:
        raise HTTPException(404, "Não encontrado")
    data = body.model_dump(exclude_none=True, exclude={"id"})
    limite_advogados = data.pop("limiteAdvogados", None)
    if limite_advogados is not None:
        if limite_advogados < 1:
            raise HTTPException(400, "O limite de advogados precisa ser maior que zero")
        e.limite_advogados = limite_advogados
    for k, v in data.items():
        setattr(e, k, v)
    e.updated_at = datetime.utcnow()
    db.commit(); db.refresh(e)
    usuarios_ativos, advogados_ativos = _usage_for_escritorio(db, e.id)
    return _to_dict(e, usuarios_ativos, advogados_ativos)

class MembroIn(BaseModel):
    usuarioId: str
    escritorioId: Optional[str] = None  # None = desassociar

@app.post("/v1/lex/escritorios/delete")
def delete_escritorio(body: EscritorioDeleteIn, db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    e = db.query(Escritorio).filter_by(id=body.id, tenant_id=tenant_id).first()
    if not e:
        raise HTTPException(404, "Não encontrado")
    db.delete(e); db.commit()
    return {"ok": True}

@app.post("/v1/lex/escritorios/associar-membro")
def associar_membro(body: MembroIn, db: Session = Depends(get_db), payload=Depends(require_admin)):
    """Associa ou desassocia um usuário a um escritório, respeitando a quota."""
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user = db.execute(
        text("SELECT id, escritorio_id, ativo FROM usuarios WHERE id = :uid AND tenant_id = :tid"),
        {"uid": body.usuarioId, "tid": tenant_id},
    ).mappings().first()
    if not user:
        raise HTTPException(404, "Usuário não encontrado")

    if body.escritorioId:
        office = db.execute(
            text("SELECT limite_advogados FROM escritorios WHERE id = :eid AND tenant_id = :tid FOR UPDATE"),
            {"eid": body.escritorioId, "tid": tenant_id},
        ).mappings().first()
        if not office:
            raise HTTPException(404, "Escritório não encontrado")
        if user["ativo"] and user["escritorio_id"] != body.escritorioId:
            count = db.execute(
                text("SELECT COUNT(*) FROM usuarios WHERE escritorio_id = :eid AND tenant_id = :tid AND ativo = 1 AND role = 'advogado'"),
                {"eid": body.escritorioId, "tid": tenant_id},
            ).scalar_one()
            limit = int(office["limite_advogados"])
            if count >= limit:
                raise HTTPException(400, f"Limite de {limit} advogados atingido para este escritório. Entre em contato com o suporte/admin para alterar o limite.")

    db.execute(
        text("UPDATE usuarios SET escritorio_id = :eid, updated_at = NOW() WHERE id = :uid AND tenant_id = :tid"),
        {"eid": body.escritorioId, "uid": body.usuarioId, "tid": tenant_id}
    )
    db.commit()
    return {"ok": True, "usuarioId": body.usuarioId, "escritorioId": body.escritorioId,
            "modalidade": "escritorio" if body.escritorioId else "autonomo"}

class AssociarCodigoIn(BaseModel):
    codigo: str

@app.post("/v1/lex/escritorios/associar-codigo")
def associar_por_codigo(body: AssociarCodigoIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    if payload.get("role") != "advogado":
        raise HTTPException(403, "Somente advogados autônomos podem usar um código de associação")
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    usuario_id = payload.get("sub")
    codigo = body.codigo.strip().upper()
    if not codigo or len(codigo) > 16:
        raise HTTPException(400, "Informe um código de escritório válido")
    user = db.execute(text("SELECT id, escritorio_id, ativo FROM usuarios WHERE id = :uid AND tenant_id = :tid AND role = 'advogado' FOR UPDATE"), {"uid": usuario_id, "tid": tenant_id}).mappings().first()
    if not user:
        raise HTTPException(404, "Usuário não encontrado")
    if user["escritorio_id"]:
        raise HTTPException(409, "Você já está associado a um escritório. Solicite a alteração ao administrador.")
    office = db.execute(text("SELECT id, tenant_id, limite_advogados FROM escritorios WHERE codigo = :codigo AND ativo = 1 FOR UPDATE"), {"codigo": codigo}).mappings().first()
    if not office:
        raise HTTPException(404, "Código não encontrado ou escritório inativo. Confira o código com o escritório.")
    count = db.execute(text("SELECT COUNT(*) FROM usuarios WHERE escritorio_id = :eid AND ativo = 1 AND role = 'advogado'"), {"eid": office["id"]}).scalar_one()
    limit = int(office["limite_advogados"])
    if user["ativo"] and count >= limit:
        raise HTTPException(409, f"Este escritório atingiu o limite de {limit} advogados. Entre em contato com o escritório para concluir a associação manualmente ou resolver a pendência de vagas.")
    db.execute(text("UPDATE usuarios SET escritorio_id = :eid, updated_at = NOW() WHERE id = :uid AND tenant_id = :tid"), {"eid": office["id"], "uid": usuario_id, "tid": tenant_id})
    db.commit()
    return {"ok": True, "usuarioId": usuario_id, "escritorioId": office["id"], "codigo": codigo, "modalidade": "escritorio"}