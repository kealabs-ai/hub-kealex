import enum, uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Integer, Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase): pass

class RoleEnum(str, enum.Enum):
    admin    = "admin"
    escritorio = "escritorio"
    advogado = "advogado"
    juridico = "juridico"
    cliente  = "cliente"

class Tenant(Base):
    __tablename__ = "tenants"
    id               = Column(String(36),  primary_key=True, default=lambda: str(uuid.uuid4()))
    nome             = Column(String(255), nullable=False)
    slug             = Column(String(100), unique=True, nullable=False)
    plano            = Column(String(20),  nullable=False, default="trial")
    trial_started_at = Column(DateTime,    nullable=True)
    trial_expires_at = Column(DateTime,    nullable=True)
    asaas_customer_id = Column(String(80), nullable=True)
    billing_name = Column(String(255), nullable=True)
    billing_email = Column(String(255), nullable=True)
    billing_cpf_cnpj = Column(String(20), nullable=True)
    billing_phone = Column(String(30), nullable=True)
    billing_mobile_phone = Column(String(30), nullable=True)
    billing_postal_code = Column(String(10), nullable=True)
    billing_address = Column(String(255), nullable=True)
    billing_address_number = Column(String(20), nullable=True)
    billing_complement = Column(String(100), nullable=True)
    billing_neighborhood = Column(String(100), nullable=True)
    billing_city = Column(String(100), nullable=True)
    billing_state = Column(String(2), nullable=True)
    asaas_subscription_id = Column(String(80), nullable=True)
    subscription_plan = Column(String(20), nullable=True)
    subscription_cycle = Column(String(20), nullable=True)
    subscription_expires_at = Column(DateTime, nullable=True)
    last_paid_payment_id = Column(String(80), nullable=True)
    subscription_status = Column(String(20), nullable=False, default="trialing")
    next_due_date = Column(String(10), nullable=True)
    ativo            = Column(Boolean,     default=True)
    created_at       = Column(DateTime,    default=datetime.utcnow)
    updated_at       = Column(DateTime,    default=datetime.utcnow, onupdate=datetime.utcnow)

class Usuario(Base):
    __tablename__ = "usuarios"
    id            = Column(String(36),  primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id     = Column(String(36),  nullable=False)
    escritorio_id = Column(String(36),  nullable=True)
    codigo = Column(String(16), nullable=True)
    nome          = Column(String(255), nullable=False)
    email         = Column(String(255), nullable=False)
    senha_hash    = Column(String(255), nullable=False)
    role          = Column(SAEnum(RoleEnum, name="role_enum_auth"), nullable=False)
    ativo         = Column(Boolean,     default=True)
    created_at    = Column(DateTime,    default=datetime.utcnow)
    updated_at    = Column(DateTime,    default=datetime.utcnow, onupdate=datetime.utcnow)

class Escritorio(Base):
    __tablename__ = "escritorios"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False)
    nome = Column(String(255), nullable=False)
    cnpj = Column(String(18), nullable=True)
    endereco = Column(String(500), nullable=True)
    telefone = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    limite_advogados = Column(Integer, nullable=False, default=3, server_default="3")
    codigo = Column(String(16), nullable=False, unique=True)
    ativo = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
class AsaasWebhookEvent(Base):
    __tablename__ = "asaas_webhook_events"
    id = Column(String(100), primary_key=True)
    event = Column(String(80), nullable=False)
    received_at = Column(DateTime, default=datetime.utcnow, nullable=False)
