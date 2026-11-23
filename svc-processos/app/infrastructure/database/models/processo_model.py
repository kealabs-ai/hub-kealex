import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, Enum as SAEnum, JSON, UniqueConstraint
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



class ProcessoAcompanhado(Base):
    __tablename__ = "processos_acompanhados"
    __table_args__ = (UniqueConstraint("tenant_id", "scope_key", "numero_processo", name="uq_processo_acompanhado_scope_numero"),)
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, index=True)
    user_id = Column(String(36), nullable=False)
    scope_key = Column(String(36), nullable=False)
    numero_processo = Column(String(20), nullable=False)
    tribunal = Column(String(255), nullable=True)
    classe_processual = Column(String(255), nullable=True)
    assunto = Column(String(1000), nullable=True)
    fase_atual = Column(String(255), nullable=True)
    situacao = Column(String(255), nullable=True)
    data_ultima_movimentacao = Column(String(100), nullable=True)
    ultima_consulta_em = Column(DateTime, nullable=False, default=datetime.utcnow)
    dados = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class HistoricoConsultaProcessual(Base):
    __tablename__ = "historico_consultas_processuais"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, index=True)
    processo_id = Column(String(36), ForeignKey("processos_acompanhados.id"), nullable=True, index=True)
    numero_processo = Column(String(20), nullable=False)
    usuario_solicitante_id = Column(String(36), nullable=False)
    fornecedor = Column(String(80), nullable=False, default="escavador")
    status_http = Column(Integer, nullable=True)
    status_consulta = Column(String(255), nullable=False)
    houve_alteracao = Column(Integer, nullable=True)
    data_ultima_movimentacao = Column(String(100), nullable=True)
    consultado_em = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
