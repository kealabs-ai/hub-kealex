import os
import uuid
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase

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

