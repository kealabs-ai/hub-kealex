import os, re, uuid, json, base64, hashlib
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import jwt, JWTError
from sqlalchemy import create_engine, Column, String, Text, Integer, Boolean, DateTime, UniqueConstraint
from sqlalchemy import text as sql_text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from cryptography.fernet import Fernet, InvalidToken
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
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
KEALEX_SECRET_KEY = os.getenv("KEALEX_SECRET_KEY") or os.getenv("KEALEX_JWT_SECRET")
if not KEALEX_SECRET_KEY:
    raise RuntimeError("KEALEX_SECRET_KEY ou KEALEX_JWT_SECRET precisa estar configurada no ambiente")
_api_key_crypto_secret = os.getenv("KEALEX_API_KEYS_ENCRYPTION_KEY") or os.getenv("KEALEX_JWT_SECRET") or os.getenv("KEALEX_SECRET_KEY")
_api_key_fernet_key = _api_key_crypto_secret.encode() if os.getenv("KEALEX_API_KEYS_ENCRYPTION_KEY") else base64.urlsafe_b64encode(hashlib.sha256((_api_key_crypto_secret + ":user-api-keys:v1").encode()).digest())
try:
    API_KEY_FERNET = Fernet(_api_key_fernet_key)
except (ValueError, TypeError) as exc:
    raise RuntimeError("KEALEX_API_KEYS_ENCRYPTION_KEY precisa ser uma chave Fernet vÃ¡lida.") from exc
ALGORITHM = "HS256"

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

# â”€â”€ Models â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class CfgGeral(Base):
    __tablename__ = "cfg_geral"
    tenant_id       = Column(String(36),  primary_key=True)
    user_id         = Column(String(36),  nullable=False)
    escritorio_id   = Column(String(36),  nullable=True)
    nome_plataforma = Column(String(255), default="Kealex")
    url_base        = Column(String(255), default=os.getenv("KEALEX_PUBLIC_APP_URL", ""))
    email_suporte   = Column(String(255), default=os.getenv("KEALEX_SUPPORT_EMAIL", ""))
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

class CfgIaProvider(Base):
    __tablename__ = "cfg_ia_providers"
    tenant_id     = Column(String(36), primary_key=True)
    provider      = Column(String(50), primary_key=True)
    user_id       = Column(String(36), nullable=False)
    api_key       = Column(Text, nullable=True)
    endpoint_url  = Column(Text, nullable=True)
    modelo        = Column(String(100), nullable=False)
    max_tokens    = Column(Integer, default=8192)
    system_prompt = Column(Text, nullable=True)
    ativo         = Column(Boolean, default=True)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class UserApiKey(Base):
    __tablename__ = "user_api_keys"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, index=True)
    user_id = Column(String(36), nullable=False)
    created_by = Column(String(36), nullable=False)
    provider = Column(String(50), nullable=False)
    model = Column(String(190), nullable=False)
    api_key_encrypted = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    __table_args__ = (UniqueConstraint("user_id", "provider", "model", name="uq_user_api_keys_user_provider_model"),)

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

class AgenteIA(Base):
    __tablename__ = "agentes_ia"
    id            = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id     = Column(String(36), nullable=False)
    owner_user_id = Column(String(36), nullable=True, index=True)
    created_by    = Column(String(36), nullable=True)
    escritorio_id = Column(String(36), nullable=True)
    nome          = Column(String(255), nullable=False)
    descricao     = Column(Text, nullable=True)
    provider      = Column(String(50), nullable=False)
    api_key       = Column(Text, nullable=True)
    modelo        = Column(String(255), nullable=False)
    max_tokens    = Column(Integer, nullable=False, default=8192)
    system_prompt = Column(Text, nullable=True)
    ativo         = Column(Boolean, nullable=False, default=True)
    publico       = Column(Boolean, nullable=False, default=True)
    created_at    = Column(DateTime, default=datetime.utcnow)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AIPlanPolicy(Base):
    __tablename__ = "ia_politicas_planos"
    tenant_id = Column(String(36), primary_key=True)
    plan_key = Column(String(40), primary_key=True)
    can_create_agents = Column(Boolean, nullable=False, default=False)
    allowed_roles = Column(Text, nullable=False, default='["advogado"]')
    max_agents = Column(Integer, nullable=False, default=0)
    allowed_models = Column(Text, nullable=False, default="[]")
    allowed_menus = Column(Text, nullable=False, default="[]")
    monthly_token_limit = Column(Integer, nullable=False, default=0)
    fallback_provider = Column(String(50), nullable=True)
    fallback_model = Column(String(190), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AIUserPolicy(Base):
    __tablename__ = "ia_politicas_usuarios"
    tenant_id = Column(String(36), primary_key=True)
    user_id = Column(String(36), primary_key=True)
    can_create_agents = Column(Boolean, nullable=True)
    max_agents = Column(Integer, nullable=True)
    allowed_models = Column(Text, nullable=True)
    allowed_menus = Column(Text, nullable=True)
    monthly_token_limit = Column(Integer, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AITokenUsage(Base):
    __tablename__ = "ia_uso_tokens"
    tenant_id = Column(String(36), primary_key=True)
    user_id = Column(String(36), primary_key=True)
    period = Column(String(7), primary_key=True)
    tokens_used = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class DriveSource(Base):
    __tablename__ = "drive_sources"
    id              = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id       = Column(String(36), nullable=False)
    agente_id       = Column(String(36), nullable=True)
    pasta_id        = Column(String(255), nullable=False)
    nome_pasta      = Column(String(255), nullable=False)
    service_account = Column(Text, nullable=False)
    ultima_sync     = Column(DateTime, nullable=True)
    ativo           = Column(Boolean, default=True)
    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class IndexacaoArquivos(Base):
    __tablename__ = "indexacao_arquivos"
    id            = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id     = Column(String(36), nullable=False)
    source_id     = Column(String(36), nullable=False)
    arquivo_id    = Column(String(255), nullable=False)
    nome          = Column(String(255), nullable=False)
    tipo          = Column(String(50), nullable=False)
    palavras_chave= Column(Text, nullable=True)
    conteudo      = Column(Text, nullable=True)
    tamanho_bytes = Column(Integer, nullable=True)
    url           = Column(Text, nullable=True)
    indexado_em   = Column(DateTime, default=datetime.utcnow)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

Base.metadata.create_all(engine)

# â”€â”€ Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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
        raise HTTPException(401, "Token invÃ¡lido")

def require_admin(payload=Depends(verify_token)):
    if payload.get("role") != "admin":
        raise HTTPException(403, "Acesso negado")
    return payload

def _row(obj) -> dict:
    d = {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
    for date_field in ["updated_at", "created_at", "indexado_em", "ultima_sync"]:
        if date_field in d and d[date_field]:
            d[date_field] = d[date_field].isoformat()
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

# â”€â”€ App â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

app = FastAPI(title="svc-configuracoes")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
def health():
    return {"status": "ok", "service": "svc-configuracoes"}

# â”€â”€ Geral â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class GeralIn(BaseModel):
    nome_plataforma:  Optional[str]  = None
    url_base:         Optional[str]  = None
    email_suporte:    Optional[str]  = None
    descricao:        Optional[str]  = None
    fuso_horario:     Optional[str]  = None
    idioma:           Optional[str]  = None
    modo_manutencao:  Optional[bool] = None

@app.get("/k1/lex/configuracoes/geral")
def get_geral(db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    return _row(_get_or_create(db, CfgGeral, tenant_id, user_id))

@app.post("/k1/lex/configuracoes/geral")
def save_geral(body: GeralIn, db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    return _row(_upsert(db, CfgGeral, tenant_id, user_id, body.model_dump(exclude_none=True)))

# â”€â”€ CDN â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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

@app.get("/k1/lex/configuracoes/cdn")
def get_cdn(db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    return _row(_get_or_create(db, CfgCdn, tenant_id, user_id))

@app.post("/k1/lex/configuracoes/cdn")
def save_cdn(body: CdnIn, db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    return _row(_upsert(db, CfgCdn, tenant_id, user_id, body.model_dump(exclude_none=True)))

# â”€â”€ Database â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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

@app.get("/k1/lex/configuracoes/database/env")
def get_database_env(payload=Depends(require_admin)):
    """Retorna os dados de conexÃ£o sem revelar a senha."""
    database_url = make_url(KEALEX_DATABASE_URL)
    return {
        "host": database_url.host or "",
        "port": str(database_url.port or ""),
        "name": database_url.database or "",
        "user": database_url.username or "",
        "password": "********" if database_url.password else "",
        "connection_string": database_url.render_as_string(hide_password=True),
    }

@app.get("/k1/lex/configuracoes/database")
def get_database(db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    return _row(_get_or_create(db, CfgDatabase, tenant_id, user_id))

@app.post("/k1/lex/configuracoes/database")
def save_database(body: DatabaseIn, db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    return _row(_upsert(db, CfgDatabase, tenant_id, user_id, body.model_dump(exclude_none=True)))

# â”€â”€ IA â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

# Modelos disponÃ­veis por provider (lista de referÃªncia)
# Nota: O endpoint aceita modelos dinÃ¢micos nÃ£o listados aqui
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
    ],
    "openai": ["gpt-5.5", "gpt-5.4", "gpt-5.4-mini", "gpt-5.4-nano"],
    "google": ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite"],
    "claude": ["claude-opus-5", "claude-sonnet-5", "claude-opus-4-8", "claude-opus-4-7", "claude-sonnet-4-6", "claude-haiku-4-5-20251001"],
    "deepseek": ["deepseek-chat", "deepseek-reasoner"],
}

IA_DEFAULT_MODELS = {
    "cerebras": "llama-3.3-70b", "groq": "llama-3.3-70b-versatile",
    "openai": "gpt-5.5", "google": "gemini-3.8-flash", "claude": "claude-sonnet-5", "deepseek": "deepseek-chat",
}

def _validate_model_provider(provider: str, model: str):
    name = (model or "").strip().lower()
    valid = {
        "openai": name.startswith(("gpt-", "o1-", "o3-", "o4-", "chatgpt-")),
        "claude": name.startswith("claude-"),
        "deepseek": name.startswith("deepseek-"),
        "google": name.startswith("gemini-"),
        "cerebras": bool(name) and not name.startswith(("gpt-", "o1-", "o3-", "o4-", "chatgpt-", "claude-", "gemini-", "deepseek-")),
        "groq": bool(name) and not name.startswith(("gpt-", "o1-", "o3-", "o4-", "chatgpt-", "claude-", "gemini-", "deepseek-")),
    }
    if provider not in valid or not valid[provider]:
        raise HTTPException(400, f"O modelo '{model}' nÃ£o corresponde ao fabricante '{provider}'.")

def _encrypt_user_api_key(value: str) -> str:
    return API_KEY_FERNET.encrypt(value.encode("utf-8")).decode("ascii")

def _decrypt_user_api_key(value: str) -> str:
    try:
        return API_KEY_FERNET.decrypt(value.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError, UnicodeDecodeError) as exc:
        raise HTTPException(500, "NÃ£o foi possÃ­vel descriptografar uma chave de IA. Confira a chave de criptografia do serviÃ§o.") from exc

def _user_api_key_json(row: UserApiKey) -> dict:
    secret = _decrypt_user_api_key(row.api_key_encrypted)
    return {"id": row.id, "provider": row.provider, "model": row.model, "api_key_masked": "â€¢" * max(4, min(12, len(secret) - 4)) + secret[-4:], "is_active": row.is_active, "created_at": row.created_at.isoformat() if row.created_at else None, "updated_at": row.updated_at.isoformat() if row.updated_at else None}

def _validate_user_api_key(provider: str, value: str):
    prefixes = {"cerebras": ("csk-",), "groq": ("gsk-", "gsk_"), "openai": ("sk-",), "google": ("AIza",), "claude": ("sk-ant-",), "deepseek": ("sk-",)}
    if provider not in prefixes or not value.startswith(prefixes[provider]):
        raise HTTPException(400, f"A chave API informada nÃ£o corresponde ao provedor '{provider}'.")

def _current_api_key_owner(payload: dict) -> tuple[str, str]:
    user_id = str(payload.get("sub") or "")
    tenant_id = str(payload.get("tenant_id") or "")
    if not user_id or not tenant_id:
        raise HTTPException(401, "O token nÃ£o identifica o usuÃ¡rio e o tenant.")
    return user_id, tenant_id

class UserApiKeyCreate(BaseModel):
    provider: str
    model: str
    api_key: str
    is_active: bool = True

class UserApiKeyUpdate(BaseModel):
    provider: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None
    is_active: Optional[bool] = None

@app.get("/k1/lex/configuracoes/ia/minhas-chaves")
def list_my_ia_keys(db: Session = Depends(get_db), payload=Depends(verify_token)):
    user_id, tenant_id = _current_api_key_owner(payload)
    _assert_ai_menu(db, payload, "/configuracoes/ia")
    rows = db.query(UserApiKey).filter_by(user_id=user_id, tenant_id=tenant_id).order_by(UserApiKey.created_at.desc()).all()
    return [_user_api_key_json(row) for row in rows]

@app.post("/k1/lex/configuracoes/ia/minhas-chaves", status_code=201)
def create_my_ia_key(body: UserApiKeyCreate, db: Session = Depends(get_db), payload=Depends(verify_token)):
    user_id, tenant_id = _current_api_key_owner(payload)
    _assert_ai_menu(db, payload, "/configuracoes/ia")
    _validate_model_provider(body.provider, body.model)
    _validate_user_api_key(body.provider, body.api_key.strip())
    if db.query(UserApiKey).filter_by(user_id=user_id, provider=body.provider, model=body.model).first():
        raise HTTPException(409, "JÃ¡ existe uma chave cadastrada para este provedor e modelo.")
    if body.is_active:
        db.query(UserApiKey).filter_by(user_id=user_id, tenant_id=tenant_id, is_active=True).update({"is_active": False}, synchronize_session=False)
    row = UserApiKey(tenant_id=tenant_id, user_id=user_id, created_by=user_id, provider=body.provider, model=body.model, api_key_encrypted=_encrypt_user_api_key(body.api_key.strip()), is_active=body.is_active)
    db.add(row)
    db.commit()
    db.refresh(row)
    return _user_api_key_json(row)

@app.put("/k1/lex/configuracoes/ia/minhas-chaves/{key_id}")
def update_my_ia_key(key_id: str, body: UserApiKeyUpdate, db: Session = Depends(get_db), payload=Depends(verify_token)):
    user_id, tenant_id = _current_api_key_owner(payload)
    _assert_ai_menu(db, payload, "/configuracoes/ia")
    row = db.query(UserApiKey).filter_by(id=key_id, user_id=user_id, tenant_id=tenant_id).first()
    if not row:
        raise HTTPException(404, "Chave de IA nÃ£o encontrada.")
    provider, model = body.provider or row.provider, body.model or row.model
    _validate_model_provider(provider, model)
    duplicate = db.query(UserApiKey).filter(UserApiKey.user_id == user_id, UserApiKey.provider == provider, UserApiKey.model == model, UserApiKey.id != row.id).first()
    if duplicate:
        raise HTTPException(409, "JÃ¡ existe uma chave cadastrada para este provedor e modelo.")
    secret = body.api_key.strip() if body.api_key and body.api_key.strip() else _decrypt_user_api_key(row.api_key_encrypted)
    _validate_user_api_key(provider, secret)
    if body.is_active is True:
        db.query(UserApiKey).filter(UserApiKey.user_id == user_id, UserApiKey.tenant_id == tenant_id, UserApiKey.id != row.id, UserApiKey.is_active.is_(True)).update({"is_active": False}, synchronize_session=False)
    row.provider, row.model, row.api_key_encrypted = provider, model, _encrypt_user_api_key(secret)
    if body.is_active is not None: row.is_active = body.is_active
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return _user_api_key_json(row)

@app.delete("/k1/lex/configuracoes/ia/minhas-chaves/{key_id}", status_code=204)
def delete_my_ia_key(key_id: str, db: Session = Depends(get_db), payload=Depends(verify_token)):
    user_id, tenant_id = _current_api_key_owner(payload)
    _assert_ai_menu(db, payload, "/configuracoes/ia")
    row = db.query(UserApiKey).filter_by(id=key_id, user_id=user_id, tenant_id=tenant_id).first()
    if not row:
        raise HTTPException(404, "Chave de IA nÃ£o encontrada.")
    db.delete(row)
    db.commit()

class IaIn(BaseModel):
    provider:      Optional[str]  = None
    api_key:       Optional[str]  = None
    modelo:        Optional[str]  = None
    max_tokens:    Optional[int]  = None
    system_prompt: Optional[str]  = None
    ativo:         Optional[bool] = None

@app.get("/k1/lex/configuracoes/ia")
def get_ia(db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    active = _get_or_create(db, CfgIa, tenant_id, user_id)
    provider_cfg = db.get(CfgIaProvider, (tenant_id, active.provider))
    result = _row(active)
    result.pop("api_key", None)
    result["configured"] = bool((provider_cfg.api_key if provider_cfg else None) or active.api_key)
    return result

@app.get("/k1/lex/configuracoes/ia/modelos")
def get_modelos_disponiveis():
    """Retorna a lista de modelos disponÃ­veis por provider (referÃªncia apenas)
    Nota: O endpoint POST /k1/lex/configuracoes/ia aceita qualquer modelo, nÃ£o apenas os listados aqui
    """
    return MODELOS_DISPONIVEIS

@app.get("/k1/lex/configuracoes/ia/ativa")
def get_ia_ativa(db: Session = Depends(get_db), payload=Depends(verify_token)):
    """Retorna a configuraÃ§Ã£o de IA ativa para o tenant (nÃ£o requer admin)"""
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    active = _get_or_create(db, CfgIa, tenant_id, user_id)
    provider_cfg = db.get(CfgIaProvider, (tenant_id, active.provider))
    result = _row(active)
    result.pop("api_key", None)
    result["configured"] = bool((provider_cfg.api_key if provider_cfg else None) or active.api_key)
    return result

@app.post("/k1/lex/configuracoes/ia")
def save_ia(body: IaIn, db: Session = Depends(get_db), payload=Depends(require_admin)):
    data = body.model_dump(exclude_none=True)
    
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    current = db.get(CfgIa, tenant_id)
    if "provider" in data or "modelo" in data:
        _validate_model_provider(data.get("provider") or (current.provider if current else "cerebras"), data.get("modelo") or (current.modelo if current else IA_DEFAULT_MODELS["cerebras"]))
    
    # Permitir qualquer modelo (sem validaÃ§Ã£o restrita Ã  lista)
    # O frontend pode enviar modelos dinÃ¢micos nÃ£o listados em MODELOS_DISPONIVEIS
    
    # Validar prefixo da API key
    if "api_key" in data and data["api_key"]:
        tenant_id = payload.get("tenant_id") or payload.get("sub")
        existing = db.get(CfgIa, tenant_id)
        provider = data.get("provider") or (existing.provider if existing else "cerebras")
        if provider == "cerebras" and not data["api_key"].startswith("csk-"):
            raise HTTPException(400, "API key Cerebras deve comeÃ§ar com 'csk-'")
        if provider == "groq" and not (data["api_key"].startswith("gsk-") or data["api_key"].startswith("gsk_")):
            raise HTTPException(400, "API key Groq deve comeÃ§ar com 'gsk-' ou 'gsk_'")
    
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    return _row(_upsert(db, CfgIa, tenant_id, user_id, data))

class IaProviderIn(BaseModel):
    api_key: Optional[str] = None
    endpoint_url: Optional[str] = None
    modelo: Optional[str] = None
    max_tokens: Optional[int] = None
    system_prompt: Optional[str] = None
    ativo: Optional[bool] = None

@app.get("/k1/lex/configuracoes/ia/provedores")
def get_ia_provedores(db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    active = _get_or_create(db, CfgIa, tenant_id, user_id)
    rows = db.query(CfgIaProvider).filter_by(tenant_id=tenant_id).all()
    configs = {}
    for row in rows:
        item = _row(row)
        item["configured"] = bool(item.pop("api_key", None))
        configs[row.provider] = item
    # Compatibilidade: migra a configuraÃ§Ã£o antiga para a respectiva aba na primeira leitura.
    if active.provider not in configs:
        legacy = CfgIaProvider(
            tenant_id=tenant_id, user_id=user_id, provider=active.provider,
            api_key=active.api_key, modelo=active.modelo or IA_DEFAULT_MODELS.get(active.provider, ""),
            max_tokens=active.max_tokens or 8192, system_prompt=active.system_prompt, ativo=active.ativo,
        )
        db.add(legacy)
        db.commit()
        db.refresh(legacy)
        item = _row(legacy)
        item["configured"] = bool(item.pop("api_key", None))
        configs[legacy.provider] = item
    return {"active_provider": active.provider, "providers": configs}

@app.post("/k1/lex/configuracoes/ia/provedores/{provider}")
def save_ia_provedor(provider: str, body: IaProviderIn, db: Session = Depends(get_db), payload=Depends(require_admin)):
    if provider not in MODELOS_DISPONIVEIS:
        raise HTTPException(400, "Provider invÃ¡lido")
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    data = body.model_dump(exclude_none=True)
    current = db.get(CfgIaProvider, (tenant_id, provider))
    _validate_model_provider(provider, data.get("modelo") or (current.modelo if current else IA_DEFAULT_MODELS[provider]))
    if data.get("api_key") == "":
        data.pop("api_key")
    if "endpoint_url" in data:
        endpoint = data["endpoint_url"].strip().rstrip("/")
        if provider == "openai" and endpoint and endpoint != "https://api.openai.com/v1":
            raise HTTPException(400, "Use o endpoint oficial https://api.openai.com/v1 da OpenAI.")
        data["endpoint_url"] = endpoint or None
    row = db.get(CfgIaProvider, (tenant_id, provider))
    if row is None:
        row = CfgIaProvider(tenant_id=tenant_id, provider=provider, user_id=user_id,
                            modelo=IA_DEFAULT_MODELS[provider])
        db.add(row)
    for key, value in data.items():
        setattr(row, key, value)
    row.updated_at = datetime.utcnow()
    active = db.get(CfgIa, tenant_id)
    if active and active.provider == provider:
        active.api_key = row.api_key
        active.modelo = row.modelo
        active.max_tokens = row.max_tokens
        active.system_prompt = row.system_prompt
        active.ativo = row.ativo
        active.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    result = _row(row)
    result["configured"] = bool(result.pop("api_key", None))
    return result

@app.post("/k1/lex/configuracoes/ia/provedor-ativo/{provider}")
def set_ia_provedor_ativo(provider: str, db: Session = Depends(get_db), payload=Depends(require_admin)):
    if provider not in MODELOS_DISPONIVEIS:
        raise HTTPException(400, "Provider invÃ¡lido")
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    provider_cfg = db.get(CfgIaProvider, (tenant_id, provider))
    if provider_cfg is None or not provider_cfg.api_key:
        raise HTTPException(400, "Configure a chave API deste provedor antes de ativÃ¡-lo")
    if not provider_cfg.ativo:
        raise HTTPException(400, "Habilite este provedor antes de ativÃ¡-lo")
    active = _get_or_create(db, CfgIa, tenant_id, user_id)
    active.provider = provider
    active.api_key = provider_cfg.api_key
    active.modelo = provider_cfg.modelo
    active.max_tokens = provider_cfg.max_tokens
    active.system_prompt = provider_cfg.system_prompt
    active.ativo = provider_cfg.ativo
    active.updated_at = datetime.utcnow()
    db.commit()
    result = _row(active)
    result.pop("api_key", None)
    result["configured"] = True
    return result

# â”€â”€ UsuÃ¡rios â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class IaChatMessage(BaseModel):
    role: str
    content: str

class IaChatIn(BaseModel):
    messages: list[IaChatMessage]
    agente_id: Optional[str] = None

def _openai_response(api_key: str, model: str, system_prompt: str, messages: list[dict], max_tokens: int, endpoint_url: Optional[str]) -> str:
    base = (endpoint_url or "https://api.openai.com/v1").rstrip("/")
    if base != "https://api.openai.com/v1":
        raise HTTPException(400, "Use o endpoint oficial https://api.openai.com/v1 da OpenAI.")
    request = urllib.request.Request(
        f"{base}/responses",
        data=json.dumps({"model": model, "instructions": system_prompt, "input": messages, "max_output_tokens": max_tokens}).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise HTTPException(502, f"A OpenAI respondeu com erro ({exc.code}): {detail[:1000]}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise HTTPException(502, "NÃƒÂ£o foi possÃƒÂ­vel conectar ÃƒÂ  OpenAI.") from exc
    return result.get("output_text") or "".join(
        part.get("text", "") for item in result.get("output", [])
        for part in item.get("content", []) if part.get("type") == "output_text"
    )

def _provider_response(provider: str, api_key: str, model: str, system_prompt: str, messages: list[dict], max_tokens: int, endpoint_url: Optional[str] = None) -> str:
    if provider == "openai":
        return _openai_response(api_key, model, system_prompt, messages, max_tokens, endpoint_url)
    if provider == "claude":
        url = "https://api.anthropic.com/v1/messages"
        headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01"}
        data = {"model": model, "max_tokens": max_tokens, "system": system_prompt, "messages": messages}
    elif provider == "google":
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        headers = {}
        data = {"systemInstruction": {"parts": [{"text": system_prompt}]}, "contents": [{"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]} for m in messages], "generationConfig": {"maxOutputTokens": max_tokens}}
    else:
        base = {"groq": "https://api.groq.com/openai/v1", "cerebras": "https://api.cerebras.ai/v1", "deepseek": "https://api.deepseek.com"}.get(provider)
        if not base:
            raise HTTPException(400, "Fabricante de IA nÃ£o suportado.")
        url, headers = f"{base}/chat/completions", {"Authorization": f"Bearer {api_key}"}
        data = {"model": model, "messages": [{"role": "system", "content": system_prompt}, *messages], "max_tokens": max_tokens}
    headers.update({"Content-Type": "application/json", "Accept": "application/json", "User-Agent": "Kealex-AI/1.0"})
    request = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        if provider == "groq" and exc.code == 403 and "1010" in detail:
            raise HTTPException(502, "O acesso do servidor ao Groq foi bloqueado pelo Cloudflare (erro 1010). Confira as regras de seguranÃ§a ou a rota de saÃ­da do servidor no provedor.") from exc
        raise HTTPException(502, f"{provider} respondeu com erro ({exc.code}): {detail[:1000]}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise HTTPException(502, f"NÃ£o foi possÃ­vel conectar ao provedor {provider}.") from exc
    if provider == "claude":
        return "".join(part.get("text", "") for part in result.get("content", []))
    if provider == "google":
        return "".join(part.get("text", "") for part in result.get("candidates", [{}])[0].get("content", {}).get("parts", []))
    return result.get("choices", [{}])[0].get("message", {}).get("content", "")

def _record_ai_usage(db: Session, tenant_id: str, user_id: str, messages: list, answer: str):
    # Approximation for providers whose wrapper does not expose usage metadata.
    used = max(1, (sum(len(str(item.get("content", ""))) for item in messages) + len(answer or "")) // 4)
    period = datetime.utcnow().strftime("%Y-%m")
    row = db.query(AITokenUsage).filter_by(tenant_id=tenant_id, user_id=user_id, period=period).first()
    if row:
        row.tokens_used += used
    else:
        db.add(AITokenUsage(tenant_id=tenant_id, user_id=user_id, period=period, tokens_used=used))
    db.commit()

@app.post("/k1/lex/configuracoes/ia/chat")
def chat_ia(body: IaChatIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    user_id, tenant_id = _current_api_key_owner(payload)
    _assert_ai_menu(db, payload, "/ia")
    personal_active = db.query(UserApiKey).filter_by(user_id=user_id, tenant_id=tenant_id, is_active=True).first()
    messages = [{"role": m.role, "content": m.content[:32000]} for m in body.messages[-50:] if m.role in ("user", "assistant")]
    if not messages or messages[-1]["role"] != "user":
        raise HTTPException(400, "A ÃƒÂºltima mensagem deve ser do usuÃƒÂ¡rio.")
    if body.agente_id:
        config = db.query(AgenteIA).filter(AgenteIA.id == body.agente_id, AgenteIA.tenant_id == tenant_id, AgenteIA.ativo == True, ((AgenteIA.publico == True) | (AgenteIA.owner_user_id == user_id))).first()
        if not config:
            raise HTTPException(404, "Agente de IA nÃƒÂ£o encontrado.")
        provider, api_key, model = config.provider, config.api_key, config.modelo
        system_prompt, max_tokens, endpoint_url = config.system_prompt, config.max_tokens or 8192, None
        personal = db.query(UserApiKey).filter_by(user_id=user_id, tenant_id=tenant_id, provider=provider, model=model, is_active=True).first()
        if personal:
            api_key = _decrypt_user_api_key(personal.api_key_encrypted)
    else:
        active = CfgIa(tenant_id=tenant_id, provider=personal_active.provider, api_key=_decrypt_user_api_key(personal_active.api_key_encrypted), modelo=personal_active.model, max_tokens=8192, ativo=True) if personal_active else db.get(CfgIa, tenant_id)
        if not active or not active.ativo:
            raise HTTPException(400, "Nenhum provedor de IA ativo estÃƒÂ¡ configurado.")
        config = None if personal_active else db.get(CfgIaProvider, (tenant_id, active.provider))
        provider = active.provider
        api_key = (config.api_key if config else None) or active.api_key
        model = (config.modelo if config else None) or active.modelo
        system_prompt = (config.system_prompt if config else None) or active.system_prompt
        max_tokens = (config.max_tokens if config else None) or active.max_tokens or 8192
        endpoint_url = config.endpoint_url if config else None
    policy = _effective_ai_policy(db, payload)
    if not _model_allowed(policy, provider, model):
        raise HTTPException(403, "O modelo selecionado nÃ£o estÃ¡ liberado no seu plano.")
    if policy["monthly_token_limit"] > 0 and policy["tokens_used"] >= policy["monthly_token_limit"]:
        fallback_provider, fallback_model = policy.get("fallback_provider"), policy.get("fallback_model")
        fallback_key = db.query(UserApiKey).filter_by(user_id=user_id, tenant_id=tenant_id, provider=fallback_provider, model=fallback_model, is_active=True).first() if fallback_provider and fallback_model else None
        if not fallback_key:
            raise HTTPException(429, "A cota mensal de tokens terminou e nÃ£o hÃ¡ chave pessoal para o modelo de continuidade do plano.")
        provider, model = fallback_provider, fallback_model
        api_key = _decrypt_user_api_key(fallback_key.api_key_encrypted)
        endpoint_url = None
    if api_key and model:
        _validate_model_provider(provider, model)
    if not api_key or not model:
        raise HTTPException(400, f"Configure a chave API e o modelo do provedor {provider}.")
    _validate_model_provider(provider, model)
    system = system_prompt or "Você é um assistente jurídico especializado em direito brasileiro. Responda em português brasileiro."
    if provider == "openai":
        content = _openai_response(api_key, model, system, messages, max_tokens, endpoint_url)
    else:
        content = _provider_response(provider, api_key, model, system, messages, max_tokens, endpoint_url)
    _record_ai_usage(db, tenant_id, user_id, messages, content)
    return {"content": content, "provider": provider, "model": model}
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

@app.get("/k1/lex/configuracoes/usuarios")
def get_usuarios(db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    return _row(_get_or_create(db, CfgUsuarios, tenant_id, user_id))

@app.post("/k1/lex/configuracoes/usuarios")
def save_usuarios(body: UsuariosIn, db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    return _row(_upsert(db, CfgUsuarios, tenant_id, user_id, body.model_dump(exclude_none=True)))

# â”€â”€ SeguranÃ§a â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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

@app.get("/k1/lex/configuracoes/seguranca")
def get_seguranca(db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    return _row(_get_or_create(db, CfgSeguranca, tenant_id, user_id))

@app.post("/k1/lex/configuracoes/seguranca")
def save_seguranca(body: SegurancaIn, db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    return _row(_upsert(db, CfgSeguranca, tenant_id, user_id, body.model_dump(exclude_none=True)))

# â”€â”€ NotificaÃ§Ãµes â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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

@app.get("/k1/lex/configuracoes/notificacoes")
def get_notificacoes(db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    return _row(_get_or_create(db, CfgNotificacoes, tenant_id, user_id))

@app.post("/k1/lex/configuracoes/notificacoes")
def save_notificacoes(body: NotificacoesIn, db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    return _row(_upsert(db, CfgNotificacoes, tenant_id, user_id, body.model_dump(exclude_none=True)))

# â”€â”€ Agentes IA â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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

@app.get("/k1/lex/agentes")
def listar_agentes(db: Session = Depends(get_db), payload=Depends(require_admin)):
    """Lista todos os agentes do tenant (apenas admin)"""
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    agentes = db.query(AgenteIA).filter(AgenteIA.tenant_id == tenant_id).order_by(AgenteIA.created_at.desc()).all()
    return [{**_row(a)} for a in agentes]

@app.get("/k1/lex/agentes/publicos")
def listar_agentes_publicos(db: Session = Depends(get_db), payload=Depends(verify_token)):
    """Lista agentes pÃºblicos e ativos (disponÃ­veis para todos)"""
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    agentes = db.query(AgenteIA).filter(
        AgenteIA.tenant_id == tenant_id,
        AgenteIA.ativo == True,
        AgenteIA.publico == True
    ).order_by(AgenteIA.created_at.desc()).all()
    public_agents = []
    for agent in agentes:
        item = _row(agent)
        item.pop("api_key", None)
        item["configured"] = bool(agent.api_key)
        public_agents.append(item)
    return public_agents

class PersonalAgentIn(BaseModel):
    nome: str
    descricao: Optional[str] = None
    provider: str
    modelo: str
    max_tokens: int = 4096
    system_prompt: Optional[str] = None
    ativo: bool = True


def _json_items(value, default=None):
    try:
        parsed = json.loads(value) if value else default
        return parsed if isinstance(parsed, list) else (default or [])
    except (TypeError, ValueError):
        return default or []


def _plan_key(db: Session, tenant_id: str) -> str:
    try:
        value = db.execute(sql_text("SELECT plano FROM tenants WHERE id=:tenant_id"), {"tenant_id": tenant_id}).scalar()
        return str(value or "trial").lower()
    except Exception:
        db.rollback()
        return "trial"


def _effective_ai_policy(db: Session, payload: dict) -> dict:
    user_id, tenant_id = _current_api_key_owner(payload)
    role = str(payload.get("role") or "")
    plan_key = _plan_key(db, tenant_id)
    plan = db.query(AIPlanPolicy).filter_by(tenant_id=tenant_id, plan_key=plan_key).first()
    user = db.query(AIUserPolicy).filter_by(tenant_id=tenant_id, user_id=user_id).first()
    allowed_roles = _json_items(plan.allowed_roles, ["advogado"]) if plan else ["advogado"]
    models = _json_items(plan.allowed_models, []) if plan else []
    menus = _json_items(plan.allowed_menus, ["/processos", "/documentos", "/prazos", "/atividades", "/financeiro", "/cobranca", "/usuarios", "/equipe", "/clientes", "/intimacoes", "/audiencias", "/integracao-orgaos", "/ia", "/analise-documentos", "/meus-agents", "/configuracoes/ia"]) if plan else ["/processos", "/documentos", "/prazos", "/atividades", "/financeiro", "/cobranca", "/usuarios", "/equipe", "/clientes", "/intimacoes", "/audiencias", "/integracao-orgaos", "/ia", "/analise-documentos", "/meus-agents", "/configuracoes/ia"]
    if user and user.allowed_models is not None: models = _json_items(user.allowed_models, [])
    if user and user.allowed_menus is not None: menus = _json_items(user.allowed_menus, [])
    can_create = bool(plan and plan.can_create_agents and role in allowed_roles)
    if user and user.can_create_agents is not None: can_create = bool(user.can_create_agents)
    monthly_limit = user.monthly_token_limit if user and user.monthly_token_limit is not None else (plan.monthly_token_limit if plan else 0)
    max_agents = user.max_agents if user and user.max_agents is not None else (plan.max_agents if plan else 0)
    period = datetime.utcnow().strftime("%Y-%m")
    usage = db.query(AITokenUsage).filter_by(tenant_id=tenant_id, user_id=user_id, period=period).first()
    return {"plan_key": plan_key, "can_create_agents": can_create, "allowed_roles": allowed_roles, "max_agents": max_agents or 0, "allowed_models": models, "allowed_menus": menus, "monthly_token_limit": monthly_limit or 0, "fallback_provider": plan.fallback_provider if plan else None, "fallback_model": plan.fallback_model if plan else None, "tokens_used": usage.tokens_used if usage else 0}


def _model_allowed(policy: dict, provider: str, model: str) -> bool:
    allowed = policy.get("allowed_models") or []
    return not allowed or model in allowed or f"{provider}:{model}" in allowed


def _assert_ai_menu(db: Session, payload: dict, path: str):
    policy = _effective_ai_policy(db, payload)
    if path not in policy.get("allowed_menus", []):
        raise HTTPException(403, "Este recurso de IA nÃ£o estÃ¡ liberado no plano do usuÃ¡rio.")

@app.get("/k1/lex/ia/politica")
def get_effective_ai_policy(db: Session = Depends(get_db), payload=Depends(verify_token)):
    return _effective_ai_policy(db, payload)


class AIPlanPolicyIn(BaseModel):
    can_create_agents: bool = False
    allowed_roles: list[str] = ["advogado"]
    max_agents: int = 0
    allowed_models: list[str] = []
    allowed_menus: list[str] = []
    monthly_token_limit: int = 0
    fallback_provider: Optional[str] = None
    fallback_model: Optional[str] = None


@app.get("/k1/lex/ia/admin/politicas")
def list_ai_plan_policies(db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    saved = {row.plan_key: row for row in db.query(AIPlanPolicy).filter_by(tenant_id=tenant_id).all()}
    plans = [("trial", "Trial"), ("starter", "Starter"), ("professional", "Professional"), ("enterprise", "Enterprise")]
    known_plans = db.execute(sql_text("SELECT DISTINCT plano FROM tenants WHERE plano IS NOT NULL")).scalars().all()
    for known_plan in known_plans:
        key = str(known_plan or "").strip().lower()
        if key and key not in {plan_key for plan_key, _ in plans}: plans.append((key, key.replace("_", " ").title()))
    return [{"plan_key": key, "plan_label": label, "can_create_agents": bool(saved[key].can_create_agents) if key in saved else False, "allowed_roles": _json_items(saved[key].allowed_roles, ["advogado"]) if key in saved else ["advogado"], "max_agents": saved[key].max_agents if key in saved else 0, "allowed_models": _json_items(saved[key].allowed_models, []) if key in saved else [], "allowed_menus": _json_items(saved[key].allowed_menus, ["/processos", "/documentos", "/prazos", "/atividades", "/financeiro", "/cobranca", "/usuarios", "/equipe", "/clientes", "/intimacoes", "/audiencias", "/integracao-orgaos", "/ia", "/analise-documentos", "/meus-agents", "/configuracoes/ia"]) if key in saved else ["/processos", "/documentos", "/prazos", "/atividades", "/financeiro", "/cobranca", "/usuarios", "/equipe", "/clientes", "/intimacoes", "/audiencias", "/integracao-orgaos", "/ia", "/analise-documentos", "/meus-agents", "/configuracoes/ia"], "monthly_token_limit": saved[key].monthly_token_limit if key in saved else 0, "fallback_provider": saved[key].fallback_provider if key in saved else None, "fallback_model": saved[key].fallback_model if key in saved else None} for key, label in plans]


@app.put("/k1/lex/ia/admin/politicas/{plan_key}")
def save_ai_plan_policy(plan_key: str, body: AIPlanPolicyIn, db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    plan_key = plan_key.strip().lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,39}", plan_key):
        raise HTTPException(400, "Identificador de plano invÃ¡lido.")
    known_plan = db.execute(
        sql_text("SELECT 1 FROM tenants WHERE LOWER(plano)=:plan_key LIMIT 1"),
        {"plan_key": plan_key},
    ).scalar()
    if plan_key not in {"trial", "starter", "professional", "enterprise"} and not known_plan:
        raise HTTPException(400, "Plano invÃ¡lido.")
    if body.max_agents < 0 or body.monthly_token_limit < 0: raise HTTPException(400, "Limites nÃ£o podem ser negativos.")
    row = db.query(AIPlanPolicy).filter_by(tenant_id=tenant_id, plan_key=plan_key).first()
    if not row:
        row = AIPlanPolicy(tenant_id=tenant_id, plan_key=plan_key)
        db.add(row)
    for field in ("can_create_agents", "max_agents", "monthly_token_limit", "fallback_provider", "fallback_model"): setattr(row, field, getattr(body, field))
    row.allowed_roles = json.dumps(body.allowed_roles)
    row.allowed_models = json.dumps(body.allowed_models)
    row.allowed_menus = json.dumps(body.allowed_menus)
    db.commit()
    return {"plan_key": plan_key, **body.model_dump()}


class AIUserPolicyIn(BaseModel):
    can_create_agents: Optional[bool] = None
    max_agents: Optional[int] = None
    allowed_models: Optional[list[str]] = None
    allowed_menus: Optional[list[str]] = None
    monthly_token_limit: Optional[int] = None


@app.get("/k1/lex/ia/admin/usuarios/{user_id}")
def get_ai_user_policy(user_id: str, db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_exists = db.execute(
        sql_text("SELECT 1 FROM usuarios WHERE id=:user_id AND tenant_id=:tenant_id LIMIT 1"),
        {"user_id": user_id, "tenant_id": tenant_id},
    ).scalar()
    if not user_exists: raise HTTPException(404, "UsuÃ¡rio nÃ£o encontrado neste tenant.")
    row = db.query(AIUserPolicy).filter_by(tenant_id=tenant_id, user_id=user_id).first()
    if not row: return {"user_id": user_id, "can_create_agents": None, "max_agents": None, "monthly_token_limit": None, "allowed_models": None, "allowed_menus": None}
    return {"user_id": user_id, "can_create_agents": row.can_create_agents, "max_agents": row.max_agents, "monthly_token_limit": row.monthly_token_limit, "allowed_models": _json_items(row.allowed_models, []) if row.allowed_models else None, "allowed_menus": _json_items(row.allowed_menus, []) if row.allowed_menus else None}

@app.put("/k1/lex/ia/admin/usuarios/{user_id}")
def save_ai_user_policy(user_id: str, body: AIUserPolicyIn, db: Session = Depends(get_db), payload=Depends(require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_exists = db.execute(
        sql_text("SELECT 1 FROM usuarios WHERE id=:user_id AND tenant_id=:tenant_id LIMIT 1"),
        {"user_id": user_id, "tenant_id": tenant_id},
    ).scalar()
    if not user_exists: raise HTTPException(404, "UsuÃ¡rio nÃ£o encontrado neste tenant.")
    if any(value is not None and value < 0 for value in (body.max_agents, body.monthly_token_limit)):
        raise HTTPException(400, "Limites nÃ£o podem ser negativos.")
    row = db.query(AIUserPolicy).filter_by(tenant_id=tenant_id, user_id=user_id).first()
    if not row:
        row = AIUserPolicy(tenant_id=tenant_id, user_id=user_id)
        db.add(row)
    values = body.model_dump(exclude_unset=True)
    for field in ("allowed_models", "allowed_menus"):
        if field in values and values[field] is not None: values[field] = json.dumps(values[field])
    for field, value in values.items(): setattr(row, field, value)
    db.commit()
    return {"user_id": user_id, **values}


@app.get("/k1/lex/agentes/meus")
def list_my_agents(db: Session = Depends(get_db), payload=Depends(verify_token)):
    user_id, tenant_id = _current_api_key_owner(payload)
    _assert_ai_menu(db, payload, "/meus-agents")
    return [{**_row(agent), "api_key": None, "configured": bool(db.query(UserApiKey).filter_by(user_id=user_id, tenant_id=tenant_id, provider=agent.provider, model=agent.modelo, is_active=True).first())} for agent in db.query(AgenteIA).filter_by(tenant_id=tenant_id, owner_user_id=user_id).order_by(AgenteIA.created_at.desc()).all()]


@app.post("/k1/lex/agentes/meus", status_code=201)
def create_my_agent(body: PersonalAgentIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    user_id, tenant_id = _current_api_key_owner(payload)
    _assert_ai_menu(db, payload, "/meus-agents")
    policy = _effective_ai_policy(db, payload)
    if not policy["can_create_agents"]: raise HTTPException(403, "Seu plano nÃ£o permite criar agentes personalizados.")
    count = db.query(AgenteIA).filter_by(tenant_id=tenant_id, owner_user_id=user_id).count()
    if policy["max_agents"] > 0 and count >= policy["max_agents"]: raise HTTPException(403, "VocÃª atingiu o limite de agentes do seu plano.")
    _validate_model_provider(body.provider, body.modelo)
    if not _model_allowed(policy, body.provider, body.modelo): raise HTTPException(403, "O modelo nÃ£o estÃ¡ liberado no seu plano.")
    if not db.query(UserApiKey).filter_by(tenant_id=tenant_id, user_id=user_id, provider=body.provider, model=body.modelo, is_active=True).first(): raise HTTPException(400, "Cadastre sua chave de IA para este provedor e modelo antes de criar o agente.")
    agent = AgenteIA(tenant_id=tenant_id, owner_user_id=user_id, created_by=user_id, escritorio_id=payload.get("escritorio_id"), nome=body.nome, descricao=body.descricao, provider=body.provider, modelo=body.modelo, max_tokens=body.max_tokens, system_prompt=body.system_prompt, ativo=body.ativo, publico=False, api_key=None)
    db.add(agent); db.commit(); db.refresh(agent)
    return {**_row(agent), "api_key": None, "configured": True}


@app.put("/k1/lex/agentes/meus/{agente_id}")
def update_my_agent(agente_id: str, body: PersonalAgentIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    user_id, tenant_id = _current_api_key_owner(payload)
    _assert_ai_menu(db, payload, "/meus-agents")
    agent = db.query(AgenteIA).filter_by(id=agente_id, tenant_id=tenant_id, owner_user_id=user_id).first()
    if not agent: raise HTTPException(404, "Agente nÃ£o encontrado.")
    policy = _effective_ai_policy(db, payload)
    _validate_model_provider(body.provider, body.modelo)
    if not _model_allowed(policy, body.provider, body.modelo): raise HTTPException(403, "O modelo nÃ£o estÃ¡ liberado no seu plano.")
    if not db.query(UserApiKey).filter_by(tenant_id=tenant_id, user_id=user_id, provider=body.provider, model=body.modelo, is_active=True).first(): raise HTTPException(400, "Cadastre sua chave de IA para este provedor e modelo antes de salvar.")
    for field, value in body.model_dump().items(): setattr(agent, field, value)
    agent.updated_at = datetime.utcnow(); db.commit(); db.refresh(agent)
    return {**_row(agent), "api_key": None, "configured": True}


@app.delete("/k1/lex/agentes/meus/{agente_id}", status_code=204)
def delete_my_agent(agente_id: str, db: Session = Depends(get_db), payload=Depends(verify_token)):
    user_id, tenant_id = _current_api_key_owner(payload)
    _assert_ai_menu(db, payload, "/meus-agents")
    agent = db.query(AgenteIA).filter_by(id=agente_id, tenant_id=tenant_id, owner_user_id=user_id).first()
    if not agent: raise HTTPException(404, "Agente nÃ£o encontrado.")
    db.delete(agent); db.commit()

@app.get("/k1/lex/agentes/{agente_id}")
def buscar_agente(agente_id: str, db: Session = Depends(get_db), payload=Depends(verify_token)):
    """Busca um agente especÃ­fico"""
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    agente = db.query(AgenteIA).filter(
        AgenteIA.id == agente_id,
        AgenteIA.tenant_id == tenant_id
    ).first()
    
    if not agente:
        raise HTTPException(404, "Agente nÃ£o encontrado")
    
    # Se nÃ£o for admin, sÃ³ pode ver agentes pÃºblicos
    if payload.get("role") != "admin" and not agente.publico:
        raise HTTPException(403, "Acesso negado a este agente")
    
    return _row(agente)

@app.post("/k1/lex/agentes", status_code=201)
def criar_agente(body: AgenteIACreate, db: Session = Depends(get_db), payload=Depends(require_admin)):
    """Cria um novo agente (apenas admin)"""
    # Validar provider
    _validate_model_provider(body.provider, body.modelo)
    
    # Validar prefixo da API key
    if body.provider == "cerebras" and not body.api_key.startswith("csk-"):
        raise HTTPException(400, "API key Cerebras deve comeÃ§ar com 'csk-'")
    if body.provider == "groq" and not (body.api_key.startswith("gsk-") or body.api_key.startswith("gsk_")):
        raise HTTPException(400, "API key Groq deve comeÃ§ar com 'gsk-' ou 'gsk_'")
    
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

@app.put("/k1/lex/agentes/{agente_id}")
def atualizar_agente(agente_id: str, body: AgenteIAUpdate, db: Session = Depends(get_db), payload=Depends(require_admin)):
    """Atualiza um agente existente (apenas admin)"""
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    agente = db.query(AgenteIA).filter(
        AgenteIA.id == agente_id,
        AgenteIA.tenant_id == tenant_id
    ).first()
    
    if not agente:
        raise HTTPException(404, "Agente nÃ£o encontrado")
    
    # Validar provider se fornecido
    update_data = body.model_dump(exclude_none=True)
    _validate_model_provider(update_data.get("provider", agente.provider), update_data.get("modelo", agente.modelo))
    
    # Validar prefixo da API key se fornecida
    if "api_key" in update_data:
        provider = update_data.get("provider", agente.provider)
        if provider == "cerebras" and not update_data["api_key"].startswith("csk-"):
            raise HTTPException(400, "API key Cerebras deve comeÃ§ar com 'csk-'")
        if provider == "groq" and not (update_data["api_key"].startswith("gsk-") or update_data["api_key"].startswith("gsk_")):
            raise HTTPException(400, "API key Groq deve comeÃ§ar com 'gsk-' ou 'gsk_'")
    
    # Atualizar campos
    for field, value in update_data.items():
        setattr(agente, field, value)
    
    agente.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(agente)
    
    return _row(agente)

@app.delete("/k1/lex/agentes/{agente_id}", status_code=204)
def deletar_agente(agente_id: str, db: Session = Depends(get_db), payload=Depends(require_admin)):
    """Deleta um agente (apenas admin)"""
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    agente = db.query(AgenteIA).filter(
        AgenteIA.id == agente_id,
        AgenteIA.tenant_id == tenant_id
    ).first()
    
    if not agente:
        raise HTTPException(404, "Agente nÃ£o encontrado")
    
    db.delete(agente)
    db.commit()
    
    return None

# â”€â”€ Google Drive â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _get_drive_service(service_account_json: str):
    """Cria cliente Google Drive a partir de service account"""
    try:
        creds_dict = json.loads(service_account_json)
        creds = Credentials.from_service_account_info(
            creds_dict,
            scopes=["https://www.googleapis.com/auth/drive.readonly"]
        )
        return build("drive", "v3", credentials=creds)
    except Exception as e:
        raise HTTPException(400, f"Erro ao criar cliente Drive: {str(e)}")

def _extrair_palavras_chave(nome: str) -> str:
    """Extrai palavras-chave do nome do arquivo"""
    return " ".join([p for p in nome.lower().replace("-", " ").replace("_", " ").split() if len(p) > 2])

def _buscar_arquivos_drive(service, pasta_id: str, tipos: list = None) -> list:
    """Lista arquivos de uma pasta no Drive"""
    if not tipos:
        tipos = ["application/pdf", "application/vnd.google-apps.document", 
                 "application/vnd.google-apps.spreadsheet", "text/plain", "application/msword"]
    
    query = f"'{pasta_id}' in parents and trashed = false"
    mime_query = " or ".join([f"mimeType='{t}'" for t in tipos])
    query += f" and ({mime_query})"
    
    try:
        results = service.files().list(
            q=query,
            spaces="drive",
            fields="files(id, name, mimeType, size, webViewLink, modifiedTime)",
            pageSize=100
        ).execute()
        return results.get("files", [])
    except HttpError as e:
        return []

class DriveSourceCreate(BaseModel):
    pasta_id: str
    nome_pasta: str
    service_account: str
    agente_id: Optional[str] = None

class DriveSourceUpdate(BaseModel):
    nome_pasta: Optional[str] = None
    agente_id: Optional[str] = None
    ativo: Optional[bool] = None

@app.post("/k1/lex/drive-sources", status_code=201)
def criar_drive_source(body: DriveSourceCreate, db: Session = Depends(get_db), payload=Depends(require_admin)):
    """Cria uma nova source de Drive (pasta)"""
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    
    _get_drive_service(body.service_account)
    
    source = DriveSource(
        tenant_id=tenant_id,
        agente_id=body.agente_id,
        pasta_id=body.pasta_id,
        nome_pasta=body.nome_pasta,
        service_account=body.service_account
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return _row(source)

@app.get("/k1/lex/drive-sources")
def listar_drive_sources(db: Session = Depends(get_db), payload=Depends(require_admin)):
    """Lista todas as drive sources do tenant"""
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    sources = db.query(DriveSource).filter(DriveSource.tenant_id == tenant_id).all()
    return [{**_row(s)} for s in sources]

@app.put("/k1/lex/drive-sources/{source_id}")
def atualizar_drive_source(source_id: str, body: DriveSourceUpdate, db: Session = Depends(get_db), payload=Depends(require_admin)):
    """Atualiza uma drive source"""
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    source = db.query(DriveSource).filter(
        DriveSource.id == source_id,
        DriveSource.tenant_id == tenant_id
    ).first()
    
    if not source:
        raise HTTPException(404, "Source nÃ£o encontrada")
    
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(source, field, value)
    
    source.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(source)
    return _row(source)

@app.post("/k1/lex/drive-sources/{source_id}/sincronizar")
def sincronizar_drive_source(source_id: str, db: Session = Depends(get_db), payload=Depends(require_admin)):
    """Sincroniza arquivos de uma drive source"""
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    source = db.query(DriveSource).filter(
        DriveSource.id == source_id,
        DriveSource.tenant_id == tenant_id
    ).first()
    
    if not source:
        raise HTTPException(404, "Source nÃ£o encontrada")
    
    service = _get_drive_service(source.service_account)
    arquivos = _buscar_arquivos_drive(service, source.pasta_id)
    
    for arquivo in arquivos:
        indexacao = db.query(IndexacaoArquivos).filter(
            IndexacaoArquivos.source_id == source_id,
            IndexacaoArquivos.arquivo_id == arquivo["id"]
        ).first()
        
        if not indexacao:
            indexacao = IndexacaoArquivos(
                tenant_id=tenant_id,
                source_id=source_id,
                arquivo_id=arquivo["id"],
                nome=arquivo["name"],
                tipo=arquivo.get("mimeType", "desconhecido"),
                palavras_chave=_extrair_palavras_chave(arquivo["name"]),
                tamanho_bytes=arquivo.get("size"),
                url=arquivo.get("webViewLink")
            )
            db.add(indexacao)
    
    source.ultima_sync = datetime.utcnow()
    db.commit()
    
    return {
        "message": f"{len(arquivos)} arquivos sincronizados",
        "total": len(arquivos),
        "source_id": source_id
    }

@app.get("/k1/lex/drive-sources/{source_id}/arquivos")
def listar_arquivos_indexados(source_id: str, db: Session = Depends(get_db), payload=Depends(verify_token)):
    """Lista arquivos indexados de uma source"""
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    arquivos = db.query(IndexacaoArquivos).filter(
        IndexacaoArquivos.source_id == source_id,
        IndexacaoArquivos.tenant_id == tenant_id
    ).all()
    return [{**_row(a)} for a in arquivos]

@app.get("/k1/lex/agentes/{agente_id}/drive-contexto")
def obter_drive_contexto(agente_id: str, prompt: str = "", db: Session = Depends(get_db), payload=Depends(verify_token)):
    """ObtÃ©m contexto do Drive para enriquecer prompt do agente (busca por palavras-chave)"""
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    
    agente = db.query(AgenteIA).filter(
        AgenteIA.id == agente_id,
        AgenteIA.tenant_id == tenant_id
    ).first()
    
    if not agente:
        raise HTTPException(404, "Agente nÃ£o encontrado")
    
    palavras_prompt = prompt.lower().split() if prompt else []
    sources = db.query(DriveSource).filter(
        DriveSource.tenant_id == tenant_id,
        DriveSource.agente_id == agente_id,
        DriveSource.ativo == True
    ).all()
    
    contexto_arquivos = []
    for source in sources:
        arquivos = db.query(IndexacaoArquivos).filter(
            IndexacaoArquivos.source_id == source.id
        ).all()
        
        for arquivo in arquivos:
            palavras_arquivo = (arquivo.palavras_chave or "").split()
            match_score = sum(1 for p in palavras_prompt if p in palavras_arquivo)
            
            if match_score > 0 or not palavras_prompt:
                contexto_arquivos.append({
                    "nome": arquivo.nome,
                    "tipo": arquivo.tipo,
                    "url": arquivo.url,
                    "score": match_score,
                    "palavras_chave": arquivo.palavras_chave
                })
    
    contexto_arquivos.sort(key=lambda x: x["score"], reverse=True)
    
    prompt_enriquecido = prompt + "\n\n=== CONTEXTO DO DRIVE ===\nArquivos relevantes:\n"
    prompt_enriquecido += "\n".join([f"- {a['nome']} ({a['tipo']}) - {a['url']}" for a in contexto_arquivos[:10]])
    
    return {
        "arquivos_relevantes": contexto_arquivos[:10],
        "total_encontrado": len(contexto_arquivos),
        "prompt_enriquecido": prompt_enriquecido
    }


