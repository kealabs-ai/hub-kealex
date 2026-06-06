import os, uuid
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import jwt, JWTError
from sqlalchemy import create_engine, Column, String, Text, Integer, Boolean, DateTime
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

# ── Models ────────────────────────────────────────────────────────────────────

class CfgGeral(Base):
    __tablename__ = "cfg_geral"
    tenant_id       = Column(String(36),  primary_key=True)
    user_id         = Column(String(36),  nullable=False)
    escritorio_id   = Column(String(36),  nullable=True)
    nome_plataforma = Column(String(255), default="Kealex")
    url_base        = Column(String(255), default="https://kealex.com.br")
    email_suporte   = Column(String(255), default="suporte@kealex.com.br")
    descricao       = Column(Text,        nullable=True)
    fuso_horario    = Column(String(100), default="America/Sao_Paulo")
    idioma          = Column(String(20),  default="pt-BR")
    modo_manutencao = Column(Boolean,     default=False)
    updated_at      = Column(DateTime,    default=datetime.utcnow, onupdate=datetime.utcnow)

class CfgCdn(Base):
    __tablename__ = "cfg_cdn"
    tenant_id         = Column(String(36),  primary_key=True)
    user_id           = Column(String(36),  nullable=False)
    escritorio_id     = Column(String(36),  nullable=True)
    provider          = Column(String(50),  default="aws_s3")
    bucket            = Column(String(255), nullable=True)
    region            = Column(String(100), nullable=True)
    access_key_id     = Column(String(255), nullable=True)
    secret_access_key = Column(String(255), nullable=True)
    cdn_url           = Column(String(255), nullable=True)
    tamanho_max_mb    = Column(Integer,     default=50)
    tipos_permitidos  = Column(String(255), default="pdf,docx,xlsx,png,jpg")
    retencao_arquivo  = Column(Boolean,     default=True)
    retencao_delete   = Column(Boolean,     default=False)
    updated_at        = Column(DateTime,    default=datetime.utcnow, onupdate=datetime.utcnow)

class CfgDatabase(Base):
    __tablename__ = "cfg_database"
    tenant_id         = Column(String(36),  primary_key=True)
    user_id           = Column(String(36),  nullable=False)
    escritorio_id     = Column(String(36),  nullable=True)
    tipo              = Column(String(50),  default="mysql")
    connection_string = Column(Text,        nullable=True)
    pool_size         = Column(Integer,     default=20)
    timeout_segundos  = Column(Integer,     default=30)
    ssl_enabled       = Column(Boolean,     default=True)
    query_logging     = Column(Boolean,     default=True)
    read_replicas     = Column(Boolean,     default=False)
    backup_frequencia = Column(String(50),  default="diario")
    backup_retencao   = Column(Integer,     default=30)
    updated_at        = Column(DateTime,    default=datetime.utcnow, onupdate=datetime.utcnow)

class CfgIa(Base):
    __tablename__ = "cfg_ia"
    tenant_id     = Column(String(36),  primary_key=True)
    user_id       = Column(String(36),  nullable=False)
    escritorio_id = Column(String(36),  nullable=True)
    provider      = Column(String(50),  default="cerebras")
    api_key       = Column(String(255), nullable=True)
    modelo        = Column(String(100), default="llama-3.3-70b")
    max_tokens    = Column(Integer,     default=8192)
    system_prompt = Column(Text,        nullable=True)
    ativo         = Column(Boolean,     default=True)
    updated_at    = Column(DateTime,    default=datetime.utcnow, onupdate=datetime.utcnow)

class CfgUsuarios(Base):
    __tablename__ = "cfg_usuarios"
    tenant_id            = Column(String(36), primary_key=True)
    user_id              = Column(String(36), nullable=False)
    escritorio_id        = Column(String(36), nullable=True)
    max_tentativas_login = Column(Integer,    default=5)
    bloqueio_minutos     = Column(Integer,    default=15)
    senha_min_chars      = Column(Integer,    default=8)
    senha_maiusculas     = Column(Boolean,    default=True)
    senha_numeros        = Column(Boolean,    default=True)
    senha_especiais      = Column(Boolean,    default=False)
    senha_expiracao_dias = Column(Integer,    default=90)
    sessao_inativa_min   = Column(Integer,    default=30)
    registro_modo        = Column(String(50), default="convite")
    updated_at           = Column(DateTime,   default=datetime.utcnow, onupdate=datetime.utcnow)

class CfgSeguranca(Base):
    __tablename__ = "cfg_seguranca"
    tenant_id           = Column(String(36),  primary_key=True)
    user_id             = Column(String(36),  nullable=False)
    escritorio_id       = Column(String(36),  nullable=True)
    twofa_obrigatorio   = Column(Boolean,     default=False)
    oauth_google        = Column(Boolean,     default=False)
    oauth_microsoft     = Column(Boolean,     default=False)
    jwt_expiracao_horas = Column(Integer,     default=8)
    log_acoes           = Column(Boolean,     default=True)
    log_documentos      = Column(Boolean,     default=True)
    alerta_suspeito     = Column(Boolean,     default=False)
    ips_bloqueados      = Column(Text,        nullable=True)
    lgpd_consentimento  = Column(Boolean,     default=True)
    lgpd_esquecimento   = Column(Boolean,     default=True)
    lgpd_exportacao     = Column(Boolean,     default=True)
    updated_at          = Column(DateTime,    default=datetime.utcnow, onupdate=datetime.utcnow)

class CfgNotificacoes(Base):
    __tablename__ = "cfg_notificacoes"
    tenant_id        = Column(String(36),  primary_key=True)
    user_id          = Column(String(36),  nullable=False)
    escritorio_id    = Column(String(36),  nullable=True)
    email_provider   = Column(String(50),  default="aws_ses")
    email_region     = Column(String(100), nullable=True)
    email_access_key = Column(String(255), nullable=True)
    email_secret_key = Column(String(255), nullable=True)
    email_remetente  = Column(String(255), nullable=True)
    notif_prazos     = Column(Boolean,     default=True)
    notif_honorarios = Column(Boolean,     default=True)
    notif_documentos = Column(Boolean,     default=True)
    notif_relatorio  = Column(Boolean,     default=False)
    notif_push       = Column(String(20),  default="habilitadas")
    notif_sms        = Column(String(20),  default="desabilitadas")
    updated_at       = Column(DateTime,    default=datetime.utcnow, onupdate=datetime.utcnow)

Base.metadata.create_all(engine)

# ── Helpers ───────────────────────────────────────────────────────────────────

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

def _row(obj) -> dict:
    d = {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
    if "updated_at" in d and d["updated_at"]:
        d["updated_at"] = d["updated_at"].isoformat()
    return d

def _get_or_create(db, Model, tenant_id: str, user_id: str):
    row = db.get(Model, tenant_id)
    if not row:
        row = Model(tenant_id=tenant_id, user_id=user_id)
        # Para cfg_ia, definir escritorio_id como None explicitamente
        if Model.__tablename__ == 'cfg_ia':
            row.escritorio_id = None
        db.add(row)
        db.commit()
        db.refresh(row)
    return row

def _upsert(db, Model, tenant_id: str, user_id: str, data: dict):
    row = db.get(Model, tenant_id)
    if not row:
        row = Model(tenant_id=tenant_id, user_id=user_id)
        # Para cfg_ia, definir escritorio_id como None explicitamente
        if Model.__tablename__ == 'cfg_ia':
            row.escritorio_id = None
        db.add(row)
    for k, v in data.items():
        setattr(row, k, v)
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return row

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(title="svc-configuracoes")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── Geral ─────────────────────────────────────────────────────────────────────

class GeralIn(BaseModel):
    nome_plataforma:  Optional[str]  = None
    url_base:         Optional[str]  = None
    email_suporte:    Optional[str]  = None
    descricao:        Optional[str]  = None
    fuso_horario:     Optional[str]  = None
    idioma:           Optional[str]  = None
    modo_manutencao:  Optional[bool] = None

@app.get("/v1/lex/configuracoes/geral")
def get_geral(db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    return _row(_get_or_create(db, CfgGeral, tenant_id, user_id))

@app.post("/v1/lex/configuracoes/geral")
def save_geral(body: GeralIn, db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    return _row(_upsert(db, CfgGeral, tenant_id, user_id, body.model_dump(exclude_none=True)))

# ── CDN ───────────────────────────────────────────────────────────────────────

class CdnIn(BaseModel):
    provider:          Optional[str]  = None
    bucket:            Optional[str]  = None
    region:            Optional[str]  = None
    access_key_id:     Optional[str]  = None
    secret_access_key: Optional[str]  = None
    cdn_url:           Optional[str]  = None
    tamanho_max_mb:    Optional[int]  = None
    tipos_permitidos:  Optional[str]  = None
    retencao_arquivo:  Optional[bool] = None
    retencao_delete:   Optional[bool] = None

@app.get("/v1/lex/configuracoes/cdn")
def get_cdn(db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    return _row(_get_or_create(db, CfgCdn, tenant_id, user_id))

@app.post("/v1/lex/configuracoes/cdn")
def save_cdn(body: CdnIn, db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    return _row(_upsert(db, CfgCdn, tenant_id, user_id, body.model_dump(exclude_none=True)))

# ── Database ──────────────────────────────────────────────────────────────────

class DatabaseIn(BaseModel):
    tipo:              Optional[str]  = None
    connection_string: Optional[str]  = None
    pool_size:         Optional[int]  = None
    timeout_segundos:  Optional[int]  = None
    ssl_enabled:       Optional[bool] = None
    query_logging:     Optional[bool] = None
    read_replicas:     Optional[bool] = None
    backup_frequencia: Optional[str]  = None
    backup_retencao:   Optional[int]  = None

@app.get("/v1/lex/configuracoes/database")
def get_database(db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    return _row(_get_or_create(db, CfgDatabase, tenant_id, user_id))

@app.post("/v1/lex/configuracoes/database")
def save_database(body: DatabaseIn, db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    return _row(_upsert(db, CfgDatabase, tenant_id, user_id, body.model_dump(exclude_none=True)))

# ── IA ────────────────────────────────────────────────────────────────────────

# Modelos disponíveis por provider
MODELOS_DISPONIVEIS = {
    "cerebras": [
        "llama-3.3-70b",
        "llama-3.1-70b",
        "llama-3.1-8b"
    ],
    "groq": [
        "llama-3.3-70b-versatile",
        "llama-3.1-70b-versatile", 
        "llama-3.1-8b-instant",
        "llama-3.2-90b-text-preview",
        "llama-3.2-11b-text-preview",
        "llama-3.2-3b-preview",
        "llama-3.2-1b-preview",
        "gemma2-9b-it",
        "gemma-7b-it"
    ]
}

class IaIn(BaseModel):
    provider:      Optional[str]  = None
    api_key:       Optional[str]  = None
    modelo:        Optional[str]  = None
    max_tokens:    Optional[int]  = None
    system_prompt: Optional[str]  = None
    ativo:         Optional[bool] = None

@app.get("/v1/lex/configuracoes/ia")
def get_ia(db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    return _row(_get_or_create(db, CfgIa, tenant_id, user_id))

@app.get("/v1/lex/configuracoes/ia/modelos")
def get_modelos_disponiveis():
    """Retorna a lista de modelos disponíveis por provider"""
    return MODELOS_DISPONIVEIS

@app.get("/v1/lex/configuracoes/ia/ativa")
def get_ia_ativa(db: Session = Depends(get_db), payload=Depends(verify_token)):
    """Retorna a configuração de IA ativa para o tenant (não requer admin)"""
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    return _row(_get_or_create(db, CfgIa, tenant_id, user_id))

@app.post("/v1/lex/configuracoes/ia")
def save_ia(body: IaIn, db: Session = Depends(get_db), payload=Depends(require_admin)):
    data = body.model_dump(exclude_none=True)
    
    # Validar provider
    if "provider" in data and data["provider"] not in ["cerebras", "groq"]:
        raise HTTPException(400, "Provider inválido. Use 'cerebras' ou 'groq'")
    
    # Validar modelo - permitir qualquer modelo para Groq (validação dinâmica)
    if "modelo" in data and "provider" in data:
        provider = data["provider"]
        modelo = data["modelo"]
        # Apenas validar Cerebras estritamente, Groq permite modelos dinâmicos
        if provider == "cerebras" and modelo not in MODELOS_DISPONIVEIS.get(provider, []):
            modelos_validos = ", ".join(MODELOS_DISPONIVEIS.get(provider, []))
            raise HTTPException(400, f"Modelo '{modelo}' inválido para provider '{provider}'. Modelos válidos: {modelos_validos}")
    
    # Validar prefixo da API key
    if "api_key" in data and data["api_key"]:
        tenant_id = payload.get("tenant_id") or payload.get("sub")
        existing = db.get(CfgIa, tenant_id)
        provider = data.get("provider") or (existing.provider if existing else "cerebras")
        if provider == "cerebras" and not data["api_key"].startswith("csk-"):
            raise HTTPException(400, "API key Cerebras deve começar com 'csk-'")
        if provider == "groq" and not (data["api_key"].startswith("gsk-") or data["api_key"].startswith("gsk_")):
            raise HTTPException(400, "API key Groq deve começar com 'gsk-' ou 'gsk_'")
    
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    return _row(_upsert(db, CfgIa, tenant_id, user_id, data))

# ── Usuários ──────────────────────────────────────────────────────────────────

class UsuariosIn(BaseModel):
    max_tentativas_login: Optional[int]  = None
    bloqueio_minutos:     Optional[int]  = None
    senha_min_chars:      Optional[int]  = None
    senha_maiusculas:     Optional[bool] = None
    senha_numeros:        Optional[bool] = None
    senha_especiais:      Optional[bool] = None
    senha_expiracao_dias: Optional[int]  = None
    sessao_inativa_min:   Optional[int]  = None
    registro_modo:        Optional[str]  = None

@app.get("/v1/lex/configuracoes/usuarios")
def get_usuarios(db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    return _row(_get_or_create(db, CfgUsuarios, tenant_id, user_id))

@app.post("/v1/lex/configuracoes/usuarios")
def save_usuarios(body: UsuariosIn, db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    return _row(_upsert(db, CfgUsuarios, tenant_id, user_id, body.model_dump(exclude_none=True)))

# ── Segurança ─────────────────────────────────────────────────────────────────

class SegurancaIn(BaseModel):
    twofa_obrigatorio:   Optional[bool] = None
    oauth_google:        Optional[bool] = None
    oauth_microsoft:     Optional[bool] = None
    jwt_expiracao_horas: Optional[int]  = None
    log_acoes:           Optional[bool] = None
    log_documentos:      Optional[bool] = None
    alerta_suspeito:     Optional[bool] = None
    ips_bloqueados:      Optional[str]  = None
    lgpd_consentimento:  Optional[bool] = None
    lgpd_esquecimento:   Optional[bool] = None
    lgpd_exportacao:     Optional[bool] = None

@app.get("/v1/lex/configuracoes/seguranca")
def get_seguranca(db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    return _row(_get_or_create(db, CfgSeguranca, tenant_id, user_id))

@app.post("/v1/lex/configuracoes/seguranca")
def save_seguranca(body: SegurancaIn, db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    return _row(_upsert(db, CfgSeguranca, tenant_id, user_id, body.model_dump(exclude_none=True)))

# ── Notificações ──────────────────────────────────────────────────────────────

class NotificacoesIn(BaseModel):
    email_provider:   Optional[str]  = None
    email_region:     Optional[str]  = None
    email_access_key: Optional[str]  = None
    email_secret_key: Optional[str]  = None
    email_remetente:  Optional[str]  = None
    notif_prazos:     Optional[bool] = None
    notif_honorarios: Optional[bool] = None
    notif_documentos: Optional[bool] = None
    notif_relatorio:  Optional[bool] = None
    notif_push:       Optional[str]  = None
    notif_sms:        Optional[str]  = None

@app.get("/v1/lex/configuracoes/notificacoes")
def get_notificacoes(db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    return _row(_get_or_create(db, CfgNotificacoes, tenant_id, user_id))

@app.post("/v1/lex/configuracoes/notificacoes")
def save_notificacoes(body: NotificacoesIn, db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    return _row(_upsert(db, CfgNotificacoes, tenant_id, user_id, body.model_dump(exclude_none=True)))