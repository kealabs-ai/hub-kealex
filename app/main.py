import os, re, uuid, enum, logging, base64, hashlib
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta
from typing import Optional, List
from urllib.parse import quote_plus
from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field
import bcrypt
from jose import jwt, JWTError
from sqlalchemy import create_engine, Column, String, Boolean, Date, DateTime, Enum as SAEnum, Index, PrimaryKeyConstraint, Text, Integer, Numeric, ForeignKey, UniqueConstraint
from sqlalchemy import text as sql_text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from cryptography.fernet import Fernet, InvalidToken

# Carregar variáveis de ambiente
from dotenv import load_dotenv
load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Configurações do Banco de Dados
def _get_database_url():
    """Monta a URL com credenciais separadas para escapar caracteres especiais."""
    host = os.getenv("KEALEX_DB_HOST")
    database = os.getenv("KEALEX_DB_NAME")
    username = os.getenv("KEALEX_DB_USER")
    password = os.getenv("KEALEX_DB_PASSWORD")

    if host and database and username and password is not None:
        # Escapar caracteres especiais na senha e username usando quote_plus
        escaped_password = quote_plus(password)
        escaped_username = quote_plus(username)
        return make_url(
            f"mysql+pymysql://{escaped_username}:{escaped_password}@"
            f"{host}:{os.getenv('KEALEX_DB_PORT', '3306')}/{database}"
        )

    legacy_url = os.getenv("KEALEX_DATABASE_URL")
    if legacy_url:
        return make_url(legacy_url)
    raise RuntimeError(
        "Configure KEALEX_DB_HOST, KEALEX_DB_NAME, KEALEX_DB_USER e KEALEX_DB_PASSWORD "
        "(ou KEALEX_DATABASE_URL para compatibilidade)"
    )

KEALEX_DATABASE_URL = _get_database_url()
DATABASE_CONFIG = make_url(KEALEX_DATABASE_URL)
DB_HOST = DATABASE_CONFIG.host or ""
DB_PORT = str(DATABASE_CONFIG.port or "")
DB_NAME = DATABASE_CONFIG.database or ""
DB_USER = DATABASE_CONFIG.username or ""

# Configurações de Autenticação
KEALEX_SECRET_KEY = os.getenv("KEALEX_JWT_SECRET") or os.getenv("KEALEX_SECRET_KEY")
if not KEALEX_SECRET_KEY:
    raise RuntimeError("KEALEX_JWT_SECRET ou KEALEX_SECRET_KEY precisa estar configurada no ambiente")
_api_key_crypto_secret = os.getenv("KEALEX_API_KEYS_ENCRYPTION_KEY") or os.getenv("KEALEX_JWT_SECRET") or os.getenv("KEALEX_SECRET_KEY")
_api_key_fernet_key = _api_key_crypto_secret.encode() if os.getenv("KEALEX_API_KEYS_ENCRYPTION_KEY") else base64.urlsafe_b64encode(hashlib.sha256((_api_key_crypto_secret + ":user-api-keys:v1").encode()).digest())
try:
    API_KEY_FERNET = Fernet(_api_key_fernet_key)
except (ValueError, TypeError) as exc:
    raise RuntimeError("KEALEX_API_KEYS_ENCRYPTION_KEY precisa ser uma chave Fernet válida.") from exc
ALGORITHM = "HS256"
KEALEX_JWT_EXPIRY_HOURS = int(os.getenv("KEALEX_JWT_EXPIRY_HOURS", "8"))
TOKEN_EXPIRE_MINUTES = KEALEX_JWT_EXPIRY_HOURS * 60

# Configurações de LLM API Keys
KEALEX_GEMINI_API_KEY = os.getenv("KEALEX_GEMINI_API_KEY", "")
KEALEX_OPENAI_API_KEY = os.getenv("KEALEX_OPENAI_API_KEY", "")
KEALEX_GROQ_API_KEY = os.getenv("KEALEX_GROQ_API_KEY", "")
KEALEX_ANTHROPIC_API_KEY = os.getenv("KEALEX_ANTHROPIC_API_KEY", "")
KEALEX_CEREBRAS_API_KEY = os.getenv("KEALEX_CEREBRAS_API_KEY", "")

# Configurações de Aplicação
KEALEX_ENVIRONMENT = os.getenv("KEALEX_ENVIRONMENT", "development")
KEALEX_DEBUG = os.getenv("KEALEX_DEBUG", "true").lower() == "true"

engine = create_engine(
    KEALEX_DATABASE_URL,
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
    escritorio = "escritorio"
    advogado = "advogado"
    juridico = "juridico"
    cliente = "cliente"

class StatusEnum(str, enum.Enum):
    ativo = "ativo"
    arquivado = "arquivado"
    encerrado = "encerrado"

# Models
TRIAL_DAYS = 7

class Tenant(Base):
    __tablename__ = "tenants"
    id               = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    nome             = Column(String(255), nullable=False)
    slug             = Column(String(100), unique=True, nullable=False)
    plano            = Column(String(20), nullable=False, default="trial")
    trial_started_at = Column(DateTime, nullable=True)
    trial_expires_at = Column(DateTime, nullable=True)
    email            = Column(String(255), nullable=True)
    whatsapp         = Column(String(20), nullable=True)
    billing_cpf_cnpj      = Column(String(20),  nullable=True)
    billing_phone         = Column(String(30),  nullable=True)
    billing_mobile_phone  = Column(String(30),  nullable=True)
    billing_name          = Column(String(255), nullable=True)
    billing_email         = Column(String(255), nullable=True)
    billing_postal_code   = Column(String(10),  nullable=True)
    billing_address       = Column(String(255), nullable=True)
    billing_address_number = Column(String(20), nullable=True)
    billing_complement    = Column(String(100), nullable=True)
    billing_neighborhood  = Column(String(100), nullable=True)
    billing_city          = Column(String(100), nullable=True)
    billing_state         = Column(String(2),   nullable=True)
    perfil                = Column(String(50),  nullable=True)
    asaas_customer_id     = Column(String(80),  nullable=True)
    asaas_subscription_id = Column(String(80),  nullable=True)
    subscription_plan     = Column(String(20),  nullable=True)
    subscription_cycle    = Column(String(20),  nullable=True)
    subscription_expires_at = Column(DateTime, nullable=True)
    last_paid_payment_id  = Column(String(80),  nullable=True)
    subscription_status   = Column(String(20),  nullable=False, default="trialing")
    next_due_date         = Column(String(10),  nullable=True)
    ativo                 = Column(Boolean, default=True)
    created_at       = Column(DateTime, default=datetime.utcnow)
    updated_at       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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

class CfgIaProvider(Base):
    __tablename__ = "cfg_ia_providers"
    tenant_id = Column(String(36), primary_key=True)
    provider = Column(String(50), primary_key=True)
    user_id = Column(String(36), nullable=False)
    api_key = Column(Text, nullable=True)
    endpoint_url = Column(Text, nullable=True)
    modelo = Column(String(100), nullable=False)
    max_tokens = Column(Integer, default=8192)
    system_prompt = Column(Text, nullable=True)
    ativo = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class UserApiKey(Base):
    __tablename__ = "user_api_keys"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    created_by = Column(String(36), ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    provider = Column(String(50), nullable=False)
    model = Column(String(190), nullable=False)
    api_key_encrypted = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    __table_args__ = (UniqueConstraint("user_id", "provider", "model", name="uq_user_api_keys_user_provider_model"),)

class AgenteIA(Base):
    __tablename__ = "agentes_ia"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False)
    owner_user_id = Column(String(36), nullable=True, index=True)
    created_by = Column(String(36), nullable=True)
    escritorio_id = Column(String(36), nullable=True)
    nome = Column(String(255), nullable=False)
    descricao = Column(Text, nullable=True)
    provider = Column(String(50), nullable=False)
    api_key = Column(Text, nullable=True)
    modelo = Column(String(255), nullable=False)
    max_tokens = Column(Integer, nullable=False, default=8192)
    system_prompt = Column(Text, nullable=True)
    ativo = Column(Boolean, nullable=False, default=True)
    publico = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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

class Audiencia(Base):
    __tablename__ = "audiencias"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, index=True)
    user_id = Column(String(36), nullable=False)
    processo_id = Column(String(36), nullable=True)
    processo_titulo = Column(String(255), nullable=False, default="")
    tipo = Column(String(80), nullable=False, default="")
    data_hora = Column(String(40), nullable=False, default="")
    local = Column(String(255), nullable=False, default="")
    juiz = Column(String(255), nullable=True)
    partes = Column(Text, nullable=True)
    observacoes = Column(Text, nullable=True)
    roteiro = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="agendada")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

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

class Cobranca(Base):
    __tablename__ = "cobrancas"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False)
    user_id = Column(String(36), nullable=False)
    processo_id = Column(String(36), nullable=False)
    cliente_id = Column(String(36), nullable=False)
    valor_centavos = Column(Integer, nullable=False)
    status = Column(String(50), default="pendente")
    fase_atual = Column(Integer, default=0)
    data_vencimento = Column(DateTime, nullable=True)
    data_pagamento = Column(DateTime, nullable=True)
    motivo_cancelamento = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class HistoricoCobranca(Base):
    __tablename__ = "historico_cobrancas"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    cobranca_id = Column(String(36), nullable=False)
    acao = Column(String(100), nullable=False)
    fase_anterior = Column(Integer, nullable=True)
    fase_nova = Column(Integer, nullable=True)
    status_anterior = Column(String(50), nullable=True)
    status_novo = Column(String(50), nullable=True)
    observacao = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

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
    status = Column(String(36), nullable=False, default="todo")
    priority = Column(String(20), nullable=False, default="media")
    due_date = Column(Date, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

class ActivityColumn(Base):
    __tablename__ = "activity_columns"
    __table_args__ = (
        PrimaryKeyConstraint("user_id", "id", name="pk_activity_columns_user_id_id"),
        Index("ix_activity_columns_tenant_user_position", "tenant_id", "user_id", "position"),
    )
    id = Column(String(36), nullable=False)
    user_id = Column(String(36), nullable=False)
    tenant_id = Column(String(36), nullable=False)
    title = Column(String(80), nullable=False)
    color = Column(String(7), nullable=False, default="#087E96")
    position = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

class AsaasWebhookEvent(Base):
    __tablename__ = "asaas_webhook_events"
    id          = Column(String(100), primary_key=True)   # event id do ASAAS
    event       = Column(String(80),  nullable=False)
    received_at = Column(DateTime,    default=datetime.utcnow, nullable=False)


def _cobranca_to_dict(c: Cobranca) -> dict:
    fases_labels = ["Pendente", "Aguardando Pagamento", "Vencida", "Em Cobrança", "Pago"]
    return {
        "id": c.id, "tenantId": c.tenant_id, "processoId": c.processo_id, "clienteId": c.cliente_id,
        "valorCentavos": c.valor_centavos, "status": c.status, "faseAtual": c.fase_atual,
        "faseLabel": fases_labels[c.fase_atual] if c.fase_atual < len(fases_labels) else "Desconhecida",
        "dataVencimento": c.data_vencimento.isoformat() if c.data_vencimento else None,
        "dataPagamento": c.data_pagamento.isoformat() if c.data_pagamento else None,
        "motivoCancelamento": c.motivo_cancelamento,
        "createdAt": c.created_at.isoformat(), "updatedAt": c.updated_at.isoformat(),
    }

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
        print(f"[INIT] Conectando ao banco: {DB_HOST}:{DB_PORT}/{DB_NAME} (usuário: {DB_USER})")
        Base.metadata.create_all(engine)
        print("[INIT] Tabelas criadas com sucesso")
        
        with SessionLocal() as db:
            tenant = db.query(Tenant).filter_by(slug="kealex").first()
            if not tenant:
                now = datetime.utcnow()
                tenant = Tenant(
                    nome="Kealex", slug="kealex", plano="admin",
                    trial_started_at=None, trial_expires_at=None,
                )
                db.add(tenant)
                db.flush()
                print("[INIT] Tenant criado")
            else:
                # tenant admin nunca expira
                if tenant.plano == "trial" and tenant.trial_started_at is None:
                    tenant.plano = "admin"
                    db.flush()
            
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
        print(f"[ERRO] Verifique as credenciais: {DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
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
        KEALEX_SECRET_KEY, ALGORITHM
    )

def verify_token(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    try:
        return jwt.decode(creds.credentials, KEALEX_SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(401, "Token inválido")

# Helper functions
def _processo_to_dict(p: Processo, cliente: Cliente = None, db: Session = None):
    fases = []
    if db and hasattr(p, 'id'):
        fases = db.query(Fase).filter_by(processo_id=p.id).order_by(Fase.ordem).all()
    return {
        "id": p.id, "tenantId": p.tenant_id, "userId": p.user_id, "escritorioId": p.escritorio_id,
        "numero": p.numero, "titulo": p.titulo, "descricao": p.descricao, "status": p.status,
        "advogadoId": p.advogado_id, "clienteId": p.cliente_id,
        "clienteNome": cliente.nome if cliente else None,
        "clienteEmail": cliente.email if cliente else None,
        "vara": p.vara, "tribunal": p.tribunal,
        "fases": [{"id": f.id, "label": f.label, "ordem": f.ordem, "status": f.status, "dataConclusao": f.data_conclusao.isoformat() if f.data_conclusao else None} for f in fases],
        "createdAt": p.created_at.isoformat(), "updatedAt": p.updated_at.isoformat()
    }

def _enrich_processos(db: Session, processos: list[Processo]):
    ids = list({p.cliente_id for p in processos})
    clientes = {c.id: c for c in db.query(Cliente).filter(Cliente.id.in_(ids)).all()}
    return [_processo_to_dict(p, clientes.get(p.cliente_id), db) for p in processos]

# Pydantic models
class LoginIn(BaseModel):
    email: EmailStr
    senha: str

class RegisterIn(BaseModel):
    nome:     str
    email:    EmailStr
    cpfCnpj:  str = ""
    whatsapp: str
    senha:    str
    perfil:   str = "advogado"
    # whatsapp já inclui máscara do frontend, ex: (11) 99999-9999

class AuthUser(BaseModel):
    id:             str
    nome:           str
    email:          str
    role:           str
    tenantId:       str
    accessToken:    str
    plano:          str           = "trial"
    subscriptionStatus: str | None = None
    trialStartedAt: str | None    = None
    trialExpiresAt: str | None    = None
    subscriptionExpiresAt: str | None = None

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

class AudienciaIn(BaseModel):
    processoId: str = ""
    processoTitulo: str = ""
    tipo: str = ""
    dataHora: str = ""
    local: str = ""
    juiz: str | None = None
    partes: str | None = None
    observacoes: str | None = None
    roteiro: str | None = None
    status: str = "agendada"

class AudienciaUpdateIn(AudienciaIn):
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
cors_allowed_origins = [
    origin.strip()
    for origin in os.getenv("KEALEX_CORS_ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

@app.on_event("startup")
def startup_event():
    _init_db()

# ── Assinatura (Asaas) ───────────────────────────────────────────────────────

import hmac as _hmac
import json as _json

KEALEX_ASAAS_API_KEY = os.getenv("KEALEX_ASAAS_API_KEY", "")
ASAAS_BASE = os.getenv("KEALEX_ASAAS_BASE_URL", "").rstrip("/")
KEALEX_ASAAS_WEBHOOK_TOKEN = os.getenv("KEALEX_ASAAS_WEBHOOK_TOKEN", "")

def _verify_webhook_token(token: str | None) -> bool:
    """Valida o token do webhook usando comparação segura contra timing attacks."""
    if not KEALEX_ASAAS_WEBHOOK_TOKEN or not token:
        return False
    return _hmac.compare_digest(
        token.encode("utf-8"),
        KEALEX_ASAAS_WEBHOOK_TOKEN.encode("utf-8"),
    )

PLANOS = {
    "starter":      {"value": 197.00, "description": "Plano Starter"},
    "professional": {"value": 397.00, "description": "Plano Professional"},
}

def _calcular_valor(valor_mensal: float, periodicidade: str) -> tuple[float, int]:
    """Retorna (valor_total, installmentCount). Trimestral = 3x com 5% de desconto."""
    if periodicidade == "trimestral":
        return round(valor_mensal * 3 * 0.95, 2), 3
    return valor_mensal, 1

def _digits(value: str | None) -> str | None:
    if value is None: return None
    return "".join(c for c in value if c.isdigit())

class CreditCardIn(BaseModel):
    holderName: str; number: str; expiryMonth: str; expiryYear: str; ccv: str

class HolderInfoIn(BaseModel):
    name: str; email: str; cpfCnpj: str; postalCode: str; addressNumber: str
    addressComplement: str | None = None; phone: str | None = None; mobilePhone: str | None = None
    address: str | None = None; neighborhood: str | None = None; city: str | None = None; state: str | None = None

class AssinarIn(BaseModel):
    plano: str; asaasCustomerId: str; periodicidade: str = "mensal"
    creditCard: CreditCardIn; holderInfo: HolderInfoIn; remoteIp: str = "127.0.0.1"

class AssinarOut(BaseModel):
    subscriptionId: str; plano: str; periodicidade: str; status: str
    nextDueDate: str; value: float; valorMensal: float; desconto: float

class AssinarPreviewOut(BaseModel):
    plano: str; descricaoPlano: str; periodicidade: str
    valorMensal: float; valorTotal: float; desconto: float
    nextDueDate: str
    titular: str; email: str; cpfCnpj: str
    cartaoFinal: str  # últimos 4 dígitos
    mensagem: str

class AssinarPixIn(BaseModel):
    plano: str; asaasCustomerId: str; periodicidade: str = "mensal"

class AssinarPixOut(BaseModel):
    subscriptionId: str; plano: str; periodicidade: str; status: str
    nextDueDate: str; value: float; valorMensal: float; desconto: float
    pixQrCode: str; pixKey: str; pixExpiresAt: str

class PreRegisterIn(BaseModel):
    nome: str; email: EmailStr; senha: str

class PreRegisterOut(BaseModel):
    userId: str; tenantId: str; token: str

@app.post("/k1/lex/auth/pre-register", response_model=PreRegisterOut, status_code=201)
def pre_register(body: PreRegisterIn, db: Session = Depends(get_db)):
    if len(body.senha) < 6:
        raise HTTPException(400, "Senha deve ter no minimo 6 caracteres")
    if db.query(Usuario).filter_by(email=body.email).first():
        raise HTTPException(409, "E-mail ja cadastrado.")
    slug = body.email.split("@")[0].lower().replace(".", "-")[:80]
    base_slug, counter = slug, 1
    while db.query(Tenant).filter_by(slug=slug).first():
        slug = f"{base_slug}-{counter}"; counter += 1
    now = datetime.utcnow()
    tenant = Tenant(nome=body.nome, slug=slug, plano="trial",
                    trial_started_at=now, trial_expires_at=now + timedelta(days=TRIAL_DAYS), ativo=True)
    db.add(tenant); db.flush()
    user = Usuario(tenant_id=tenant.id, nome=body.nome, email=body.email,
                   senha_hash=_hash(body.senha), role=RoleEnum.advogado, ativo=True)
    db.add(user); db.commit(); db.refresh(user)
    token = jwt.encode(
        {"sub": user.id, "role": user.role, "tenant_id": tenant.id,
         "exp": datetime.utcnow() + timedelta(hours=2), "pre": True},
        KEALEX_SECRET_KEY, ALGORITHM)
    return PreRegisterOut(userId=user.id, tenantId=tenant.id, token=token)

@app.post("/k1/lex/auth/criar-cliente-asaas")
def criar_cliente_asaas(body: HolderInfoIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    if not ASAAS_BASE:
        raise HTTPException(503, "Integracao Asaas nao configurada")
    tenant = db.query(Tenant).filter_by(id=payload.get("tenant_id")).first()
    if not tenant: raise HTTPException(404, "Tenant nao encontrado")
    customer_data = {k: v for k, v in {
        "name": body.name, "email": body.email, "cpfCnpj": _digits(body.cpfCnpj),
        "phone": _digits(body.phone), "mobilePhone": _digits(body.mobilePhone),
        "postalCode": _digits(body.postalCode), "addressNumber": body.addressNumber,
        "complement": body.addressComplement, "address": body.address,
        "province": body.neighborhood, "city": body.city,
    }.items() if v not in (None, "")}
    headers = {"access_token": KEALEX_ASAAS_API_KEY, "Content-Type": "application/json", "User-Agent": "Kealex/1.0.0"}
    try:
        if tenant.asaas_customer_id:
            resp = httpx.put(f"{ASAAS_BASE}/customers/{tenant.asaas_customer_id}", json=customer_data, headers=headers, timeout=15)
        else:
            resp = httpx.post(f"{ASAAS_BASE}/customers", json=customer_data, headers=headers, timeout=15)
        if resp.status_code not in (200, 201):
            raise HTTPException(422, f"Asaas recusou: {resp.json().get('errors', resp.text)}")
        customer_id = tenant.asaas_customer_id or resp.json().get("id")
        tenant.asaas_customer_id = customer_id
        tenant.billing_name = body.name
        tenant.billing_email = body.email
        tenant.billing_cpf_cnpj = _digits(body.cpfCnpj)
        tenant.billing_phone = _digits(body.phone)
        tenant.billing_mobile_phone = _digits(body.mobilePhone)
        tenant.billing_postal_code = _digits(body.postalCode)
        tenant.billing_address = body.address
        tenant.billing_address_number = body.addressNumber
        tenant.billing_complement = body.addressComplement
        tenant.billing_neighborhood = body.neighborhood
        tenant.billing_city = body.city
        tenant.billing_state = body.state
        db.commit()
        return {"customerId": customer_id}
    except httpx.TimeoutException:
        raise HTTPException(504, "Timeout ao conectar com Asaas")

@app.post("/k1/lex/auth/assinar/preview", response_model=AssinarPreviewOut)
def assinar_preview(body: AssinarIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    plano_cfg = PLANOS.get(body.plano)
    if not plano_cfg: raise HTTPException(400, f"Plano invalido: {body.plano}")
    tenant = db.query(Tenant).filter_by(id=payload.get("tenant_id")).first()
    if not tenant: raise HTTPException(404, "Tenant nao encontrado")
    if tenant.asaas_customer_id != body.asaasCustomerId:
        raise HTTPException(403, "Cliente Asaas nao vinculado a esta conta")
    valor_mensal = plano_cfg["value"]
    valor_total, _ = _calcular_valor(valor_mensal, body.periodicidade)
    desconto = round(valor_mensal * (3 if body.periodicidade == "trimestral" else 1) - valor_total, 2)
    now = datetime.utcnow()
    next_due = tenant.trial_expires_at.strftime("%Y-%m-%d") if tenant.plano == "trial" and tenant.trial_expires_at and tenant.trial_expires_at > now else (now + timedelta(days=1)).strftime("%Y-%m-%d")
    cartao_final = body.creditCard.number[-4:] if body.creditCard.number else "****"
    mensagem = (
        f"Voce esta contratando o {plano_cfg['description']} no ciclo {'trimestral com 5% de desconto' if body.periodicidade == 'trimestral' else 'mensal'}. "
        f"O valor de R$ {valor_total:.2f} sera cobrado em {next_due} no cartao terminado em {cartao_final}. "
        f"Clique em Confirmar para finalizar a contratacao."
    )
    return AssinarPreviewOut(
        plano=body.plano, descricaoPlano=plano_cfg["description"],
        periodicidade=body.periodicidade, valorMensal=valor_mensal,
        valorTotal=valor_total, desconto=desconto, nextDueDate=next_due,
        titular=body.holderInfo.name, email=body.holderInfo.email,
        cpfCnpj=body.holderInfo.cpfCnpj[-4:].rjust(len(body.holderInfo.cpfCnpj), "*"),
        cartaoFinal=cartao_final, mensagem=mensagem,
    )

@app.post("/k1/lex/auth/assinar", response_model=AssinarOut)
def assinar(body: AssinarIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    if not ASAAS_BASE:
        raise HTTPException(503, "Integracao Asaas nao configurada")
    plano_cfg = PLANOS.get(body.plano)
    if not plano_cfg: raise HTTPException(400, f"Plano invalido: {body.plano}")
    tenant = db.query(Tenant).filter_by(id=payload.get("tenant_id")).first()
    if not tenant: raise HTTPException(404, "Tenant nao encontrado")
    if tenant.asaas_customer_id != body.asaasCustomerId:
        raise HTTPException(403, "Cliente Asaas nao vinculado a esta conta")
    if tenant.asaas_subscription_id:
        _h = {"access_token": KEALEX_ASAAS_API_KEY, "Content-Type": "application/json", "User-Agent": "Kealex/1.0.0"}
        try:
            _r = httpx.get(f"{ASAAS_BASE}/subscriptions/{tenant.asaas_subscription_id}", headers=_h, timeout=10)
            asaas_status = _r.json().get("status", "") if _r.status_code == 200 else ""
        except Exception:
            asaas_status = ""
        if asaas_status == "ACTIVE":
            raise HTTPException(409, "Ja existe uma assinatura ativa vinculada a esta conta")
        # Cancela assinatura pendente/inativa no Asaas antes de criar nova
        try:
            httpx.delete(f"{ASAAS_BASE}/subscriptions/{tenant.asaas_subscription_id}", headers=_h, timeout=10)
        except Exception:
            pass
        logging.warning("[ASSINAR] Assinatura anterior cancelada asaas_status=%s tenant=%s",
                        asaas_status, tenant.id)
        tenant.asaas_subscription_id = None
        tenant.subscription_status = "trialing"
        db.commit()
    valor_mensal = plano_cfg["value"]
    valor_total, installment_count = _calcular_valor(valor_mensal, body.periodicidade)
    desconto = round(valor_mensal * (3 if body.periodicidade == "trimestral" else 1) - valor_total, 2)
    now = datetime.utcnow()
    next_due = tenant.trial_expires_at.strftime("%Y-%m-%d") if tenant.plano == "trial" and tenant.trial_expires_at and tenant.trial_expires_at > now else (now + timedelta(days=1)).strftime("%Y-%m-%d")
    headers = {"access_token": KEALEX_ASAAS_API_KEY, "Content-Type": "application/json", "User-Agent": "Kealex/1.0.0"}
    subscription_payload = {
        "customer": body.asaasCustomerId, "billingType": "CREDIT_CARD",
        "nextDueDate": next_due, "value": valor_total, "cycle": "MONTHLY",
        "description": f"{plano_cfg['description']} ({'Trimestral' if body.periodicidade == 'trimestral' else 'Mensal'})",
        "creditCard": {"holderName": body.creditCard.holderName, "number": body.creditCard.number,
                       "expiryMonth": body.creditCard.expiryMonth, "expiryYear": body.creditCard.expiryYear, "ccv": body.creditCard.ccv},
        "creditCardHolderInfo": {k: v for k, v in {
            "name": body.holderInfo.name, "email": body.holderInfo.email,
            "cpfCnpj": _digits(body.holderInfo.cpfCnpj), "postalCode": _digits(body.holderInfo.postalCode),
            "addressNumber": body.holderInfo.addressNumber,
            "addressComplement": body.holderInfo.addressComplement,
            "phone": _digits(body.holderInfo.phone) or _digits(body.holderInfo.mobilePhone),
        }.items() if v not in (None, "")},
        "remoteIp": body.remoteIp,
    }
    if body.periodicidade == "trimestral":
        subscription_payload["installmentCount"] = 3
        subscription_payload["installmentValue"] = round(valor_total / 3, 2)
    try:
        resp = httpx.post(f"{ASAAS_BASE}/subscriptions", headers=headers, timeout=20, json=subscription_payload)
        if resp.status_code not in (200, 201):
            raise HTTPException(422, f"Asaas recusou: {resp.json().get('errors', resp.text)}")
        data = resp.json()
    except httpx.TimeoutException:
        raise HTTPException(504, "Timeout ao conectar com Asaas")
    # Salva como pending e aguarda webhook para ativar — não polling de status
    tenant.asaas_subscription_id = data.get("id")
    tenant.subscription_plan = body.plano
    tenant.subscription_status = "pending"
    tenant.next_due_date = data.get("nextDueDate", next_due)
    tenant.updated_at = datetime.utcnow()
    db.commit()
    return AssinarOut(subscriptionId=data.get("id", ""), plano=body.plano, periodicidade=body.periodicidade,
                      status="PENDING",
                      nextDueDate=data.get("nextDueDate", next_due),
                      value=valor_total, valorMensal=valor_mensal, desconto=desconto)

@app.post("/k1/lex/auth/assinar-pix", response_model=AssinarPixOut)
def assinar_pix(body: AssinarPixIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    if not ASAAS_BASE:
        raise HTTPException(503, "Integracao Asaas nao configurada")
    plano_cfg = PLANOS.get(body.plano)
    if not plano_cfg: raise HTTPException(400, f"Plano invalido: {body.plano}")
    tenant = db.query(Tenant).filter_by(id=payload.get("tenant_id")).first()
    if not tenant: raise HTTPException(404, "Tenant nao encontrado")
    if tenant.asaas_customer_id != body.asaasCustomerId:
        raise HTTPException(403, "Cliente Asaas nao vinculado a esta conta")
    if tenant.asaas_subscription_id and tenant.subscription_status in ("active", "past_due"):
        raise HTTPException(409, "Ja existe uma assinatura ativa vinculada a esta conta")
    valor_mensal = plano_cfg["value"]
    valor_total, installment_count = _calcular_valor(valor_mensal, body.periodicidade)
    desconto = round(valor_mensal * (3 if body.periodicidade == "trimestral" else 1) - valor_total, 2)
    now = datetime.utcnow()
    next_due = tenant.trial_expires_at.strftime("%Y-%m-%d") if tenant.plano == "trial" and tenant.trial_expires_at and tenant.trial_expires_at > now else (now + timedelta(days=1)).strftime("%Y-%m-%d")
    headers = {"access_token": KEALEX_ASAAS_API_KEY, "Content-Type": "application/json", "User-Agent": "Kealex/1.0.0"}
    pix_payload = {
        "customer": body.asaasCustomerId, "billingType": "PIX",
        "nextDueDate": next_due, "value": valor_total, "cycle": "MONTHLY",
        "description": f"{plano_cfg['description']} ({'Trimestral' if body.periodicidade == 'trimestral' else 'Mensal'})",
    }
    if body.periodicidade == "trimestral":
        pix_payload["installmentCount"] = 3
        pix_payload["installmentValue"] = round(valor_total / 3, 2)
    try:
        # 1. Criar assinatura PIX
        resp = httpx.post(f"{ASAAS_BASE}/subscriptions", headers=headers, timeout=20, json=pix_payload)
        if resp.status_code not in (200, 201):
            raise HTTPException(422, f"Asaas recusou: {resp.json().get('errors', resp.text)}")
        subscription_id = resp.json()["id"]
        # 2. Buscar pagamento gerado
        resp = httpx.get(f"{ASAAS_BASE}/payments", headers=headers, timeout=15,
                         params={"subscription": subscription_id, "limit": 1})
        payments = resp.json().get("data", [])
        if not payments: raise HTTPException(422, "Nenhum pagamento gerado para a assinatura PIX")
        payment_id = payments[0]["id"]
        due_date = payments[0].get("dueDate", next_due)
        # 3. Buscar QR Code
        resp = httpx.get(f"{ASAAS_BASE}/payments/{payment_id}/pixQrCode", headers=headers, timeout=15)
        if resp.status_code != 200:
            raise HTTPException(422, f"Erro ao obter QR Code PIX: {resp.text}")
        qr_data = resp.json()
    except httpx.TimeoutException:
        raise HTTPException(504, "Timeout ao conectar com Asaas")
    tenant.asaas_subscription_id = subscription_id
    tenant.subscription_plan = body.plano
    tenant.subscription_status = "pending"
    tenant.next_due_date = due_date
    tenant.updated_at = datetime.utcnow()
    if not tenant.ativo:
        tenant.ativo = True
        db.query(Usuario).filter_by(tenant_id=tenant.id).update({"ativo": True})
    db.commit()
    return AssinarPixOut(
        subscriptionId=subscription_id, plano=body.plano, periodicidade=body.periodicidade,
        status="PENDING", nextDueDate=due_date,
        value=valor_total, valorMensal=valor_mensal, desconto=desconto,
        pixQrCode=qr_data.get("encodedImage", ""),
        pixKey=qr_data.get("payload", ""),
        pixExpiresAt=qr_data.get("expirationDate") or (now + timedelta(hours=24)).isoformat(),
    )

@app.post("/k1/lex/auth/asaas-webhook")
async def asaas_webhook(
    request: Request,
    db: Session = Depends(get_db),
    access_token: str | None = Header(default=None, alias="asaas-access-token"),
):
    if not _verify_webhook_token(access_token):
        logging.warning("[WEBHOOK] Token invalido recebido: %s", access_token)
        raise HTTPException(401, "Webhook nao autenticado")

    raw_body = await request.body()
    try:
        event = _json.loads(raw_body)
    except _json.JSONDecodeError:
        raise HTTPException(400, "Payload invalido")

    event_id   = event.get("id") or str(uuid.uuid4())
    event_name = event.get("event", "")

    # ── Idempotência: ignora eventos já processados ──────────────────────────
    if db.get(AsaasWebhookEvent, event_id):
        logging.info("[WEBHOOK] Evento duplicado ignorado: %s", event_id)
        return {"ok": True, "duplicated": True}

    db.add(AsaasWebhookEvent(
        id=event_id,
        event=event_name,
    ))

    # ── Extrai subscription_id ───────────────────────────────────────────────
    payment      = event.get("payment") or {}
    subscription = event.get("subscription") or {}
    subscription_id = (
        payment.get("subscription")
        or subscription.get("id")
        or payment.get("subscriptionId")
    )

    if not subscription_id:
        logging.info("[WEBHOOK] Evento sem subscription_id ignorado: %s", event_name)
        db.commit()
        return {"ok": True, "ignored": True}

    tenant = db.query(Tenant).filter_by(asaas_subscription_id=subscription_id).first()
    if not tenant:
        logging.warning("[WEBHOOK] Tenant nao encontrado para subscription: %s", subscription_id)
        db.commit()
        return {"ok": True, "tenant_not_found": True}

    logging.info("[WEBHOOK] Processando evento=%s subscription=%s tenant=%s",
                 event_name, subscription_id, tenant.id)

    # ── Transições de estado ─────────────────────────────────────────────────
    if event_name in ("PAYMENT_CONFIRMED", "PAYMENT_RECEIVED"):
        tenant.subscription_status = "active"
        tenant.plano = tenant.subscription_plan or tenant.plano
        tenant.ativo = True
        if payment.get("dueDate"):
            tenant.next_due_date = payment["dueDate"]
        db.query(Usuario).filter_by(tenant_id=tenant.id).update({"ativo": True})

    elif event_name == "PAYMENT_OVERDUE":
        tenant.subscription_status = "past_due"

    elif event_name in ("SUBSCRIPTION_DELETED", "PAYMENT_DELETED"):
        tenant.subscription_status = "canceled"
        tenant.ativo = False
        db.query(Usuario).filter_by(tenant_id=tenant.id).update({"ativo": False})

    elif event_name == "PAYMENT_REFUNDED":
        tenant.subscription_status = "inactive"

    elif event_name == "SUBSCRIPTION_UPDATED":
        if subscription.get("nextDueDate"):
            tenant.next_due_date = subscription["nextDueDate"]

    tenant.updated_at = datetime.utcnow()
    db.commit()
    logging.info("[WEBHOOK] Tenant %s atualizado: status=%s plano=%s",
                 tenant.id, tenant.subscription_status, tenant.plano)
    return {"ok": True}

@app.get("/k1/lex/auth/billing-status")
def billing_status(db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant = db.query(Tenant).filter_by(id=payload.get("tenant_id")).first()
    if not tenant: raise HTTPException(404, "Tenant nao encontrado")
    now = datetime.utcnow()
    if not tenant.ativo:
        status = "inactive"
    elif tenant.plano == "trial":
        status = "trial_expired" if tenant.trial_expires_at and tenant.trial_expires_at <= now else "trial"
    elif tenant.plano in ("starter", "professional", "enterprise"):
        status = tenant.subscription_status or "inactive"
    else:
        status = "inactive"
    return {"plano": tenant.plano, "status": status, "subscriptionStatus": tenant.subscription_status,
            "nextDueDate": tenant.next_due_date,
            "trialExpiresAt": tenant.trial_expires_at.isoformat() if tenant.trial_expires_at else None}

@app.get("/k1/lex/auth/billing-profile")
def billing_profile_v2(db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant = db.query(Tenant).filter_by(id=payload.get("tenant_id")).first()
    if not tenant: raise HTTPException(404, "Tenant nao encontrado")
    return {
        "name": tenant.billing_name or "",
        "email": tenant.billing_email or "",
        "cpfCnpj": tenant.billing_cpf_cnpj or "",
        "phone": tenant.billing_phone or "",
        "mobilePhone": tenant.billing_mobile_phone or "",
        "postalCode": tenant.billing_postal_code or "",
        "address": tenant.billing_address or "",
        "addressNumber": tenant.billing_address_number or "",
        "addressComplement": tenant.billing_complement or "",
        "neighborhood": tenant.billing_neighborhood or "",
        "city": tenant.billing_city or "",
        "state": tenant.billing_state or "",
    }

@app.patch("/k1/lex/auth/billing-profile")
def update_billing_profile(body: HolderInfoIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    """Atualiza dados do titular sem criar novo registro."""
    tenant = db.query(Tenant).filter_by(id=payload.get("tenant_id")).first()
    if not tenant: raise HTTPException(404, "Tenant nao encontrado")
    if body.name: tenant.billing_name = body.name
    if body.email: tenant.billing_email = body.email
    if body.cpfCnpj: tenant.billing_cpf_cnpj = _digits(body.cpfCnpj)
    if body.phone: tenant.billing_phone = _digits(body.phone)
    if body.mobilePhone: tenant.billing_mobile_phone = _digits(body.mobilePhone)
    if body.postalCode: tenant.billing_postal_code = _digits(body.postalCode)
    if body.address: tenant.billing_address = body.address
    if body.addressNumber: tenant.billing_address_number = body.addressNumber
    if body.addressComplement is not None: tenant.billing_complement = body.addressComplement
    if body.neighborhood: tenant.billing_neighborhood = body.neighborhood
    if body.city: tenant.billing_city = body.city
    if body.state: tenant.billing_state = body.state
    tenant.updated_at = datetime.utcnow()
    db.commit()
    return {"ok": True}


class ActivityCreateIn(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    description: str = Field(default="", max_length=5000)
    status: str = Field(default="todo", min_length=1, max_length=36)
    priority: str = "media"
    dueDate: date | None = None

class ActivityUpdateIn(BaseModel):
    id: str
    title: str | None = Field(default=None, min_length=1, max_length=180)
    description: str | None = Field(default=None, max_length=5000)
    status: str | None = Field(default=None, min_length=1, max_length=36)
    priority: str | None = None
    dueDate: date | None = None

class ActivityColumnCreateIn(BaseModel):
    title: str = Field(min_length=1, max_length=80)
    color: str = Field(default="#087E96", pattern=r"^#[0-9A-Fa-f]{6}$")

class ActivityColumnUpdateIn(BaseModel):
    id: str
    title: str | None = Field(default=None, min_length=1, max_length=80)
    color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")

class ActivityIdIn(BaseModel):
    id: str

_ACTIVITY_DEFAULT_COLUMNS = [
    {"id": "todo", "title": "A Fazer", "color": "#087E96"},
    {"id": "in_progress", "title": "Em Andamento", "color": "#D97706"},
    {"id": "done", "title": "Concluído", "color": "#16834F"},
]

def _activity_owner(payload: dict) -> tuple[str, str]:
    user_id, tenant_id = payload.get("sub"), payload.get("tenant_id")
    if not user_id or not tenant_id:
        raise HTTPException(401, "Token sem usuário ou escritório associado")
    return str(user_id), str(tenant_id)

def _ensure_activity_columns(db: Session, user_id: str, tenant_id: str):
    columns = db.query(ActivityColumn).filter_by(user_id=user_id, tenant_id=tenant_id).order_by(ActivityColumn.position).all()
    if columns:
        return columns
    now = datetime.utcnow()
    columns = [
        ActivityColumn(**definition, user_id=user_id, tenant_id=tenant_id, position=position, created_at=now, updated_at=now)
        for position, definition in enumerate(_ACTIVITY_DEFAULT_COLUMNS)
    ]
    db.add_all(columns)
    db.commit()
    return db.query(ActivityColumn).filter_by(user_id=user_id, tenant_id=tenant_id).order_by(ActivityColumn.position).all()

def _activity_column_json(column: ActivityColumn) -> dict:
    return {
        "id": column.id, "title": column.title, "color": column.color,
        "position": column.position, "createdAt": column.created_at.isoformat(),
        "updatedAt": column.updated_at.isoformat(),
    }

def _activity_json(activity: Activity) -> dict:
    return {
        "id": activity.id, "userId": activity.user_id, "title": activity.title,
        "description": activity.description, "status": activity.status, "priority": activity.priority,
        "dueDate": activity.due_date.isoformat() if activity.due_date else None,
        "createdAt": activity.created_at.isoformat(), "updatedAt": activity.updated_at.isoformat(),
    }

@app.get("/k1/lex/activities/columns")
def hub_list_activity_columns(payload=Depends(verify_token), db: Session = Depends(get_db)):
    user_id, tenant_id = _activity_owner(payload)
    return [_activity_column_json(row) for row in _ensure_activity_columns(db, user_id, tenant_id)]

@app.post("/k1/lex/activities/columns", status_code=201)
def hub_create_activity_column(body: ActivityColumnCreateIn, payload=Depends(verify_token), db: Session = Depends(get_db)):
    user_id, tenant_id = _activity_owner(payload)
    columns = _ensure_activity_columns(db, user_id, tenant_id)
    title = body.title.strip()
    if not title:
        raise HTTPException(400, "O nome da coluna é obrigatório")
    row = ActivityColumn(
        id=uuid.uuid4().hex[:20], user_id=user_id, tenant_id=tenant_id, title=title,
        color=body.color.upper(), position=max((column.position for column in columns), default=-1) + 1,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _activity_column_json(row)

@app.post("/k1/lex/activities/columns/update")
def hub_update_activity_column(body: ActivityColumnUpdateIn, payload=Depends(verify_token), db: Session = Depends(get_db)):
    user_id, tenant_id = _activity_owner(payload)
    row = db.query(ActivityColumn).filter_by(id=body.id, user_id=user_id, tenant_id=tenant_id).first()
    if not row:
        raise HTTPException(404, "Coluna não encontrada")
    fields = body.model_dump(exclude_unset=True, exclude={"id"})
    if not fields:
        raise HTTPException(400, "Informe o nome ou a cor da coluna")
    for name, value in fields.items():
        if value is None:
            raise HTTPException(400, f"O campo {name} não pode ser nulo")
        if name == "title":
            value = value.strip()
            if not value:
                raise HTTPException(400, "O nome da coluna é obrigatório")
        if name == "color":
            value = value.upper()
        setattr(row, name, value)
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return _activity_column_json(row)

@app.post("/k1/lex/activities/columns/delete")
def hub_delete_activity_column(body: ActivityIdIn, payload=Depends(verify_token), db: Session = Depends(get_db)):
    user_id, tenant_id = _activity_owner(payload)
    row = db.query(ActivityColumn).filter_by(id=body.id, user_id=user_id, tenant_id=tenant_id).first()
    if not row:
        raise HTTPException(404, "Coluna não encontrada")
    if db.query(ActivityColumn).filter_by(user_id=user_id, tenant_id=tenant_id).count() <= 1:
        raise HTTPException(409, "O quadro precisa manter pelo menos uma coluna")
    if db.query(Activity).filter_by(user_id=user_id, tenant_id=tenant_id, status=body.id).first():
        raise HTTPException(409, "Mova as atividades desta coluna antes de excluí-la")
    db.delete(row)
    db.commit()
    return {"ok": True}

@app.get("/k1/lex/activities")
def hub_list_activities(status: str | None = None, payload=Depends(verify_token), db: Session = Depends(get_db)):
    user_id, tenant_id = _activity_owner(payload)
    _ensure_activity_columns(db, user_id, tenant_id)
    query = db.query(Activity).filter(Activity.user_id == user_id, Activity.tenant_id == tenant_id)
    if status is not None:
        if not db.query(ActivityColumn).filter_by(id=status, user_id=user_id, tenant_id=tenant_id).first():
            raise HTTPException(400, "Status de atividade inválido")
        query = query.filter(Activity.status == status)
    return [_activity_json(row) for row in query.order_by(Activity.created_at.desc()).all()]

@app.post("/k1/lex/activities", status_code=201)
def hub_create_activity(body: ActivityCreateIn, payload=Depends(verify_token), db: Session = Depends(get_db)):
    user_id, tenant_id = _activity_owner(payload)
    columns = _ensure_activity_columns(db, user_id, tenant_id)
    if body.status not in {column.id for column in columns}:
        raise HTTPException(400, "Coluna de atividade inválida")
    if body.priority not in {"baixa", "media", "alta"}:
        raise HTTPException(400, "Prioridade inválida")
    title = body.title.strip()
    if not title:
        raise HTTPException(400, "O título da atividade é obrigatório")
    row = Activity(
        user_id=user_id, tenant_id=tenant_id, title=title, description=body.description.strip(),
        status=body.status, priority=body.priority, due_date=body.dueDate,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _activity_json(row)

@app.post("/k1/lex/activities/update")
def hub_update_activity(body: ActivityUpdateIn, payload=Depends(verify_token), db: Session = Depends(get_db)):
    user_id, tenant_id = _activity_owner(payload)
    row = db.query(Activity).filter_by(id=body.id, user_id=user_id, tenant_id=tenant_id).first()
    if not row:
        raise HTTPException(404, "Atividade não encontrada")
    for name, value in body.model_dump(exclude_unset=True, exclude={"id"}).items():
        if name == "status" and value is not None:
            if not db.query(ActivityColumn).filter_by(id=value, user_id=user_id, tenant_id=tenant_id).first():
                raise HTTPException(400, "Coluna de atividade inválida")
        if name == "priority" and value is not None and value not in {"baixa", "media", "alta"}:
            raise HTTPException(400, "Prioridade inválida")
        if name == "title" and value is not None:
            value = value.strip()
            if not value:
                raise HTTPException(400, "O título da atividade é obrigatório")
        if name == "description" and value is not None:
            value = value.strip()
        setattr(row, "due_date" if name == "dueDate" else name, value)
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return _activity_json(row)

@app.post("/k1/lex/activities/delete")
def hub_delete_activity(body: ActivityIdIn, payload=Depends(verify_token), db: Session = Depends(get_db)):
    user_id, tenant_id = _activity_owner(payload)
    row = db.query(Activity).filter_by(id=body.id, user_id=user_id, tenant_id=tenant_id).first()
    if not row:
        raise HTTPException(404, "Atividade não encontrada")
    db.delete(row)
    db.commit()
    return {"ok": True}

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
        tenant = db.query(Tenant).filter_by(id=user.tenant_id).first()
        return AuthUser(
            id=user.id,
            nome=user.nome,
            email=user.email,
            role=user.role,
            tenantId=user.tenant_id,
            accessToken=_make_token(user),
            plano=tenant.plano if tenant else "trial",
            subscriptionStatus=tenant.subscription_status if tenant else None,
            trialStartedAt=tenant.trial_started_at.isoformat() if tenant and tenant.trial_started_at else None,
            trialExpiresAt=tenant.trial_expires_at.isoformat() if tenant and tenant.trial_expires_at else None,
            subscriptionExpiresAt=tenant.subscription_expires_at.isoformat() + "Z" if tenant and tenant.subscription_expires_at else None,
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[LOGIN_ERROR] {type(e).__name__}: {str(e)}")
        import traceback; traceback.print_exc()
        raise HTTPException(500, f"Erro no login: {str(e)}")


@app.post("/k1/lex/auth/register", response_model=AuthUser, status_code=201)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    cpf_cnpj = "".join(filter(str.isdigit, body.cpfCnpj or ""))
    if len(cpf_cnpj) not in (11, 14):
        raise HTTPException(400, "Informe um CPF ou CNPJ válido.")

    if db.query(Usuario).filter_by(email=body.email).first():
        raise HTTPException(409, "E-mail já cadastrado. Acesse /entrar para fazer login.")

    now  = datetime.utcnow()
    slug = body.email.split("@")[0].lower().replace(".", "-")[:80]
    base_slug, counter = slug, 1
    while db.query(Tenant).filter_by(slug=slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1

    tenant = Tenant(
        nome=body.nome,
        slug=slug,
        plano="trial",
        trial_started_at=now,
        trial_expires_at=now + timedelta(days=TRIAL_DAYS),
        email=body.email,
        whatsapp=body.whatsapp,
        billing_cpf_cnpj=cpf_cnpj,
        billing_mobile_phone="".join(filter(str.isdigit, body.whatsapp or "")),
        perfil=body.perfil,
    )
    db.add(tenant)
    db.flush()

    senha_temp = str(uuid.uuid4())[:8]
    user = Usuario(
        tenant_id=tenant.id,
        nome=body.nome,
        email=body.email,
        senha_hash=_hash(body.senha if body.senha else senha_temp),
        role=RoleEnum.advogado,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.refresh(tenant)

    print(f"[REGISTER] novo trial: {body.email} | tenant={tenant.id} | expires={tenant.trial_expires_at}")

    return AuthUser(
        id=user.id,
        nome=user.nome,
        email=user.email,
        role=user.role,
        tenantId=tenant.id,
        accessToken=_make_token(user),
        plano=tenant.plano,
        subscriptionStatus=tenant.subscription_status,
        trialStartedAt=tenant.trial_started_at.isoformat(),
        trialExpiresAt=tenant.trial_expires_at.isoformat(),
        subscriptionExpiresAt=tenant.subscription_expires_at.isoformat() + "Z" if tenant.subscription_expires_at else None,
    )

@app.get("/auth/me")
@app.get("/k1/lex/auth/me")
def me(payload=Depends(verify_token)):
    return payload


@app.get("/k1/lex/processos")
def list_processos(db: Session = Depends(get_db), payload=Depends(verify_token)):
    role, uid, tid = payload.get("role"), payload.get("sub"), payload.get("tenant_id")
    q = db.query(Processo).filter_by(tenant_id=tid)
    
    if role == "cliente":
        q = q.filter_by(cliente_id=uid)
    elif role in ("advogado", "juridico"):
        q = q.filter_by(advogado_id=uid)
    
    return _enrich_processos(db, q.all())

@app.post("/k1/lex/processos/get")
def get_processo(body: ProcessoGetIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    p = db.query(Processo).filter_by(id=body.id, tenant_id=tenant_id).first()
    if not p:
        raise HTTPException(404, "Não encontrado")
    cliente = db.query(Cliente).filter_by(id=p.cliente_id).first()
    return _processo_to_dict(p, cliente, db)

@app.post("/k1/lex/processos", status_code=201)
def create_processo(body: ProcessoIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    cliente = db.query(Cliente).filter_by(id=body.clienteId, tenant_id=tenant_id).first()
    if not cliente:
        raise HTTPException(404, "Cliente não encontrado")
    p = Processo(tenant_id=tenant_id, user_id=payload["sub"], escritorio_id=body.escritorioId,
                 numero=body.numero, titulo=body.titulo, descricao=body.descricao,
                 advogado_id=payload["sub"], cliente_id=body.clienteId, vara=body.vara, tribunal=body.tribunal)
    db.add(p)
    db.flush()
    
    fases_padrao = [
        Fase(id=str(uuid.uuid4()), processo_id=p.id, label="Protocolo", ordem=0, status="ativa"),
        Fase(id=str(uuid.uuid4()), processo_id=p.id, label="Citacao", ordem=1, status="futura"),
        Fase(id=str(uuid.uuid4()), processo_id=p.id, label="Contestacao", ordem=2, status="futura"),
        Fase(id=str(uuid.uuid4()), processo_id=p.id, label="Audiencia", ordem=3, status="futura"),
        Fase(id=str(uuid.uuid4()), processo_id=p.id, label="Sentenca", ordem=4, status="futura"),
        Fase(id=str(uuid.uuid4()), processo_id=p.id, label="Recurso", ordem=5, status="futura"),
        Fase(id=str(uuid.uuid4()), processo_id=p.id, label="Encerrado", ordem=6, status="futura"),
    ]
    for fase in fases_padrao:
        db.add(fase)
    db.commit()
    db.refresh(p)
    
    return _processo_to_dict(p, cliente, db)

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
    return _processo_to_dict(p, cliente, db)

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
    
    fase_atual = db.query(Fase).filter_by(processo_id=processo_id, status="ativa").first()
    
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
    
    proxima_fase.status = "ativa"
    proxima_fase.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "ok": True,
        "faseAnterior": {"id": fase_atual.id, "label": fase_atual.label, "status": "concluida"} if fase_atual else None,
        "faseAtual": {"id": proxima_fase.id, "label": proxima_fase.label, "status": "ativa"}
    }

@app.post("/k1/lex/processos/listar-fases")
def listar_fases(body: dict, db: Session = Depends(get_db), payload=Depends(verify_token)):
    processo_id = body.get("processoId") or body.get("processo_id")
    if not processo_id:
        raise HTTPException(400, "processoId obrigatorio")
    
    tenant_id = payload.get("tenant_id")
    p = db.query(Processo).filter_by(id=processo_id, tenant_id=tenant_id).first()
    if not p:
        raise HTTPException(404, "Processo nao encontrado")
    
    fases = db.query(Fase).filter_by(processo_id=processo_id).order_by(Fase.ordem).all()
    return [{"id": f.id, "label": f.label, "ordem": f.ordem, "status": f.status, "dataConclusao": f.data_conclusao.isoformat() if f.data_conclusao else None} for f in fases]

@app.get("/k1/lex/debug/fases/{processo_id}")
def debug_fases(processo_id: str, db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    p = db.query(Processo).filter_by(id=processo_id, tenant_id=tenant_id).first()
    if not p:
        return {"erro": "Processo nao encontrado", "processo_id": processo_id}
    
    fases = db.query(Fase).filter_by(processo_id=processo_id).all()
    return {
        "processo_id": processo_id,
        "processo_numero": p.numero,
        "total_fases": len(fases),
        "fases": [{"id": f.id, "label": f.label, "ordem": f.ordem, "status": f.status} for f in fases]
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

def _audiencia_to_dict(row: Audiencia) -> dict:
    return {
        "id": row.id,
        "tenantId": row.tenant_id,
        "userId": row.user_id,
        "processoId": row.processo_id or "",
        "processoTitulo": row.processo_titulo,
        "tipo": row.tipo,
        "dataHora": row.data_hora,
        "local": row.local,
        "juiz": row.juiz,
        "partes": row.partes,
        "observacoes": row.observacoes,
        "roteiro": row.roteiro,
        "status": row.status,
        "createdAt": row.created_at.isoformat(),
        "updatedAt": row.updated_at.isoformat(),
    }

@app.get("/audiencias")
@app.get("/k1/lex/audiencias")
def list_audiencias(db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    rows = db.query(Audiencia).filter_by(tenant_id=tenant_id).order_by(Audiencia.data_hora.asc()).all()
    return [_audiencia_to_dict(row) for row in rows]

@app.post("/audiencias", status_code=201)
@app.post("/k1/lex/audiencias", status_code=201)
def create_audiencia(body: AudienciaIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    row = Audiencia(
        tenant_id=payload.get("tenant_id"), user_id=payload.get("sub"),
        processo_id=body.processoId or None, processo_titulo=body.processoTitulo,
        tipo=body.tipo, data_hora=body.dataHora, local=body.local,
        juiz=body.juiz, partes=body.partes, observacoes=body.observacoes,
        roteiro=body.roteiro, status=body.status or "agendada",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _audiencia_to_dict(row)

@app.post("/audiencias/update")
@app.post("/k1/lex/audiencias/update")
def update_audiencia(body: AudienciaUpdateIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    row = db.query(Audiencia).filter_by(id=body.id, tenant_id=payload.get("tenant_id")).first()
    if not row:
        raise HTTPException(404, "Audiência não encontrada")
    data = body.model_dump(exclude_unset=True, exclude={"id"})
    fields = {"processoId": "processo_id", "processoTitulo": "processo_titulo", "dataHora": "data_hora"}
    for name, value in data.items():
        setattr(row, fields.get(name, name), value or None if name in {"juiz", "partes", "observacoes", "roteiro"} else value)
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return _audiencia_to_dict(row)

@app.post("/audiencias/delete")
@app.post("/k1/lex/audiencias/delete")
def delete_audiencia(body: ProcessoDeleteIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    row = db.query(Audiencia).filter_by(id=body.id, tenant_id=payload.get("tenant_id")).first()
    if not row:
        raise HTTPException(404, "Audiência não encontrada")
    db.delete(row)
    db.commit()
    return {"ok": True}

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
    "groq": ["llama-3.3-70b-versatile", "llama-3.1-70b-versatile", "llama-3.1-8b-instant", "llama-3.2-90b-text-preview", "llama-3.2-11b-text-preview", "gemma2-9b-it"],
    "openai": ["gpt-5.5", "gpt-5.4", "gpt-5.4-mini", "gpt-5.4-nano"],
    "google": ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite"],
    "claude": ["claude-opus-5", "claude-sonnet-5", "claude-opus-4-8", "claude-opus-4-7", "claude-sonnet-4-6", "claude-haiku-4-5-20251001"],
    "deepseek": ["deepseek-chat", "deepseek-reasoner"],
}

IA_DEFAULT_MODELS = {"cerebras": "llama-3.3-70b", "groq": "llama-3.3-70b-versatile", "openai": "gpt-5.5", "google": "gemini-3.8-flash", "claude": "claude-sonnet-5", "deepseek": "deepseek-chat"}

def _encrypt_user_api_key(value: str) -> str:
    return API_KEY_FERNET.encrypt(value.encode("utf-8")).decode("ascii")

def _decrypt_user_api_key(value: str) -> str:
    try:
        return API_KEY_FERNET.decrypt(value.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError, UnicodeDecodeError) as exc:
        raise HTTPException(500, "Não foi possível descriptografar uma chave de IA. Configure a mesma chave de criptografia usada ao salvar credenciais.") from exc

def _user_api_key_json(row: UserApiKey) -> dict:
    secret = _decrypt_user_api_key(row.api_key_encrypted)
    return {"id": row.id, "provider": row.provider, "model": row.model, "api_key_masked": "•" * max(4, min(12, len(secret) - 4)) + secret[-4:], "is_active": row.is_active, "created_at": row.created_at, "updated_at": row.updated_at}

def _validate_user_api_key(provider: str, value: str):
    prefixes = {"cerebras": ("csk-",), "groq": ("gsk-", "gsk_"), "openai": ("sk-",), "google": ("AIza",), "claude": ("sk-ant-",), "deepseek": ("sk-",)}
    if provider not in prefixes or not value.startswith(prefixes[provider]):
        raise HTTPException(400, f"A chave API informada não corresponde ao provedor '{provider}'.")

def _current_api_key_owner(db: Session, payload: dict) -> tuple[str, str]:
    user_id = str(payload.get("sub") or "")
    user = db.get(Usuario, user_id) if user_id else None
    if not user or not user.ativo:
        raise HTTPException(401, "Usuário autenticado não encontrado ou inativo.")
    return user.id, user.tenant_id

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
    user_id, tenant_id = _current_api_key_owner(db, payload)
    rows = db.query(UserApiKey).filter_by(user_id=user_id, tenant_id=tenant_id).order_by(UserApiKey.created_at.desc()).all()
    return [_user_api_key_json(row) for row in rows]

@app.post("/k1/lex/configuracoes/ia/minhas-chaves", status_code=201)
def create_my_ia_key(body: UserApiKeyCreate, db: Session = Depends(get_db), payload=Depends(verify_token)):
    user_id, tenant_id = _current_api_key_owner(db, payload)
    _validate_model_provider(body.provider, body.model)
    _validate_user_api_key(body.provider, body.api_key.strip())
    if db.query(UserApiKey).filter_by(user_id=user_id, provider=body.provider, model=body.model).first():
        raise HTTPException(409, "Já existe uma chave cadastrada para este provedor e modelo.")
    if body.is_active:
        db.query(UserApiKey).filter_by(user_id=user_id, tenant_id=tenant_id, is_active=True).update({"is_active": False}, synchronize_session=False)
    row = UserApiKey(tenant_id=tenant_id, user_id=user_id, created_by=user_id, provider=body.provider, model=body.model, api_key_encrypted=_encrypt_user_api_key(body.api_key.strip()), is_active=body.is_active)
    db.add(row)
    db.commit()
    db.refresh(row)
    return _user_api_key_json(row)

@app.put("/k1/lex/configuracoes/ia/minhas-chaves/{key_id}")
def update_my_ia_key(key_id: str, body: UserApiKeyUpdate, db: Session = Depends(get_db), payload=Depends(verify_token)):
    user_id, tenant_id = _current_api_key_owner(db, payload)
    row = db.query(UserApiKey).filter_by(id=key_id, user_id=user_id, tenant_id=tenant_id).first()
    if not row:
        raise HTTPException(404, "Chave de IA não encontrada.")
    provider = body.provider or row.provider
    model = body.model or row.model
    _validate_model_provider(provider, model)
    duplicate = db.query(UserApiKey).filter(UserApiKey.user_id == user_id, UserApiKey.provider == provider, UserApiKey.model == model, UserApiKey.id != row.id).first()
    if duplicate:
        raise HTTPException(409, "Já existe uma chave cadastrada para este provedor e modelo.")
    secret = body.api_key.strip() if body.api_key and body.api_key.strip() else _decrypt_user_api_key(row.api_key_encrypted)
    _validate_user_api_key(provider, secret)
    if body.is_active is True:
        db.query(UserApiKey).filter(UserApiKey.user_id == user_id, UserApiKey.tenant_id == tenant_id, UserApiKey.id != row.id, UserApiKey.is_active.is_(True)).update({"is_active": False}, synchronize_session=False)
    row.provider, row.model, row.api_key_encrypted = provider, model, _encrypt_user_api_key(secret)
    if body.is_active is not None:
        row.is_active = body.is_active
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return _user_api_key_json(row)

@app.delete("/k1/lex/configuracoes/ia/minhas-chaves/{key_id}", status_code=204)
def delete_my_ia_key(key_id: str, db: Session = Depends(get_db), payload=Depends(verify_token)):
    user_id, tenant_id = _current_api_key_owner(db, payload)
    row = db.query(UserApiKey).filter_by(id=key_id, user_id=user_id, tenant_id=tenant_id).first()
    if not row:
        raise HTTPException(404, "Chave de IA não encontrada.")
    db.delete(row)
    db.commit()

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
        raise HTTPException(400, f"O modelo '{model}' não corresponde ao fabricante '{provider}'.")

@app.get("/k1/lex/configuracoes/ia")
def get_ia(db: Session = Depends(get_db), payload=Depends(_require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    active = _get_or_create_cfg_ia(db, tenant_id, user_id)
    provider_cfg = db.get(CfgIaProvider, (tenant_id, active.provider))
    result = _row(active)
    legacy_key = result.pop("api_key", None)
    result["configured"] = bool((provider_cfg.api_key if provider_cfg else None) or legacy_key)
    return result

@app.get("/k1/lex/configuracoes/ia/modelos")
def get_modelos_disponiveis():
    return MODELOS_DISPONIVEIS

@app.get("/k1/lex/configuracoes/ia/ativa")
def get_ia_ativa(db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    active = _get_or_create_cfg_ia(db, tenant_id, user_id)
    provider_cfg = db.get(CfgIaProvider, (tenant_id, active.provider))
    result = _row(active)
    legacy_key = result.pop("api_key", None)
    result["configured"] = bool((provider_cfg.api_key if provider_cfg else None) or legacy_key)
    return result

@app.post("/k1/lex/configuracoes/ia")
def save_ia(body: IaIn, db: Session = Depends(get_db), payload=Depends(_require_admin)):
    data = body.model_dump(exclude_none=True)
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    current = db.get(CfgIa, tenant_id)
    if "provider" in data or "modelo" in data:
        _validate_model_provider(data.get("provider") or (current.provider if current else "cerebras"), data.get("modelo") or (current.modelo if current else IA_DEFAULT_MODELS["cerebras"]))
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

class IaProviderIn(BaseModel):
    api_key: Optional[str] = None
    endpoint_url: Optional[str] = None
    modelo: Optional[str] = None
    max_tokens: Optional[int] = None
    system_prompt: Optional[str] = None
    ativo: Optional[bool] = None

@app.get("/k1/lex/configuracoes/ia/provedores")
def get_ia_provedores(db: Session = Depends(get_db), payload=Depends(_require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    active = _get_or_create_cfg_ia(db, tenant_id, user_id)
    rows = db.query(CfgIaProvider).filter_by(tenant_id=tenant_id).all()
    configs = {}
    for row in rows:
        item = _row(row)
        item["configured"] = bool(item.pop("api_key", None))
        configs[row.provider] = item
    if active.provider not in configs:
        legacy = CfgIaProvider(tenant_id=tenant_id, user_id=user_id, provider=active.provider,
            api_key=active.api_key, modelo=active.modelo or IA_DEFAULT_MODELS.get(active.provider, ""),
            max_tokens=active.max_tokens or 8192, system_prompt=active.system_prompt, ativo=active.ativo)
        db.add(legacy)
        db.commit()
        db.refresh(legacy)
        item = _row(legacy)
        item["configured"] = bool(item.pop("api_key", None))
        configs[legacy.provider] = item
    return {"active_provider": active.provider, "providers": configs}

@app.post("/k1/lex/configuracoes/ia/provedores/{provider}")
def save_ia_provedor(provider: str, body: IaProviderIn, db: Session = Depends(get_db), payload=Depends(_require_admin)):
    if provider not in MODELOS_DISPONIVEIS:
        raise HTTPException(400, "Provider inválido")
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
        row = CfgIaProvider(tenant_id=tenant_id, user_id=user_id, provider=provider, modelo=IA_DEFAULT_MODELS[provider])
        db.add(row)
    for key, value in data.items():
        setattr(row, key, value)
    row.updated_at = datetime.utcnow()
    active = db.get(CfgIa, tenant_id)
    if active and active.provider == provider:
        active.api_key, active.modelo = row.api_key, row.modelo
        active.max_tokens, active.system_prompt, active.ativo = row.max_tokens, row.system_prompt, row.ativo
        active.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    result = _row(row)
    result["configured"] = bool(result.pop("api_key", None))
    return result

@app.post("/k1/lex/configuracoes/ia/provedor-ativo/{provider}")
def set_ia_provedor_ativo(provider: str, db: Session = Depends(get_db), payload=Depends(_require_admin)):
    if provider not in MODELOS_DISPONIVEIS:
        raise HTTPException(400, "Provider inválido")
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_id = payload.get("sub")
    config = db.get(CfgIaProvider, (tenant_id, provider))
    if config is None or not config.api_key:
        raise HTTPException(400, "Configure a chave API deste provedor antes de ativá-lo")
    if not config.ativo:
        raise HTTPException(400, "Habilite este provedor antes de ativá-lo")
    active = _get_or_create_cfg_ia(db, tenant_id, user_id)
    active.provider, active.api_key, active.modelo = provider, config.api_key, config.modelo
    active.max_tokens, active.system_prompt, active.ativo = config.max_tokens, config.system_prompt, config.ativo
    active.updated_at = datetime.utcnow()
    db.commit()
    result = _row(active)
    result.pop("api_key", None)
    result["configured"] = True
    return result

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
        data=_json.dumps({"model": model, "instructions": system_prompt, "input": messages, "max_output_tokens": max_tokens}).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            result = _json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise HTTPException(502, f"A OpenAI respondeu com erro ({exc.code}): {detail[:1000]}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise HTTPException(502, "NÃ£o foi possÃ­vel conectar Ã  OpenAI.") from exc
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
            raise HTTPException(400, "Fabricante de IA não suportado.")
        url, headers = f"{base}/chat/completions", {"Authorization": f"Bearer {api_key}"}
        data = {"model": model, "messages": [{"role": "system", "content": system_prompt}, *messages], "max_tokens": max_tokens}
    headers.update({"Content-Type": "application/json", "Accept": "application/json", "User-Agent": "Kealex-AI/1.0"})
    request = urllib.request.Request(url, data=_json.dumps(data).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            result = _json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        if provider == "groq" and exc.code == 403 and "1010" in detail:
            raise HTTPException(502, "O acesso do servidor ao Groq foi bloqueado pelo Cloudflare (erro 1010). Confira as regras de segurança ou a rota de saída do servidor no provedor.") from exc
        raise HTTPException(502, f"{provider} respondeu com erro ({exc.code}): {detail[:1000]}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise HTTPException(502, f"Não foi possível conectar ao provedor {provider}.") from exc
    if provider == "claude":
        return "".join(part.get("text", "") for part in result.get("content", []))
    if provider == "google":
        return "".join(part.get("text", "") for part in result.get("candidates", [{}])[0].get("content", {}).get("parts", []))
    return result.get("choices", [{}])[0].get("message", {}).get("content", "")

@app.post("/k1/lex/configuracoes/ia/chat")
def chat_ia(body: IaChatIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    user_id, tenant_id = _current_api_key_owner(db, payload)
    personal_active = db.query(UserApiKey).filter_by(user_id=user_id, tenant_id=tenant_id, is_active=True).first()
    messages = [{"role": m.role, "content": m.content[:32000]} for m in body.messages[-50:] if m.role in ("user", "assistant")]
    if not messages or messages[-1]["role"] != "user":
        raise HTTPException(400, "A Ãºltima mensagem deve ser do usuÃ¡rio.")
    if body.agente_id:
        config = db.query(AgenteIA).filter_by(id=body.agente_id, tenant_id=tenant_id, ativo=True, publico=True).first()
        if not config:
            raise HTTPException(404, "Agente de IA nÃ£o encontrado.")
        provider, api_key, model = config.provider, config.api_key, config.modelo
        system_prompt, max_tokens, endpoint_url = config.system_prompt, config.max_tokens or 8192, None
        personal = db.query(UserApiKey).filter_by(user_id=user_id, tenant_id=tenant_id, provider=provider, model=model, is_active=True).first()
        if personal:
            api_key = _decrypt_user_api_key(personal.api_key_encrypted)
    else:
        active = CfgIa(tenant_id=tenant_id, provider=personal_active.provider, api_key=_decrypt_user_api_key(personal_active.api_key_encrypted), modelo=personal_active.model, max_tokens=8192, ativo=True) if personal_active else db.get(CfgIa, tenant_id)
        if not active or not active.ativo:
            raise HTTPException(400, "Nenhum provedor de IA ativo estÃ¡ configurado.")
        config = None if personal_active else db.get(CfgIaProvider, (tenant_id, active.provider))
        provider = active.provider
        api_key = (config.api_key if config else None) or active.api_key
        model = (config.modelo if config else None) or active.modelo
        system_prompt = (config.system_prompt if config else None) or active.system_prompt
        max_tokens = (config.max_tokens if config else None) or active.max_tokens or 8192
        endpoint_url = config.endpoint_url if config else None
    if api_key and model:
        _validate_model_provider(provider, model)
    if provider != "openai":
        if not api_key or not model:
            raise HTTPException(400, f"Configure a chave API e o modelo do provedor {provider}.")
        _validate_model_provider(provider, model)
        content = _provider_response(provider, api_key, model, system_prompt or "Você é um assistente jurídico especializado em direito brasileiro. Responda em português brasileiro.", messages, max_tokens, endpoint_url)
        return {"content": content}
    if provider != "openai":
        raise HTTPException(400, "O chat deste endpoint estÃ¡ configurado para modelos OpenAI.")
    if not api_key or not model:
        raise HTTPException(400, "Configure a chave API e o modelo da OpenAI.")
    content = _openai_response(api_key, model, system_prompt or "VocÃª Ã© um assistente jurÃ­dico especializado em direito brasileiro. Responda em portuguÃªs brasileiro.", messages, max_tokens, endpoint_url)
    return {"content": content}

AI_DEFAULT_MENUS = [
    "/processos", "/documentos", "/prazos", "/atividades", "/financeiro",
    "/cobranca", "/usuarios", "/equipe", "/clientes", "/intimacoes",
    "/audiencias", "/integracao-orgaos", "/ia", "/analise-documentos",
    "/meus-agents", "/configuracoes/ia",
]
AI_DEFAULT_PLANS = [
    ("trial", "Trial"),
    ("starter", "Starter"),
    ("professional", "Professional"),
    ("enterprise", "Enterprise"),
]


def _ai_json_items(value, default):
    if not value:
        return list(default)
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        return list(default)
    return parsed if isinstance(parsed, list) else list(default)


def _ai_plan_key(db: Session, tenant_id: str) -> str:
    value = db.execute(
        sql_text("SELECT plano FROM tenants WHERE id=:tenant_id"),
        {"tenant_id": tenant_id},
    ).scalar()
    return str(value or "trial").strip().lower()


def _effective_ai_policy(db: Session, payload: dict) -> dict:
    user_id, tenant_id = _current_api_key_owner(db, payload)
    plan_key = _ai_plan_key(db, tenant_id)
    plan = db.query(AIPlanPolicy).filter_by(tenant_id=tenant_id, plan_key=plan_key).first()
    user = db.query(AIUserPolicy).filter_by(tenant_id=tenant_id, user_id=user_id).first()
    allowed_roles = _ai_json_items(plan.allowed_roles, ["advogado"]) if plan else ["advogado"]
    models = _ai_json_items(plan.allowed_models, []) if plan else []
    menus = _ai_json_items(plan.allowed_menus, AI_DEFAULT_MENUS) if plan else list(AI_DEFAULT_MENUS)
    if user and user.allowed_models is not None:
        models = _ai_json_items(user.allowed_models, [])
    if user and user.allowed_menus is not None:
        menus = _ai_json_items(user.allowed_menus, [])

    can_create_agents = bool(
        plan
        and plan.can_create_agents
        and str(payload.get("role") or "") in allowed_roles
    )
    if user and user.can_create_agents is not None:
        can_create_agents = bool(user.can_create_agents)

    token_period = datetime.utcnow().strftime("%Y-%m")
    usage = db.query(AITokenUsage).filter_by(
        tenant_id=tenant_id,
        user_id=user_id,
        period=token_period,
    ).first()
    return {
        "plan_key": plan_key,
        "can_create_agents": can_create_agents,
        "allowed_roles": allowed_roles,
        "max_agents": (
            user.max_agents if user and user.max_agents is not None
            else (plan.max_agents if plan else 0)
        ) or 0,
        "allowed_models": models,
        "allowed_menus": menus,
        "monthly_token_limit": (
            user.monthly_token_limit
            if user and user.monthly_token_limit is not None
            else (plan.monthly_token_limit if plan else 0)
        ) or 0,
        "fallback_provider": plan.fallback_provider if plan else None,
        "fallback_model": plan.fallback_model if plan else None,
        "tokens_used": usage.tokens_used if usage else 0,
    }


def _assert_ai_menu(db: Session, payload: dict, path: str):
    policy = _effective_ai_policy(db, payload)
    if path not in policy["allowed_menus"]:
        raise HTTPException(403, "Este recurso de IA não está liberado no plano do usuário.")


class AIPlanPolicyIn(BaseModel):
    can_create_agents: bool = False
    allowed_roles: list[str] = Field(default_factory=lambda: ["advogado"])
    max_agents: int = 0
    allowed_models: list[str] = Field(default_factory=list)
    allowed_menus: list[str] = Field(default_factory=list)
    monthly_token_limit: int = 0
    fallback_provider: Optional[str] = None
    fallback_model: Optional[str] = None


class AIUserPolicyIn(BaseModel):
    can_create_agents: Optional[bool] = None
    max_agents: Optional[int] = None
    allowed_models: Optional[list[str]] = None
    allowed_menus: Optional[list[str]] = None
    monthly_token_limit: Optional[int] = None


@app.get("/k1/lex/ia/politica")
def get_effective_ai_policy(db: Session = Depends(get_db), payload=Depends(verify_token)):
    return _effective_ai_policy(db, payload)


@app.get("/k1/lex/ia/admin/politicas")
def list_ai_plan_policies(db: Session = Depends(get_db), payload=Depends(_require_admin)):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    saved = {
        row.plan_key: row
        for row in db.query(AIPlanPolicy).filter_by(tenant_id=tenant_id).all()
    }
    plans = list(AI_DEFAULT_PLANS)
    known_plans = db.execute(
        sql_text("SELECT DISTINCT plano FROM tenants WHERE plano IS NOT NULL")
    ).scalars().all()
    known_keys = {key for key, _label in plans}
    for known_plan in known_plans:
        key = str(known_plan or "").strip().lower()
        if key and key not in known_keys:
            plans.append((key, key.replace("_", " ").title()))
            known_keys.add(key)

    return [
        {
            "plan_key": key,
            "plan_label": label,
            "can_create_agents": bool(saved[key].can_create_agents) if key in saved else False,
            "allowed_roles": _ai_json_items(saved[key].allowed_roles, ["advogado"]) if key in saved else ["advogado"],
            "max_agents": saved[key].max_agents if key in saved else 0,
            "allowed_models": _ai_json_items(saved[key].allowed_models, []) if key in saved else [],
            "allowed_menus": _ai_json_items(saved[key].allowed_menus, AI_DEFAULT_MENUS) if key in saved else list(AI_DEFAULT_MENUS),
            "monthly_token_limit": saved[key].monthly_token_limit if key in saved else 0,
            "fallback_provider": saved[key].fallback_provider if key in saved else None,
            "fallback_model": saved[key].fallback_model if key in saved else None,
        }
        for key, label in plans
    ]


@app.put("/k1/lex/ia/admin/politicas/{plan_key}")
def save_ai_plan_policy(
    plan_key: str,
    body: AIPlanPolicyIn,
    db: Session = Depends(get_db),
    payload=Depends(_require_admin),
):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    plan_key = plan_key.strip().lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,39}", plan_key):
        raise HTTPException(400, "Identificador de plano inválido.")
    known_plan = db.execute(
        sql_text("SELECT 1 FROM tenants WHERE LOWER(plano)=:plan_key LIMIT 1"),
        {"plan_key": plan_key},
    ).scalar()
    if plan_key not in {key for key, _label in AI_DEFAULT_PLANS} and not known_plan:
        raise HTTPException(400, "Plano inválido.")
    if body.max_agents < 0 or body.monthly_token_limit < 0:
        raise HTTPException(400, "Limites não podem ser negativos.")

    row = db.query(AIPlanPolicy).filter_by(tenant_id=tenant_id, plan_key=plan_key).first()
    if not row:
        row = AIPlanPolicy(tenant_id=tenant_id, plan_key=plan_key)
        db.add(row)
    row.can_create_agents = body.can_create_agents
    row.allowed_roles = json.dumps(body.allowed_roles)
    row.max_agents = body.max_agents
    row.allowed_models = json.dumps(body.allowed_models)
    row.allowed_menus = json.dumps(body.allowed_menus)
    row.monthly_token_limit = body.monthly_token_limit
    row.fallback_provider = body.fallback_provider
    row.fallback_model = body.fallback_model
    db.commit()
    return {"plan_key": plan_key, **body.model_dump()}


@app.get("/k1/lex/ia/admin/usuarios/{user_id}")
def get_ai_user_policy(
    user_id: str,
    db: Session = Depends(get_db),
    payload=Depends(_require_admin),
):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_exists = db.execute(
        sql_text("SELECT 1 FROM usuarios WHERE id=:user_id AND tenant_id=:tenant_id LIMIT 1"),
        {"user_id": user_id, "tenant_id": tenant_id},
    ).scalar()
    if not user_exists:
        raise HTTPException(404, "Usuário não encontrado neste tenant.")
    row = db.query(AIUserPolicy).filter_by(tenant_id=tenant_id, user_id=user_id).first()
    if not row:
        return {
            "user_id": user_id,
            "can_create_agents": None,
            "max_agents": None,
            "monthly_token_limit": None,
            "allowed_models": None,
            "allowed_menus": None,
        }
    return {
        "user_id": user_id,
        "can_create_agents": row.can_create_agents,
        "max_agents": row.max_agents,
        "monthly_token_limit": row.monthly_token_limit,
        "allowed_models": _ai_json_items(row.allowed_models, []) if row.allowed_models is not None else None,
        "allowed_menus": _ai_json_items(row.allowed_menus, []) if row.allowed_menus is not None else None,
    }


@app.put("/k1/lex/ia/admin/usuarios/{user_id}")
def save_ai_user_policy(
    user_id: str,
    body: AIUserPolicyIn,
    db: Session = Depends(get_db),
    payload=Depends(_require_admin),
):
    tenant_id = payload.get("tenant_id") or payload.get("sub")
    user_exists = db.execute(
        sql_text("SELECT 1 FROM usuarios WHERE id=:user_id AND tenant_id=:tenant_id LIMIT 1"),
        {"user_id": user_id, "tenant_id": tenant_id},
    ).scalar()
    if not user_exists:
        raise HTTPException(404, "Usuário não encontrado neste tenant.")
    if any(value is not None and value < 0 for value in (body.max_agents, body.monthly_token_limit)):
        raise HTTPException(400, "Limites não podem ser negativos.")

    row = db.query(AIUserPolicy).filter_by(tenant_id=tenant_id, user_id=user_id).first()
    if not row:
        row = AIUserPolicy(tenant_id=tenant_id, user_id=user_id)
        db.add(row)
    values = body.model_dump(exclude_unset=True)
    for field in ("allowed_models", "allowed_menus"):
        if field in values and values[field] is not None:
            values[field] = json.dumps(values[field])
    for field, value in values.items():
        setattr(row, field, value)
    db.commit()
    return {"user_id": user_id, **body.model_dump()}


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
    public_agents = []
    for agent in agentes:
        item = _row(agent)
        item.pop("api_key", None)
        item["configured"] = bool(agent.api_key)
        public_agents.append(item)
    return public_agents

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
    
    _validate_model_provider(update_data.get("provider", agente.provider), update_data.get("modelo", agente.modelo))
    
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
    _validate_model_provider(body.provider, body.modelo)
    
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
    _validate_model_provider(update_data.get("provider", agente.provider), update_data.get("modelo", agente.modelo))
    
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


# ── COBRANCAS ──────────────────────────────────────────────────────────────

@app.get("/v1/lex/cobrancas")
@app.get("/k1/lex/cobrancas")
def list_cobrancas(db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    cobrancas = db.query(Cobranca).filter_by(tenant_id=tenant_id).order_by(Cobranca.created_at.desc()).all()
    return [_cobranca_to_dict(c) for c in cobrancas]

@app.post("/v1/lex/cobrancas", status_code=201)
@app.post("/k1/lex/cobrancas", status_code=201)
def create_cobranca(body: dict, db: Session = Depends(get_db), payload=Depends(verify_token)):
    tenant_id = payload.get("tenant_id")
    c = Cobranca(
        id=str(uuid.uuid4()), tenant_id=tenant_id, user_id=payload["sub"],
        processo_id=body.get("processoId"), cliente_id=body.get("clienteId"),
        valor_centavos=body.get("valorCentavos"), status="pendente", fase_atual=0,
        data_vencimento=datetime.fromisoformat(body["dataVencimento"]) if body.get("dataVencimento") else None,
    )
    db.add(c)
    db.flush()
    db.add(HistoricoCobranca(id=str(uuid.uuid4()), cobranca_id=c.id, acao="criada", status_novo="pendente", observacao="Cobrança criada"))
    db.commit()
    db.refresh(c)
    return _cobranca_to_dict(c)

@app.post("/v1/lex/cobrancas/get")
@app.post("/k1/lex/cobrancas/get")
def get_cobranca(body: dict, db: Session = Depends(get_db), payload=Depends(verify_token)):
    c = db.query(Cobranca).filter_by(id=body.get("id"), tenant_id=payload.get("tenant_id")).first()
    if not c: raise HTTPException(404, "Cobrança não encontrada")
    return _cobranca_to_dict(c)

@app.post("/v1/lex/cobrancas/proxima-fase")
@app.post("/k1/lex/cobrancas/proxima-fase")
def cobranca_proxima_fase(body: dict, db: Session = Depends(get_db), payload=Depends(verify_token)):
    c = db.query(Cobranca).filter_by(id=body.get("id"), tenant_id=payload.get("tenant_id")).first()
    if not c: raise HTTPException(404, "Cobrança não encontrada")
    if c.status in ("pago", "cancelado"): raise HTTPException(400, f"Status {c.status} não permite avançar fase")
    fases_labels = ["Pendente", "Aguardando Pagamento", "Vencida", "Em Cobrança", "Pago"]
    fase_ant = c.fase_atual
    c.fase_atual = min(c.fase_atual + 1, len(fases_labels) - 1)
    c.updated_at = datetime.utcnow()
    db.add(HistoricoCobranca(id=str(uuid.uuid4()), cobranca_id=c.id, acao="fase_avancada",
        fase_anterior=fase_ant, fase_nova=c.fase_atual,
        observacao=f"Avançado de {fases_labels[fase_ant]} para {fases_labels[c.fase_atual]}"))
    db.commit()
    return _cobranca_to_dict(c)

@app.post("/v1/lex/cobrancas/marcar-pago")
@app.post("/k1/lex/cobrancas/marcar-pago")
def cobranca_marcar_pago(body: dict, db: Session = Depends(get_db), payload=Depends(verify_token)):
    c = db.query(Cobranca).filter_by(id=body.get("id"), tenant_id=payload.get("tenant_id")).first()
    if not c: raise HTTPException(404, "Cobrança não encontrada")
    if c.status == "cancelado": raise HTTPException(400, "Cobrança cancelada não pode ser paga")
    status_ant = c.status
    c.status, c.fase_atual, c.data_pagamento, c.updated_at = "pago", 4, datetime.utcnow(), datetime.utcnow()
    db.add(HistoricoCobranca(id=str(uuid.uuid4()), cobranca_id=c.id, acao="marcado_pago",
        status_anterior=status_ant, status_novo="pago", observacao=body.get("observacao", "Marcado como pago")))
    db.commit()
    return _cobranca_to_dict(c)

@app.post("/v1/lex/cobrancas/cancelar")
@app.post("/k1/lex/cobrancas/cancelar")
def cobranca_cancelar(body: dict, db: Session = Depends(get_db), payload=Depends(verify_token)):
    c = db.query(Cobranca).filter_by(id=body.get("id"), tenant_id=payload.get("tenant_id")).first()
    if not c: raise HTTPException(404, "Cobrança não encontrada")
    if c.status == "pago": raise HTTPException(400, "Cobrança paga não pode ser cancelada")
    status_ant = c.status
    motivo = body.get("motivo", "Cancelado pelo usuário")
    c.status, c.motivo_cancelamento, c.updated_at = "cancelado", motivo, datetime.utcnow()
    db.add(HistoricoCobranca(id=str(uuid.uuid4()), cobranca_id=c.id, acao="cancelada",
        status_anterior=status_ant, status_novo="cancelado", observacao=motivo))
    db.commit()
    return _cobranca_to_dict(c)

@app.post("/v1/lex/cobrancas/timeline")
@app.post("/k1/lex/cobrancas/timeline")
def cobranca_timeline(body: dict, db: Session = Depends(get_db), payload=Depends(verify_token)):
    c = db.query(Cobranca).filter_by(id=body.get("id"), tenant_id=payload.get("tenant_id")).first()
    if not c: raise HTTPException(404, "Cobrança não encontrada")
    historico = db.query(HistoricoCobranca).filter_by(cobranca_id=c.id).order_by(HistoricoCobranca.created_at).all()
    fases = [{"ordem": i, "label": l, "descricao": d} for i, (l, d) in enumerate([
        ("Pendente", "Aguardando processamento"),
        ("Aguardando Pagamento", "Aguardando confirmação"),
        ("Vencida", "Prazo de pagamento vencido"),
        ("Em Cobrança", "Cobrança ativa em andamento"),
        ("Pago", "Pagamento recebido com sucesso"),
    ])]
    proximas_acoes = []
    if c.status not in ("pago", "cancelado"):
        proximas_acoes = [
            {"acao": "proxima_fase", "label": "Próxima Fase", "descricao": "Avançar fase de cobrança"},
            {"acao": "marcar_pago", "label": "Marcar como Pago", "descricao": "Registrar pagamento"},
            {"acao": "cancelar", "label": "Cancelar", "descricao": "Cancelar cobrança"},
        ]
    return {
        "cobranca_id": c.id, "status_atual": c.status, "fase_atual": c.fase_atual,
        "valor_centavos": c.valor_centavos,
        "data_vencimento": c.data_vencimento.isoformat() if c.data_vencimento else None,
        "data_pagamento": c.data_pagamento.isoformat() if c.data_pagamento else None,
        "fases": fases,
        "timeline": [{
            "id": h.id, "acao": h.acao, "fase_anterior": h.fase_anterior, "fase_nova": h.fase_nova,
            "status_anterior": h.status_anterior, "status_novo": h.status_novo,
            "observacao": h.observacao, "data": h.created_at.isoformat()
        } for h in historico],
        "proximas_acoes": proximas_acoes,
    }

class _CreditCardIn(BaseModel):
    holderName: str; number: str; expiryMonth: str; expiryYear: str; ccv: str

class _CreditCardHolderInfoIn(BaseModel):
    name: str; email: str; cpfCnpj: str; postalCode: str; addressNumber: str
    phone: Optional[str] = None; mobilePhone: Optional[str] = None

class PagamentoIn(BaseModel):
    cobrancaId: str
    billingType: str
    customer: str
    description: Optional[str] = None
    creditCardToken: Optional[str] = None
    creditCard: Optional[_CreditCardIn] = None
    creditCardHolderInfo: Optional[_CreditCardHolderInfoIn] = None
    remoteIp: str = "127.0.0.1"

@app.post("/v1/lex/cobrancas/pagamento")
@app.post("/k1/lex/cobrancas/pagamento")
def criar_pagamento(body: PagamentoIn, db: Session = Depends(get_db), payload=Depends(verify_token)):
    if body.billingType not in ("CREDIT_CARD", "PIX"):
        raise HTTPException(400, "billingType invalido. Use 'CREDIT_CARD' ou 'PIX'")
    if body.billingType == "CREDIT_CARD" and not body.creditCardToken and not body.creditCard:
        raise HTTPException(400, "Informe creditCardToken ou creditCard para pagamento com cartao")
    if body.billingType == "CREDIT_CARD" and body.creditCard and not body.creditCardHolderInfo:
        raise HTTPException(400, "creditCardHolderInfo e obrigatorio quando creditCard e informado")
    if not KEALEX_ASAAS_API_KEY:
        raise HTTPException(500, "KEALEX_ASAAS_API_KEY nao configurada")

    tenant_id = payload.get("tenant_id")
    c = db.query(Cobranca).filter_by(id=body.cobrancaId, tenant_id=tenant_id).first()
    if not c:
        raise HTTPException(404, "Cobranca nao encontrada")
    if c.status in ("pago", "cancelado"):
        raise HTTPException(400, f"Cobranca com status '{c.status}' nao pode ser paga")

    due_date = c.data_vencimento.date().isoformat() if c.data_vencimento else datetime.utcnow().date().isoformat()
    payload_asaas = {
        "billingType": body.billingType,
        "customer": body.customer,
        "value": round(c.valor_centavos / 100, 2),
        "dueDate": due_date,
        "description": body.description or f"Cobranca {c.id}",
        "externalReference": c.id,
    }
    if body.billingType == "CREDIT_CARD":
        if body.creditCardToken:
            payload_asaas["creditCardToken"] = body.creditCardToken
        else:
            payload_asaas["creditCard"] = body.creditCard.model_dump()
            payload_asaas["creditCardHolderInfo"] = {
                **body.creditCardHolderInfo.model_dump(exclude_none=True),
                "cpfCnpj": _digits(body.creditCardHolderInfo.cpfCnpj),
                "phone": _digits(body.creditCardHolderInfo.phone),
                "mobilePhone": _digits(body.creditCardHolderInfo.mobilePhone),
            }
            payload_asaas["remoteIp"] = body.remoteIp

    try:
        resp = httpx.post(
            f"{ASAAS_BASE}/payments",
            json=payload_asaas,
            headers={"accept": "application/json", "content-type": "application/json",
                     "access_token": KEALEX_ASAAS_API_KEY, "User-Agent": "HubKealex/1.0.0"},
            timeout=15,
        )
    except httpx.RequestError as e:
        raise HTTPException(502, f"Erro ao conectar com gateway de pagamento: {str(e)}")

    if resp.status_code not in (200, 201):
        raise HTTPException(502, f"Asaas recusou: {resp.json().get('errors', resp.text)}")

    asaas_data = resp.json()
    status_ant = c.status
    c.status = "aguardando_pagamento"
    c.fase_atual = max(c.fase_atual, 1)
    c.updated_at = datetime.utcnow()
    db.add(HistoricoCobranca(
        id=str(uuid.uuid4()), cobranca_id=c.id, acao="pagamento_iniciado",
        status_anterior=status_ant, status_novo="aguardando_pagamento",
        observacao=f"billingType={body.billingType}, asaas_id={asaas_data.get('id')}",
    ))
    db.commit()
    return {
        "cobrancaId": c.id,
        "asaasId": asaas_data.get("id"),
        "billingType": asaas_data.get("billingType"),
        "status": asaas_data.get("status"),
        "value": asaas_data.get("value"),
        "dueDate": asaas_data.get("dueDate"),
        "invoiceUrl": asaas_data.get("invoiceUrl"),
        "pixQrCodeUrl": asaas_data.get("pixQrCodeUrl"),
        "bankSlipUrl": asaas_data.get("bankSlipUrl"),
    }

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
    database_url = make_url(KEALEX_DATABASE_URL)
    return {
        "host": database_url.host or "",
        "port": str(database_url.port or ""),
        "name": database_url.database or "",
        "user": database_url.username or "",
        "password": "********" if database_url.password else "",
        "connection_string": database_url.render_as_string(hide_password=True),
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
