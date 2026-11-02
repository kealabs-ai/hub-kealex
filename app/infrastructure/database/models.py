import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Enum as SAEnum, ForeignKey, Index,
    Integer, Numeric, PrimaryKeyConstraint, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase

from app.domain.entities.enums import RoleEnum, StatusEnum

class Base(DeclarativeBase): pass

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

class UsuarioChavePublica(Base):
    __tablename__ = "usuarios_chaves_publicas"
    __table_args__ = (
        UniqueConstraint("user_id", "orgao", name="uq_usuario_chave_publica_orgao"),
    )
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True)
    orgao = Column(String(120), nullable=False)
    chave_publica = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

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

class Intimacao(Base):
    __tablename__ = "intimacoes"
    __table_args__ = (
        Index("ix_intimacoes_tenant_publicacao", "tenant_id", "data_publicacao"),
    )
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, index=True)
    user_id = Column(String(36), nullable=False)
    processo_id = Column(String(36), nullable=True)
    processo_numero = Column(String(50), nullable=True)
    processo_titulo = Column(String(255), nullable=True)
    diario = Column(String(255), nullable=False)
    data_publicacao = Column(String(40), nullable=False)
    conteudo = Column(Text, nullable=False)
    resumo_ia = Column(Text, nullable=True)
    prazo_calculado = Column(String(40), nullable=True)
    status = Column(String(20), nullable=False, default="nova")
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


__all__ = [name for name in globals() if not name.startswith("__")]
