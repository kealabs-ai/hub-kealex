import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase, relationship
from app.domain.entities.process_status import StatusEnum

class Base(DeclarativeBase): pass

class Cliente(Base):
    __tablename__ = "clientes"
    id          = Column(String(36),  primary_key=True)
    tenant_id   = Column(String(36),  nullable=False)
    advogado_id = Column(String(36),  nullable=False)
    nome        = Column(String(255), nullable=False)
    email       = Column(String(255), nullable=False)
    telefone    = Column(String(50),  nullable=True)
    cpf_cnpj    = Column(String(20),  nullable=True)
    endereco    = Column(String(500), nullable=True)
    observacoes = Column(Text,        nullable=True)
    created_at  = Column(DateTime,    default=datetime.utcnow)
    updated_at  = Column(DateTime,    default=datetime.utcnow, onupdate=datetime.utcnow)

class Processo(Base):
    __tablename__ = "processos"
    id            = Column(String(36),   primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id     = Column(String(36),   nullable=False)
    user_id       = Column(String(36),   nullable=False)
    escritorio_id = Column(String(36),   nullable=True)
    numero        = Column(String(100),  nullable=False)
    titulo        = Column(String(255),  nullable=False)
    descricao     = Column(String(1000), default="")
    status        = Column(SAEnum(StatusEnum, name="status_processo_enum"), default=StatusEnum.ativo)
    advogado_id   = Column(String(36),   nullable=False)
    cliente_id    = Column(String(36),   nullable=False)
    vara          = Column(String(255),  default="")
    tribunal      = Column(String(255),  default="")
    fase_atual    = Column(Integer,      default=0)
    created_at    = Column(DateTime,     default=datetime.utcnow)
    updated_at    = Column(DateTime,     default=datetime.utcnow, onupdate=datetime.utcnow)
    fases         = relationship("Fase", back_populates="processo", cascade="all, delete-orphan")

class Fase(Base):
    __tablename__ = "fases"
    id            = Column(String(36),   primary_key=True, default=lambda: str(uuid.uuid4()))
    processo_id   = Column(String(36),   ForeignKey("processos.id"), nullable=False)
    label         = Column(String(255),  nullable=False)
    ordem         = Column(Integer,      nullable=False)
    status        = Column(String(50),   default="futura")
    data_conclusao = Column(DateTime,    nullable=True)
    created_at    = Column(DateTime,     default=datetime.utcnow)
    updated_at    = Column(DateTime,     default=datetime.utcnow, onupdate=datetime.utcnow)
    processo      = relationship("Processo", back_populates="fases")

