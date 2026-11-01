import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String, Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase
from app.domain.entities.document import TipoEnum, StatusEnum

class Base(DeclarativeBase): pass

class Documento(Base):
    __tablename__ = "documentos"
    id               = Column(String(36),   primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id        = Column(String(36),   nullable=False)
    user_id          = Column(String(36),   nullable=False)
    escritorio_id    = Column(String(36),   nullable=True)
    processo_id      = Column(String(36),   nullable=False)
    uploadado_por_id = Column(String(36),   nullable=False)
    nome             = Column(String(255),  nullable=False)
    tipo             = Column(SAEnum(TipoEnum,   name="tipo_doc_enum"),   nullable=False)
    status           = Column(SAEnum(StatusEnum, name="status_doc_enum"), default=StatusEnum.pendente)
    url_arquivo      = Column(String(1000), nullable=False)
    tamanho_bytes    = Column(Integer,      default=0)
    created_at       = Column(DateTime,     default=datetime.utcnow)
    updated_at       = Column(DateTime,     default=datetime.utcnow, onupdate=datetime.utcnow)

