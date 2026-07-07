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

# Carregar variáveis de ambiente
from dotenv import load_dotenv
load_dotenv()

# Configurações do Banco de Dados
DB_HOST = os.getenv("DB_HOST", "srv1078.hstgr.io")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "u549746795_kealex")
DB_USER = os.getenv("DB_USER", "u549746795_kealex")
DB_PASSWORD = os.getenv("DB_PASSWORD", "Sally2026@!@")

# Construir DATABASE_URL - usar URL pré-codificada se disponível
DATABASE_URL = os.getenv("DATABASE_URL", f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

# Configurações de Autenticação
SECRET_KEY = os.getenv("JWT_SECRET", "changeme-secret-key-development")
ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", "8"))
TOKEN_EXPIRE_MINUTES = JWT_EXPIRY_HOURS * 60

# Configurações de LLM API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY", "")

# Configurações de Aplicação
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
DEBUG = os.getenv("DEBUG", "true").lower() == "true"

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

class CfgIa(Base):
    __tablename__ = "cfg_ia"
    tenant_id = Column(String(36), primary_key=True)
    user_id = Column(String(36), nullable=False)
    escritorio_id = Column(String(36), nullable=True)
    provider = Column(String(50), default="cerebras")
    api_key = Column(String(255), nullable=True)
    modelo = Column(String(100), default="llama-3.3-70b")
    max_tokens = Column(Integer, default=8192)
    system_prompt = Column(Text, nullable=True)
    ativo = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AgenteIA(Base):
    __tablename__ = "agentes_ia"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False)
    escritorio_id = Column(String(36), nullable=True)
    nome = Column(String(255), nullable=False)
    descricao = Column(Text, nullable=True)
    provider = Column(String(50), nullable=False)
    api_key = Column(Text, nullable=False)
    modelo = Column(String(255), nullable=False)
    max_tokens = Column(Integer, nullable=False, default=8192)
    system_prompt = Column(Text, nullable=True)
    ativo = Column(Boolean, nullable=False, default=True)
    publico = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Documento(Base):
    __tablename__ = "documentos"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False)
    user_id = Column(String(36), nullable=False)
    escritorio_id = Column(String(36), nullable=True)
    processo_id = Column(String(36), nullable=False)
    nome = Column(String(255), nullable=False)
    tipo = Column(String(50), default="outro")
    url_arquivo = Column(String(1000), nullable=False)
    status = Column(String(50), default="pendente")
    tamanho_bytes = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Prazo(Base):
    __tablename__ = "prazos"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False)
    user_id = Column(String(36), nullable=False)
    escritorio_id = Column(String(36), nullable=True)
    processo_id = Column(String(36), nullable=False)
    titulo = Column(String(255), nullable=False)
    descricao = Column(String(1000), default="")
    data_vencimento = Column(String(10), nullable=False)
    status = Column(String(50), default="pendente")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Fase(Base):
    __tablename__ = "fases"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    processo_id = Column(String(36), nullable=False)
    label = Column(String(255), nullable=False)
    ordem = Column(Integer, nullable=False)
    status = Column(String(50), default="futura")
    data_conclusao = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Honorario(Base):
    __tablename__ = "honorarios"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False)
    user_id = Column(String(36), nullable=False)
    processo_id = Column(String(36), nullable=False)
    cliente_id = Column(String(36), nullable=False)
    descricao = Column(String(500), default="")
    valor_centavos = Column(Integer, nullable=False)
    status = Column(String(50), default="pendente")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

def _init_db():
    try:
        print(f"[INIT] Conectando ao banco: {DB_HOST}:{DB_PORT}/{DB_NAME}")
        Base.metadata.create_all(engine)
        print("[INIT] Tabelas criadas com sucesso")
        
        with SessionLocal() as db:
            tenant = db.query(Tenant).filter_by(slug="kealex").first()
            if not tenant:
                tenant = Tenant(nome="Kealex", slug="kealex")
                db.add(tenant)
                db.flush()
                print("[INIT] Tenant criado")
            
            admin = db.query(Usuario).filter_by(email="admin@kealex.com").first()
            if not admin:
                admin = Usuario(tenant_id=tenant.id, nome="Admin Kealex",
                               email="admin@kealex.com", senha_hash=_hash("admin123"),
                               role=RoleEnum.admin)
                db.add(admin)
                db.commit()
                print("[INIT] Admin criado")
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
                    print("[INIT] Admin atualizado")
        
        print("[INIT] Banco de dados inicializado com sucesso")
    except Exception as e:
        print(f"[ERRO] Database init falhou: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

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

class IaIn(BaseModel):
    provider: Optional[str] = None
    api_key: Optional[str] = None
    modelo: Optional[str] = None
    max_tokens: Optional[int] = None
    system_prompt: Optional[str] = None
    ativo: Optional[bool] = None

class AgenteIACreate(BaseModel):
    nome: str
    descricao: Optional[str] = None
    provider: str
    api_key: str
    modelo: str
    max_tokens: int = 8192
    system_prompt: Optional[str] = None
    ativo: bool = True
    publico: bool = True

class AgenteIAUpdate(BaseModel):
    nome: Optional[str] = None
    descricao: Optional[str] = None
    provider: Optional[str] = None
    api_key: Optional[str] = None
    modelo: Optional[str] = None
    max_tokens: Optional[int] = None
    system_prompt: Optional[str] = None
    ativo: Optional[bool] = None
    publico: Optional[bool] = None

def _require_admin(payload=Depends(verify_token)):
    if payload.get("role") != "admin":
        raise HTTPException(403, "Acesso negado")
    return payload

def _row(obj) -> dict:
    d = {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
    if "updated_at" in d and d["updated_at"]:
        d["updated_at"] = d["updated_at"].isoformat()
    return d

def _get_or_create_cfg_ia(db: Session, tenant_id: str, user_id: str):
    row = db.get(CfgIa, tenant_id)
    if not row:
        row = CfgIa(tenant_id=tenant_id, user_id=user_id)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row

def _upsert_cfg_ia(db: Session, tenant_id: str, user_id: str, data: dict):
    row = db.get(CfgIa, tenant_id)
    if not row:
        row = CfgIa(tenant_id=tenant_id, user_id=user_id)
        db.add(row)
    for k, v in data.items():
        setattr(row, k, v)
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return row

app = FastAPI(title="HubKealex API")
# CORS gerenciado pelo Traefik
# app.add_middleware(CORSMiddleware,
#     allow_origins=[
#         "https://darkorange-raven-554257.hostingersite.com",
#         "https://kealabs.cloud",
#         "https://www.kealabs.cloud",
#         "https://kealabs.com.br",
#         "https://www.kealabs.com.br",
#         "https://srv1023256.hstgr.cloud",
#         "http://localhost:3000",
#         "http://localhost:5173",
#     ],
#     allow_methods=["*"],
#     allow_headers=["*"],
#     allow_credentials=True,
# )

@app.on_event("startup")
def startup_event():
    _init_db()

# Health endpoints
@app.get("/health")
def health_simple():
    return {"status": "healthy", "service": "hubkealex"}

@app.get("/debug/db-status")
def debug_db_status():
    """Debug endpoint para verificar status de conexão com banco de dados"""
    try:
        with SessionLocal() as db:
            result = db.execute("SELECT 1").fetchone()
        return {
            "status": "connected",
            "database_url": f"mysql+pymysql://{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
            "host": DB_HOST,
            "port": DB_PORT,
            "database": DB_NAME
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "database_url": f"mysql+pymysql://{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
            "host": DB_HOST,
            "port": DB_PORT,
            "database": DB_NAME
        }

@app.get("/k1/lex/health")
def health():
    return {"status": "ok", "service": "hubkealex"}

# Auth endpoints
@app.post("/auth/login", response_model=AuthUser)
@app.post("/k1/lex/auth/login", response_model=AuthUser)
def login(body: LoginIn, db: Session = Depends(get_db)):
    try:
        user = db.query(Usuario).filter_by(email=body.email, ativo=True).first()
        if not user or not _verify(body.senha, user.senha_hash):
            raise HTTPException(401, "Credenciais inválidas")
        return AuthUser(nome=user.nome, role=user.role,
                        tenantId=user.tenant_id, accessToken=_make_token(user))
    except HTTPException:
        raise
    except Exception as e:
        print(f"[LOGIN_ERROR] {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Erro no login: {str(e)}")

@app.get("/auth/me")
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

@app.post("/k1/lex/processos/avancar-fase")
def avancar_fase(body: dict, db: Session = Depends(get_db), payload=Depends(verify_token)):
    processo_id = body.get("processoId")
    if not processo_id:
        raise HTTPException(400, "processoId obrigatório")
    
    tenant_id = payload.get("tenant_id")
    p = db.query(Processo).filter_by(id=processo_id, tenant_id=tenant_id).first()
    if not p:
        raise HTTPException(404, "Processo não encontrado")
    
    fases = db.query(Fase).filter_by(processo_id=processo_id).order_by(Fase.ordem).all()
    if not fases:
        raise HTTPException(400, "Nenhuma fase encontrada para este processo")
    
    fase_atual = db.query(Fase).filter_by(processo_id=processo_id, status="em_andamento").first()
    
    if not fase_atual:
        proxima_fase = fases[0]
    else:
        idx = next((i for i, f in enumerate(fases) if f.id == fase_atual.id), -1)
        if idx == -1 or idx >= len(fases) - 1:
            raise HTTPException(400, "Nenhuma próxima fase disponível")
        proxima_fase = fases[idx + 1]
    
    if fase_atual:
        fase_atual.status = "concluida"
        fase_atual.data_conclusao = datetime.utcnow()
    
    proxima_fase.status = "em_andamento"
    proxima_fase.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "ok": True,
        "faseAnterior": {"id": fase_atual.id, "label": fase_atual.label, "status": "concluida"} if fase_atual else None,
        "faseAtual": {"id": proxima_fase.id, "label": proxima_fase.label, "status": "em_andamento"}
    }

# Basic endpoints for other services (placeholder endpoints)
@app.get("/clientes")
@app.get("/k1/lex/clientes")
def list_clientes(db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    return [{"id": c.id, "tenantId": c.tenant_id, "nome": c.nome, "email": c.email} for c in db.query(Cliente).filter_by(tenant_id=tenant_id).all()]

@app.post("/clientes", status_code=201)
@app.post("/k1/lex/clientes", status_code=201)
def create_cliente(body: dict, db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    c = Cliente(id=str(uuid.uuid4()), tenant_id=tenant_id, advogado_id=payload["sub"],
                nome=body.get("nome"), email=body.get("email"))
    db.add(c); db.commit(); db.refresh(c)
    return {"id": c.id, "tenantId": c.tenant_id, "nome": c.nome, "email": c.email}

@app.get("/documentos")
@app.get("/k1/lex/documentos")
def list_documentos(db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    docs = db.query(Documento).filter_by(tenant_id=tenant_id).all()
    return [{"id": d.id, "nome": d.nome, "tipo": d.tipo, "status": d.status, "processoId": d.processo_id} for d in docs]

@app.post("/documentos", status_code=201)
@app.post("/k1/lex/documentos", status_code=201)
def create_documento(body: dict, db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    d = Documento(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        user_id=payload["sub"],
        processo_id=body.get("processoId"),
        nome=body.get("nome"),
        tipo=body.get("tipo", "outro"),
        url_arquivo=body.get("urlArquivo", ""),
        status="pendente",
        tamanho_bytes=body.get("tamanhoBytes", 0)
    )
    db.add(d)
    db.commit()
    db.refresh(d)
    return {"id": d.id, "tenantId": d.tenant_id, "nome": d.nome, "tipo": d.tipo, "status": d.status}

@app.get("/financeiro")
@app.get("/k1/lex/financeiro")
def list_financeiro(db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    honorarios = db.query(Honorario).filter_by(tenant_id=tenant_id).all()
    return [{"id": h.id, "descricao": h.descricao, "valorCentavos": h.valor_centavos, "status": h.status, "processoId": h.processo_id} for h in honorarios]

@app.post("/financeiro", status_code=201)
@app.post("/k1/lex/financeiro", status_code=201)
def create_honorario(body: dict, db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    h = Honorario(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        user_id=payload["sub"],
        processo_id=body.get("processoId"),
        cliente_id=body.get("clienteId"),
        descricao=body.get("descricao", ""),
        valor_centavos=body.get("valorCentavos", 0),
        status="pendente"
    )
    db.add(h)
    db.commit()
    db.refresh(h)
    return {"id": h.id, "tenantId": h.tenant_id, "descricao": h.descricao, "valorCentavos": h.valor_centavos, "status": h.status}

@app.get("/financeiro/dashboard")
@app.get("/k1/lex/financeiro/dashboard")
def financeiro_dashboard(db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    honorarios = db.query(Honorario).filter_by(tenant_id=tenant_id).all()
    total_pago = sum(h.valor_centavos for h in honorarios if h.status == "pago")
    total_pendente = sum(h.valor_centavos for h in honorarios if h.status == "pendente")
    total_vencido = sum(h.valor_centavos for h in honorarios if h.status == "vencido")
    return {"totalPago": total_pago, "totalPendente": total_pendente, "totalVencido": total_vencido, "totalGeral": total_pago + total_pendente + total_vencido}

@app.get("/prazos")
@app.get("/k1/lex/prazos")
def list_prazos(db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    prazos = db.query(Prazo).filter_by(tenant_id=tenant_id).all()
    return [{"id": p.id, "titulo": p.titulo, "dataVencimento": p.data_vencimento, "status": p.status, "processoId": p.processo_id} for p in prazos]

@app.post("/prazos", status_code=201)
@app.post("/k1/lex/prazos", status_code=201)
def create_prazo(body: dict, db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    p = Prazo(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        user_id=payload["sub"],
        processo_id=body.get("processoId"),
        titulo=body.get("titulo"),
        descricao=body.get("descricao", ""),
        data_vencimento=body.get("dataVencimento"),
        status="pendente"
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return {"id": p.id, "tenantId": p.tenant_id, "titulo": p.titulo, "dataVencimento": p.data_vencimento, "status": p.status}

@app.post("/prazos/vencendo")
@app.post("/k1/lex/prazos/vencendo")
def prazos_vencendo(body: dict = None, db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    dias = body.get("dias", 7) if body else 7
    from datetime import date, timedelta
    hoje = date.today().isoformat()
    limite = (date.today() + timedelta(days=dias)).isoformat()
    prazos = db.query(Prazo).filter(
        Prazo.tenant_id == tenant_id,
        Prazo.data_vencimento >= hoje,
        Prazo.data_vencimento <= limite,
        Prazo.status == "pendente"
    ).all()
    return [{"id": p.id, "titulo": p.titulo, "dataVencimento": p.data_vencimento, "diasRestantes": (date.fromisoformat(p.data_vencimento) - date.today()).days} for p in prazos]

@app.get("/usuarios")
@app.get("/k1/lex/usuarios")
def list_usuarios(db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    return [{"id": u.id, "tenantId": u.tenant_id, "nome": u.nome, "email": u.email, "role": u.role} for u in db.query(Usuario).filter_by(tenant_id=tenant_id).all()]

@app.get("/escritorios")
@app.get("/k1/lex/escritorios")
def list_escritorios(db: Session = Depends(get_db), payload=Depends(verify_token)):
    return {"data": [], "message": "Escritórios - use serviço svc-escritorios"}

@app.get("/configuracoes/geral")
@app.get("/k1/lex/configuracoes/geral")
def get_configuracoes_geral(db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    return {
        "tenantId": tenant_id,
        "theme": "light",
        "language": "pt-BR",
        "timezone": "America/Sao_Paulo",
        "notificacoes": True
    }

@app.post("/configuracoes/geral")
@app.post("/k1/lex/configuracoes/geral")
def save_configuracoes_geral(body: dict, db: Session = Depends(get_db), payload=Depends(verify_token)):
    return {"success": True, "message": "Configurações salvas", "data": body}


# IA Configuration
MODELOS_DISPONIVEIS = {
    "cerebras": ["llama-3.3-70b", "llama-3.1-70b", "llama-3.1-8b"],
    "groq": ["llama-3.3-70b-versatile", "llama-3.1-70b-versatile", "llama-3.1-8b-instant", "llama-3.2-90b-text-preview", "llama-3.2-11b-text-preview", "gemma2-9b-it"]
}

@app.get("/k1/lex/configuracoes/ia")
def get_ia(db: Session = Depends(get_db), payload=Depends(_require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    return _row(_get_or_create_cfg_ia(db, tenant_id, user_id))

@app.get("/k1/lex/configuracoes/ia/modelos")
def get_modelos_disponiveis():
    return MODELOS_DISPONIVEIS

@app.get("/k1/lex/configuracoes/ia/ativa")
def get_ia_ativa(db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    return _row(_get_or_create_cfg_ia(db, tenant_id, user_id))

@app.post("/k1/lex/configuracoes/ia")
def save_ia(body: IaIn, db: Session = Depends(get_db), payload=Depends(_require_admin)):
    data = body.model_dump(exclude_none=True)
    if "provider" in data and data["provider"] not in ["cerebras", "groq"]:
        raise HTTPException(400, "Provider invalido. Use 'cerebras' ou 'groq'")
    if "api_key" in data and data["api_key"]:
        tenant_id = payload.get("tenant_id") or payload.get("sub")
        existing = db.get(CfgIa, tenant_id)
        provider = data.get("provider") or (existing.provider if existing else "cerebras")
        if provider == "cerebras" and not data["api_key"].startswith("csk-"):
            raise HTTPException(400, "API key Cerebras deve comecar com 'csk-'")
        if provider == "groq" and not (data["api_key"].startswith("gsk-") or data["api_key"].startswith("gsk_")):
            raise HTTPException(400, "API key Groq deve comecar com 'gsk-' ou 'gsk_'")
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    return _row(_upsert_cfg_ia(db, tenant_id, user_id, data))

# Agentes IA endpoints
@app.get("/k1/lex/agentes")
def listar_agentes(db: Session = Depends(get_db), payload=Depends(_require_admin)):
    """Lista todos os agentes do tenant (apenas admin)"""
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    agentes = db.query(AgenteIA).filter(AgenteIA.tenant_id == tenant_id).order_by(AgenteIA.created_at.desc()).all()
    return [{**_row(a)} for a in agentes]

@app.get("/k1/lex/agentes/publicos")
def listar_agentes_publicos(db: Session = Depends(get_db), payload=Depends(verify_token)):
    """Lista agentes publicos e ativos (disponiveis para todos)"""
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    agentes = db.query(AgenteIA).filter(
        AgenteIA.tenant_id == tenant_id,
        AgenteIA.ativo == True,
        AgenteIA.publico == True
    ).order_by(AgenteIA.created_at.desc()).all()
    return [{**_row(a)} for a in agentes]

@app.get("/k1/lex/agentes/{agente_id}")
def buscar_agente_by_id(agente_id: str, db: Session = Depends(get_db), payload=Depends(verify_token)):
    """Busca um agente especifico por ID via GET"""
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    agente = db.query(AgenteIA).filter(
        AgenteIA.id == agente_id,
        AgenteIA.tenant_id == tenant_id
    ).first()
    
    if not agente:
        raise HTTPException(404, "Agente nao encontrado")
    
    if payload.get("role") != "admin" and not agente.publico:
        raise HTTPException(403, "Acesso negado a este agente")
    
    return _row(agente)

@app.put("/k1/lex/agentes/{agente_id}")
def atualizar_agente_by_id(agente_id: str, body: AgenteIAUpdate, db: Session = Depends(get_db), payload=Depends(_require_admin)):
    """Atualiza um agente via PUT"""
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    agente = db.query(AgenteIA).filter(
        AgenteIA.id == agente_id,
        AgenteIA.tenant_id == tenant_id
    ).first()
    
    if not agente:
        raise HTTPException(404, "Agente nao encontrado")
    
    update_data = body.model_dump(exclude_none=True)
    
    if "provider" in update_data and update_data["provider"] not in ["cerebras", "groq"]:
        raise HTTPException(400, "Provider invalido. Use 'cerebras' ou 'groq'")
    
    if "api_key" in update_data:
        provider = update_data.get("provider", agente.provider)
        if provider == "cerebras" and not update_data["api_key"].startswith("csk-"):
            raise HTTPException(400, "API key Cerebras deve comecar com 'csk-'")
        if provider == "groq" and not (update_data["api_key"].startswith("gsk-") or update_data["api_key"].startswith("gsk_")):
            raise HTTPException(400, "API key Groq deve comecar com 'gsk-' ou 'gsk_'")
    
    for field, value in update_data.items():
        if hasattr(agente, field):
            setattr(agente, field, value)
    
    agente.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(agente)
    
    return _row(agente)

@app.delete("/k1/lex/agentes/{agente_id}")
def deletar_agente_by_id(agente_id: str, db: Session = Depends(get_db), payload=Depends(_require_admin)):
    """Deleta um agente via DELETE"""
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    agente = db.query(AgenteIA).filter(
        AgenteIA.id == agente_id,
        AgenteIA.tenant_id == tenant_id
    ).first()
    
    if not agente:
        raise HTTPException(404, "Agente nao encontrado")
    
    db.delete(agente)
    db.commit()
    
    return {"ok": True}

@app.post("/k1/lex/agentes/get")
def buscar_agente(body: dict, db: Session = Depends(get_db), payload=Depends(verify_token)):
    """Busca um agente especifico"""
    agente_id = body.get("id")
    if not agente_id:
        raise HTTPException(400, "ID do agente obrigatorio")
    
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    agente = db.query(AgenteIA).filter(
        AgenteIA.id == agente_id,
        AgenteIA.tenant_id == tenant_id
    ).first()
    
    if not agente:
        raise HTTPException(404, "Agente nao encontrado")
    
    # Se nao for admin, so pode ver agentes publicos
    if payload.get("role") != "admin" and not agente.publico:
        raise HTTPException(403, "Acesso negado a este agente")
    
    return _row(agente)

@app.post("/k1/lex/agentes", status_code=201)
def criar_agente(body: AgenteIACreate, db: Session = Depends(get_db), payload=Depends(_require_admin)):
    """Cria um novo agente (apenas admin)"""
    # Validar provider
    if body.provider not in ["cerebras", "groq"]:
        raise HTTPException(400, "Provider invalido. Use 'cerebras' ou 'groq'")
    
    # Validar prefixo da API key
    if body.provider == "cerebras" and not body.api_key.startswith("csk-"):
        raise HTTPException(400, "API key Cerebras deve comecar com 'csk-'")
    if body.provider == "groq" and not (body.api_key.startswith("gsk-") or body.api_key.startswith("gsk_")):
        raise HTTPException(400, "API key Groq deve comecar com 'gsk-' ou 'gsk_'")
    
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    escritorio_id = payload.get("escritorio_id")
    
    novo_agente = AgenteIA(
        tenant_id=tenant_id,
        escritorio_id=escritorio_id,
        **body.model_dump()
    )
    
    db.add(novo_agente)
    db.commit()
    db.refresh(novo_agente)
    
    return _row(novo_agente)

@app.post("/k1/lex/agentes/update")
def atualizar_agente(body: dict, db: Session = Depends(get_db), payload=Depends(_require_admin)):
    """Atualiza um agente existente (apenas admin)"""
    agente_id = body.get("id")
    if not agente_id:
        raise HTTPException(400, "ID do agente obrigatorio")
    
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    agente = db.query(AgenteIA).filter(
        AgenteIA.id == agente_id,
        AgenteIA.tenant_id == tenant_id
    ).first()
    
    if not agente:
        raise HTTPException(404, "Agente nao encontrado")
    
    # Remover 'id' dos dados de atualização
    update_data = {k: v for k, v in body.items() if k != "id" and v is not None}
    
    # Validar provider se fornecido
    if "provider" in update_data and update_data["provider"] not in ["cerebras", "groq"]:
        raise HTTPException(400, "Provider invalido. Use 'cerebras' ou 'groq'")
    
    # Validar prefixo da API key se fornecida
    if "api_key" in update_data:
        provider = update_data.get("provider", agente.provider)
        if provider == "cerebras" and not update_data["api_key"].startswith("csk-"):
            raise HTTPException(400, "API key Cerebras deve comecar com 'csk-'")
        if provider == "groq" and not (update_data["api_key"].startswith("gsk-") or update_data["api_key"].startswith("gsk_")):
            raise HTTPException(400, "API key Groq deve comecar com 'gsk-' ou 'gsk_'")
    
    # Atualizar campos
    for field, value in update_data.items():
        if hasattr(agente, field):
            setattr(agente, field, value)
    
    agente.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(agente)
    
    return _row(agente)

@app.post("/k1/lex/agentes/delete")
def deletar_agente(body: dict, db: Session = Depends(get_db), payload=Depends(_require_admin)):
    """Deleta um agente (apenas admin)"""
    agente_id = body.get("id")
    if not agente_id:
        raise HTTPException(400, "ID do agente obrigatorio")
    
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    agente = db.query(AgenteIA).filter(
        AgenteIA.id == agente_id,
        AgenteIA.tenant_id == tenant_id
    ).first()
    
    if not agente:
        raise HTTPException(404, "Agente nao encontrado")
    
    db.delete(agente)
    db.commit()
    
    return {"ok": True}


# Configuration Models
class CfgDatabase(Base):
    __tablename__ = "cfg_database"
    tenant_id = Column(String(36), primary_key=True)
    user_id = Column(String(36), nullable=False)
    tipo = Column(String(50), default="mysql")
    pool_size = Column(Integer, default=20)
    timeout_segundos = Column(Integer, default=30)
    ssl_enabled = Column(Boolean, default=True)
    backup_frequencia = Column(String(50), default="diario")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CfgCdn(Base):
    __tablename__ = "cfg_cdn"
    tenant_id = Column(String(36), primary_key=True)
    user_id = Column(String(36), nullable=False)
    provider = Column(String(50), default="aws_s3")
    bucket = Column(String(255), nullable=True)
    region = Column(String(100), nullable=True)
    cdn_url = Column(String(255), nullable=True)
    tamanho_max_mb = Column(Integer, default=50)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CfgUsuarios(Base):
    __tablename__ = "cfg_usuarios"
    tenant_id = Column(String(36), primary_key=True)
    user_id = Column(String(36), nullable=False)
    max_tentativas_login = Column(Integer, default=5)
    bloqueio_minutos = Column(Integer, default=15)
    senha_min_chars = Column(Integer, default=8)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CfgSeguranca(Base):
    __tablename__ = "cfg_seguranca"
    tenant_id = Column(String(36), primary_key=True)
    user_id = Column(String(36), nullable=False)
    twofa_obrigatorio = Column(Boolean, default=False)
    jwt_expiracao_horas = Column(Integer, default=8)
    log_acoes = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CfgNotificacoes(Base):
    __tablename__ = "cfg_notificacoes"
    tenant_id = Column(String(36), primary_key=True)
    user_id = Column(String(36), nullable=False)
    email_provider = Column(String(50), default="aws_ses")
    notif_prazos = Column(Boolean, default=True)
    notif_documentos = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Configuration Endpoints
@app.get("/k1/lex/configuracoes/database")
def get_database(db: Session = Depends(get_db), payload=Depends(_require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    row = db.get(CfgDatabase, tenant_id)
    if not row:
        row = CfgDatabase(tenant_id=tenant_id, user_id=user_id)
        db.add(row)
        db.commit()
        db.refresh(row)
    return _row(row)

@app.get("/k1/lex/admin/config/env")
def get_database_env(payload=Depends(_require_admin)):
    """Retorna valores das variáveis de ambiente do banco de dados"""
    return {
        "host": DB_HOST,
        "port": DB_PORT,
        "name": DB_NAME,
        "user": DB_USER,
        "password": DB_PASSWORD,
        "connection_string": DATABASE_URL
    }

@app.post("/k1/lex/configuracoes/database")
def save_database(body: dict, db: Session = Depends(get_db), payload=Depends(_require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    row = db.get(CfgDatabase, tenant_id)
    if not row:
        row = CfgDatabase(tenant_id=tenant_id, user_id=user_id)
        db.add(row)
    for k, v in body.items():
        if hasattr(row, k) and k != "tenant_id" and v is not None:
            setattr(row, k, v)
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return _row(row)

@app.get("/k1/lex/configuracoes/cdn")
def get_cdn(db: Session = Depends(get_db), payload=Depends(_require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    row = db.get(CfgCdn, tenant_id)
    if not row:
        row = CfgCdn(tenant_id=tenant_id, user_id=user_id)
        db.add(row)
        db.commit()
        db.refresh(row)
    return _row(row)

@app.post("/k1/lex/configuracoes/cdn")
def save_cdn(body: dict, db: Session = Depends(get_db), payload=Depends(_require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    row = db.get(CfgCdn, tenant_id)
    if not row:
        row = CfgCdn(tenant_id=tenant_id, user_id=user_id)
        db.add(row)
    for k, v in body.items():
        if hasattr(row, k) and k != "tenant_id" and v is not None:
            setattr(row, k, v)
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return _row(row)

@app.get("/k1/lex/configuracoes/usuarios")
def get_usuarios_cfg(db: Session = Depends(get_db), payload=Depends(_require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    row = db.get(CfgUsuarios, tenant_id)
    if not row:
        row = CfgUsuarios(tenant_id=tenant_id, user_id=user_id)
        db.add(row)
        db.commit()
        db.refresh(row)
    return _row(row)

@app.post("/k1/lex/configuracoes/usuarios")
def save_usuarios_cfg(body: dict, db: Session = Depends(get_db), payload=Depends(_require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    row = db.get(CfgUsuarios, tenant_id)
    if not row:
        row = CfgUsuarios(tenant_id=tenant_id, user_id=user_id)
        db.add(row)
    for k, v in body.items():
        if hasattr(row, k) and k != "tenant_id" and v is not None:
            setattr(row, k, v)
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return _row(row)

@app.get("/k1/lex/configuracoes/seguranca")
def get_seguranca(db: Session = Depends(get_db), payload=Depends(_require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    row = db.get(CfgSeguranca, tenant_id)
    if not row:
        row = CfgSeguranca(tenant_id=tenant_id, user_id=user_id)
        db.add(row)
        db.commit()
        db.refresh(row)
    return _row(row)

@app.post("/k1/lex/configuracoes/seguranca")
def save_seguranca(body: dict, db: Session = Depends(get_db), payload=Depends(_require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    row = db.get(CfgSeguranca, tenant_id)
    if not row:
        row = CfgSeguranca(tenant_id=tenant_id, user_id=user_id)
        db.add(row)
    for k, v in body.items():
        if hasattr(row, k) and k != "tenant_id" and v is not None:
            setattr(row, k, v)
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return _row(row)

@app.get("/k1/lex/configuracoes/notificacoes")
def get_notificacoes(db: Session = Depends(get_db), payload=Depends(_require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    row = db.get(CfgNotificacoes, tenant_id)
    if not row:
        row = CfgNotificacoes(tenant_id=tenant_id, user_id=user_id)
        db.add(row)
        db.commit()
        db.refresh(row)
    return _row(row)

@app.post("/k1/lex/configuracoes/notificacoes")
def save_notificacoes(body: dict, db: Session = Depends(get_db), payload=Depends(_require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    row = db.get(CfgNotificacoes, tenant_id)
    if not row:
        row = CfgNotificacoes(tenant_id=tenant_id, user_id=user_id)
        db.add(row)
    for k, v in body.items():
        if hasattr(row, k) and k != "tenant_id" and v is not None:
            setattr(row, k, v)
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return _row(row)
